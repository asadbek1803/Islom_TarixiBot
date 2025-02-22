import logging
import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loader import db, bot
from keyboards.inline.buttons import are_you_sure_markup
from states.test import AdminStateADD
from states.admin import AdminState
from filters.admin import IsBotAdminFilter
from data.config import ADMINS
from utils.pgtoexcel import export_to_excel
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon import TelegramClient
from datetime import datetime




router = Router()


@router.message(Command('allusers'), IsBotAdminFilter(ADMINS))
async def get_all_users(message: types.Message):
    users = await db.select_all_users()

    file_path = f"data/users_list.xlsx"
    await export_to_excel(data=users, headings=['ID', 'Full Name', 'Telegram ID', 'Username', "Language", "Is Admin", "Created At"], filepath=file_path)

    await message.answer_document(types.input_file.FSInputFile(file_path))


@router.message(Command('reklama'), IsBotAdminFilter(ADMINS))
async def ask_ad_content(message: types.Message, state: FSMContext):
    await message.answer("Reklama uchun post yuboring")
    await state.set_state(AdminStateADD.ask_ad_content)


@router.message(AdminStateADD.ask_ad_content, IsBotAdminFilter(ADMINS))
async def send_ad_to_users(message: types.Message, state: FSMContext):
    users = await db.select_all_users()
    count = 0
    for user in users:
        user_id = user[-1]
        try:
            await message.send_copy(chat_id=user_id)
            count += 1
            await asyncio.sleep(0.05)
        except Exception as error:
            logging.info(f"Ad did not send to user: {user_id}. Error: {error}")
    await message.answer(text=f"Reklama {count} ta foydalauvchiga muvaffaqiyatli yuborildi.")
    await state.clear()


@router.message(Command('cleandb'), IsBotAdminFilter(ADMINS))
async def ask_are_you_sure(message: types.Message, state: FSMContext):
    msg = await message.reply("Haqiqatdan ham bazani tozalab yubormoqchimisiz?", reply_markup=are_you_sure_markup)
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(AdminStateADD.are_you_sure)


@router.callback_query(AdminStateADD.are_you_sure, IsBotAdminFilter(ADMINS))
async def clean_db(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    msg_id = data.get('msg_id')
    if call.data == 'yes':
        await db.delete_users()
        text = "Baza tozalandi!"
    elif call.data == 'no':
        text = "Bekor qilindi."
    await bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=msg_id)
    await state.clear()


# Admin management
@router.message(Command('addadmin'), IsBotAdminFilter(ADMINS))
async def ask_admin_id(message: types.Message, state: FSMContext):
    await message.answer("Yangi admin ID raqamini yuboring:")
    await state.set_state(AdminState.add_admin_id)

@router.message(AdminState.add_admin_id, IsBotAdminFilter(ADMINS))
async def add_new_admin(message: types.Message, state: FSMContext):
    try:
        admin_id = int(message.text)
        user = await db.select_user(telegram_id=admin_id)
        if not user:
            await message.answer("Foydalanuvchi topilmadi. Avval bot bilan ishlashi kerak.")
            await state.clear()
            return
        
        await db.set_user_admin(admin_id, True)
        await message.answer(f"Admin muvaffaqiyatli qo'shildi: {user['full_name']}")
    except ValueError:
        await message.answer("Noto'g'ri ID format. Raqam kiriting.")
    except Exception as e:
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        logging.error(f"Error adding admin: {e}")
    
    await state.clear()



# Film management
@router.message(Command('addfilm'), IsBotAdminFilter(ADMINS))
async def ask_film_name(message: types.Message, state: FSMContext):
    await message.answer("Film nomini kiriting:")
    await state.set_state(AdminState.film_name)

@router.message(AdminState.film_name, IsBotAdminFilter(ADMINS))
async def get_film_name(message: types.Message, state: FSMContext):
    await state.update_data(film_name=message.text)
    await message.answer("Film kodini kiriting (Masalan: M.S.A_(1)):")
    await state.set_state(AdminState.film_code)

@router.message(AdminState.film_code, IsBotAdminFilter(ADMINS))
async def get_film_code(message: types.Message, state: FSMContext):
    await state.update_data(film_code=message.text)
    await message.answer("Umumiy seriyalar sonini kiriting:")
    await state.set_state(AdminState.film_series)

@router.message(AdminState.film_series, IsBotAdminFilter(ADMINS))
async def add_new_film(message: types.Message, state: FSMContext):
    await state.update_data(total_series = message.text)
    data = await state.get_data()
    try:
        film = await db.add_film(
            film_name=data['film_name'],
            starting_code=data['film_code'],
            total_series=int(data['total_series']),
        )
        await message.answer(
            f"Film qo'shildi:\n"
            f"Nomi: {film['film_name']}\n"
            f"Kod: {film['starting_code']}\n"
            f"Seriyalar: {film['total_series']}\n"
        )
    except Exception as e:
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        logging.error(f"Error adding film: {e}")
    
    await state.clear()




# Client management
@router.message(Command('addclient'), IsBotAdminFilter(ADMINS))
async def ask_client_phone(message: types.Message, state: FSMContext):
    await message.answer("Telefon raqamni kiriting (+998...):")
    await state.set_state(AdminState.client_phone)

@router.message(AdminState.client_phone, IsBotAdminFilter(ADMINS))
async def get_client_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("API ID ni kiriting:")
    await state.set_state(AdminState.client_api_id)

@router.message(AdminState.client_api_id, IsBotAdminFilter(ADMINS))
async def get_client_api_id(message: types.Message, state: FSMContext):
    try:
        api_id = int(message.text)
        await state.update_data(api_id=api_id)
        await message.answer("API Hash ni kiriting:")
        await state.set_state(AdminState.client_api_hash)
    except ValueError:
        await message.answer("Iltimos, to'g'ri API ID kiriting (raqam).")

@router.message(AdminState.client_api_hash, IsBotAdminFilter(ADMINS))
async def get_client_api_hash(message: types.Message, state: FSMContext):
    await state.update_data(api_hash=message.text)
    await message.answer("Session nomini kiriting:")
    await state.set_state(AdminState.client_session)

@router.message(AdminState.client_session, IsBotAdminFilter(ADMINS))
async def start_client_verification(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    try:
        # Create temporary client for verification
        client = TelegramClient(
            message.text,  # session name
            data['api_id'],
            data['api_hash']
        )
        
        await client.connect()
        
        if not await client.is_user_authorized():
            # Send code request
            await client.send_code_request(data['phone'])
            
            # Store client temporarily
            await state.update_data(
                session_name=message.text,
                temp_client=client
            )
            
            await message.answer("Telegram dan kelgan kodni yuboring:")
            await state.set_state(AdminState.client_code)
        else:
            # If already authorized, save to database
            await client.disconnect()
            await save_client_to_db(message, state, data, message.text)
            
    except Exception as e:
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        logging.error(f"Error in client verification: {e}")
        await state.clear()

@router.message(AdminState.client_code, IsBotAdminFilter(ADMINS))
async def process_code(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['temp_client']
    
    try:
        # Try to sign in with the code
        await client.sign_in(data['phone'], message.text.split("_")[1])
        await client.disconnect()
        
        # Save to database after successful verification
        await save_client_to_db(message, state, data, data['session_name'])
        
    except SessionPasswordNeededError:
        # If 2FA is enabled
        await message.answer("Ikki bosqichli autentifikatsiya paroli kerak. Parolni yuboring:")
        await state.set_state(AdminState.client_2fa)
        
    except PhoneCodeInvalidError:
        await message.answer("Noto'g'ri kod. Qaytadan urinib ko'ring:")
        
    except Exception as e:
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        logging.error(f"Error in code verification: {e}")
        await client.disconnect()
        await state.clear()

@router.message(AdminState.client_2fa, IsBotAdminFilter(ADMINS))
async def process_2fa(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['temp_client']
    
    try:
        # Try to complete sign in with 2FA password
        await client.sign_in(password=message.text)
        await client.disconnect()
        
        # Save to database after successful 2FA
        await save_client_to_db(message, state, data, data['session_name'])
        
    except Exception as e:
        await message.answer("Noto'g'ri parol yoki xatolik yuz berdi. Qaytadan urinib ko'ring.")
        logging.error(f"Error in 2FA verification: {e}")
        await client.disconnect()
        await state.clear()

async def save_client_to_db(message: types.Message, state: FSMContext, data: dict, session_name: str):
    try:
        # Save verified client to database
        client = await db.add_bot_client(
            phone_number=data['phone'],
            api_id=data['api_id'],
            api_hash=data['api_hash'],
            session_name=session_name
        )
        
        await message.answer(
            f"Client muvaffaqiyatli qo'shildi:\n"
            f"📱 Telefon: {client['phone_number']}\n"
            f"📝 Sessiya: {client['session_name']}\n"
            f"✅ Status: Tasdiqlangan"
        )
        
    except Exception as e:
        await message.answer("Ma'lumotlar bazasiga saqlashda xatolik yuz berdi.")
        logging.error(f"Error saving client to database: {e}")
    
    finally:
        await state.clear()

# Active clients list
@router.message(Command('clients'), IsBotAdminFilter(ADMINS))
async def list_active_clients(message: types.Message):
    try:
        clients = await db.get_active_bot_clients()
        if not clients:
            await message.answer("Aktiv clientlar mavjud emas.")
            return

        
        text = "Aktiv clientlar ro'yxati:\n\n"
        for client in clients:
            right_time = datetime.strftime('%Y-%m-%d %H:%M')
            text += f"📱 {client['phone_number']}\n"
            text += f"📝 Session: {client['session_name']}\n"
            text += f"📅 Qo'shilgan vaqt: {client['created_at']}\n\n"
        
        await message.answer(text)
    except Exception as e:
        await message.answer("Xatolik yuz berdi.")
        logging.error(f"Error listing clients: {e}")