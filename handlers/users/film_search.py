from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from loader import bot, db
from telethon import TelegramClient
from telethon.tl.types import Message
import math

router = Router()

# Telegramga ulanish uchun malumotlar
api_id = '28188052'
api_hash = '215d8197a0eecdf6faf269014044f721'
channel = '@IslomTarixiBaza'
client = TelegramClient('session_name', api_id, api_hash)

async def get_movie_by_code(movie_code):
    print(f"Qidirilmoqda: {movie_code}")
    messages = []
    try:
        async with client:
            offset_id = 0
            total_messages = 0
            
            while True:
                batch = await client.get_messages(channel, limit=100, offset_id=offset_id)
                if not batch:
                    print(f"{total_messages} ta xabar tekshirildi, boshqa xabar topilmadi")
                    break
                    
                messages.extend(batch)
                total_messages += len(batch)
                offset_id = batch[-1].id
                
                print(f"{total_messages} ta xabar tekshirildi...")
                
                for msg in batch:
                    if isinstance(msg, Message) and msg.text:
                        # Har bir xabarni tekshirish va debug qilish
                        if "ID" in msg.text:
                            print(f"ID li xabar topildi: {msg.text[:100]}")  # Xabarning boshlanishi
                            
                            # Barcha mumkin bo'lgan formatlarni tekshirish
                            search_formats = [
                                f"ID: {movie_code}",
                                f"ID:{movie_code}",
                                f"ID: {movie_code}",  # Bo'sh joylar bilan
                                f"ID:{movie_code}",   # Bo'sh joylarsiz
                                f"**ID:** {movie_code}",  # Markdown formati
                                f"**ID:**{movie_code}"    # Markdown formati bo'sh joysiz
                            ]
                            
                            for format in search_formats:
                                if format in msg.text:
                                    print(f"Xabar topildi! Format: {format}")
                                    return msg
                
                if total_messages >= 1000:
                    print("1000 ta xabar tekshirildi, qidiruv to'xtatildi")
                    break

    except Exception as e:
        print(f"Qidirishda xatolik: {str(e)}")
        return None

    print(f"{movie_code} kodi uchun {total_messages} ta xabar tekshirildi, topilmadi")
    return None


# ID bo'yicha kino yuborish
@router.message(lambda message: message.text and '-' in message.text)
async def send_movie_by_id(message: types.Message):
    movie_code = message.text.strip()
    
    # Validate the format (e.g., M.S.A.V-1)
    if not movie_code or not '-' in movie_code:
        await message.reply("Noto'g'ri format. Masalan: M.S.A.V-1")
        return
        
    loading_msg = await bot.send_message(text="Kino qidirilmoqda⏳", chat_id=message.from_user.id)
    
    movie_msg = await get_movie_by_code(movie_code=movie_code)
    
    await bot.delete_message(chat_id=message.from_user.id, message_id=loading_msg.message_id)
    
    if movie_msg:
        try:
            await bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=channel,
                message_id=movie_msg.id
            )
            back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
            ])
            await message.answer("Boshqa kinoni ko'rish uchun:", reply_markup=back_keyboard)
        except Exception as e:
            print(f"Xabarni yuborishda xatolik: {e}")
            await message.reply("Kino yuborishda xatolik yuz berdi.")
    else:
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
        ])
        await message.reply("Kino topilmadi❌", reply_markup=back_keyboard)
    

# Asosiy menyu callbackni ko'rsatish
@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: types.CallbackQuery):
    # Asosiy menyu buttonlari - bu qismni o'zingizni asosiy menyungizga moslashtiring
    main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Barcha filmlar 🎬", callback_data="btn_films")],
        [InlineKeyboardButton(text="Payg'ambarlar tarixi 🎥", callback_data="btn_prophets")]
        # Boshqa asosiy menyu tugmalarini qo'shing
    ])
    
    await callback.message.edit_text("Bosh menyu 🏠\nKerakli bo'limni tanlang:", reply_markup=main_menu_keyboard)
    await callback.answer()

# Film seriyalarini sahifalash uchun keyboard yaratish
def create_series_pagination(film_name, total_series, current_page=1, items_per_page=10):
    keyboard = []
    
    # Sahifalash uchun ma'lumotlar
    total_pages = math.ceil(total_series / items_per_page)
    start_idx = (current_page - 1) * items_per_page + 1
    end_idx = min(current_page * items_per_page, total_series)
    
    # Seriya tugmalarini qo'shish
    for i in range(start_idx, end_idx + 1):
        keyboard.append([
            InlineKeyboardButton(text=f"{i}-qism", callback_data=f"series:{film_name}:{i}")
        ])
    
    # Navigatsiya tugmalari
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"series_page:{film_name}:{current_page-1}:{total_series}"))
    
    nav_row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="ignore"))
    
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"series_page:{film_name}:{current_page+1}:{total_series}"))
    
    keyboard.append(nav_row)
    
    # Orqaga qaytish va Asosiy menyuga qaytish
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="btn_films"),
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Filmlar ro'yxatini sahifalash uchun keyboard yaratish
async def create_films_pagination(current_page=1, items_per_page=10, category=None):
    # Barcha filmlarni olish (agar category berilgan bo'lsa, shu kategoriyaga tegishli filmlarni olish)
    
    all_films = await db.get_all_films()

        
    # Sahifalash uchun ma'lumotlar
    total_films = len(all_films)
    total_pages = math.ceil(total_films / items_per_page)
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(current_page * items_per_page, total_films)
    
    # Joriy sahifa uchun filmlar
    current_films = all_films[start_idx:end_idx]
    
    keyboard = []
    
    # Film tugmalarini qo'shish
    for film in current_films:
        keyboard.append([
            InlineKeyboardButton(
                text=film['film_name'], 
                callback_data=f"film:{film['id']}:{film['total_series']}"
            )
        ])
    
    # Navigatsiya tugmalari
    nav_row = []
    if current_page > 1:
        nav_data = f"films_page:{current_page-1}"
        if category:
            nav_data += f":{category}"
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=nav_data))
    
    nav_row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="ignore"))
    
    if current_page < total_pages:
        nav_data = f"films_page:{current_page+1}"
        if category:
            nav_data += f":{category}"
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=nav_data))
    
    keyboard.append(nav_row)
    
    # Asosiy menyuga qaytish
    keyboard.append([InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Barcha filmlar ro'yxatini ko'rsatish
@router.callback_query(F.data == "btn_films")
async def show_films_list(callback: types.CallbackQuery):
    keyboard = await create_films_pagination(current_page=1)
    
    if keyboard:
        await callback.message.edit_text(
            "Mavjud filmlar ro'yxati 🎬\nKerakli filmni tanlang:", 
            reply_markup=keyboard
        )
    else:
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
        ])
        await callback.message.edit_text("Filmlar ro'yxati bo'sh 😔", reply_markup=back_keyboard)
    
    await callback.answer()

# Payg'ambarlar tarixi bo'limiga o'tish
@router.callback_query(F.data == "btn_prophets")
async def prophets_films_callback(callback: types.CallbackQuery):
    keyboard = await create_films_pagination(current_page=1, category="prophets")
    
    if keyboard:
        await callback.message.edit_text(
            "Payg'ambarlar tarixi bo'limidagi filmlar 🎬\nKerakli filmni tanlang:", 
            reply_markup=keyboard
        )
    else:
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
        ])
        await callback.message.edit_text("Filmlar ro'yxati bo'sh 😔", reply_markup=back_keyboard)
    
    await callback.answer()

# Payg'ambarlar tarixi bo'limiga o'tish (message handler)
@router.message(F.text == "Payg'ambarlar tarixi 🎥")
async def prophets_films(message: types.Message):
    keyboard = await create_films_pagination(current_page=1, category="prophets")
    
    if keyboard:
        await message.answer(
            "Payg'ambarlar tarixi bo'limidagi filmlar 🎬\nKerakli filmni tanlang:", 
            reply_markup=keyboard
        )
    else:
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
        ])
        await message.answer("Filmlar ro'yxati bo'sh 😔", reply_markup=back_keyboard)

# Filmlar sahifasini almashtirish
@router.callback_query(F.data.startswith("films_page:"))
async def handle_films_pagination(callback: types.CallbackQuery):
    data_parts = callback.data.split(':')
    page = int(data_parts[1])
    
    category = None
    if len(data_parts) > 2:
        category = data_parts[2]
    
    keyboard = await create_films_pagination(current_page=page, category=category)
    
    title = "Mavjud filmlar ro'yxati 🎬"
    if category == "prophets":
        title = "Payg'ambarlar tarixi bo'limidagi filmlar 🎬"
    
    if keyboard:
        await callback.message.edit_text(
            f"{title}\nKerakli filmni tanlang:", 
            reply_markup=keyboard
        )
    else:
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
        ])
        await callback.message.edit_text("Filmlar ro'yxati bo'sh 😔", reply_markup=back_keyboard)
    
    await callback.answer()

# Film tanlanganda seriyalarini ko'rsatish
@router.callback_query(F.data.startswith("film:"))
async def show_film_series(callback: types.CallbackQuery):
    data_parts = callback.data.split(':')
    film_id = int(data_parts[1])
    total_series = int(data_parts[2])
    
    # Filmni bazadan olish
    film = await db.get_film(id=film_id)
    
    if film:
        keyboard = create_series_pagination(film['film_name'], total_series)
        await callback.message.edit_text(
            f"""{film['film_name']}" filmi qismlari:\nKerakli qismni tanlang:""",
            reply_markup=keyboard
        )
    else:
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="btn_films")],
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
        ])
        await callback.message.edit_text("Film topilmadi 😔", reply_markup=back_keyboard)
    
    await callback.answer()

# Seriyalar sahifasini almashtirish
@router.callback_query(F.data.startswith("series_page:"))
async def handle_series_pagination(callback: types.CallbackQuery):
    data_parts = callback.data.split(':')
    film_name = data_parts[1]
    page = int(data_parts[2])
    total_series = int(data_parts[3])
    
    keyboard = create_series_pagination(film_name, total_series, current_page=page)
    
    await callback.message.edit_text(
        f"""{film_name}" filmi qismlari:\nKerakli qismni tanlang:""",
        reply_markup=keyboard
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("series:"))
async def send_film_series(callback: types.CallbackQuery):
    data_parts = callback.data.split(':')
    film_name = data_parts[1]
    series_num = data_parts[2]

    await callback.answer("Qism qidirilmoqda...")
    loading_msg = await callback.message.answer("Kino qidirilmoqda⏳")

    try:
        film = await db.get_film(film_name=film_name)

        if film:
            print(f"Film ma'lumotlari: {film}")
            series_code = f"{film['starting_code']}-{series_num}"
            print(f"Yaratilgan seriya kodi: {series_code}")

            movie_msg = await get_movie_by_code(movie_code=series_code)

            # O'chirish loading xabarni
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=loading_msg.message_id)

            # O'chirish qismlar ko'rsatilgan xabarni
            await callback.message.delete()

            if movie_msg:
                try:
                    await bot.copy_message(
                        chat_id=callback.message.chat.id,
                        from_chat_id=channel,
                        message_id=movie_msg.id
                    )

                    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="⬅️ Filmga qaytish", callback_data=f"film:{film['id']}:{film['total_series']}")],
                        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
                    ])

                    await callback.message.answer("Qo'shimcha harakatlar:", reply_markup=back_keyboard)
                except Exception as e:
                    print(f"Xabarni yuborishda xatolik: {str(e)}")
                    await callback.message.answer("Kinoni yuborishda xatolik yuz berdi.", 
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"film:{film['id']}:{film['total_series']}")],
                            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
                        ])
                    )
            else:
                await callback.message.answer(
                    f"Ushbu qism ({series_num}) topilmadi❌\n"
                    f"Qidirilgan ID: {series_code}\n"
                    "Iltimos, kanal administratoriga bog'laning.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="⬅️ Filmga qaytish", callback_data=f"film:{film['id']}:{film['total_series']}")],
                        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
                    ])
                )
        else:
            print("Film bazadan topilmadi")
            await callback.message.answer("Film ma'lumotlari topilmadi😔",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="btn_films")],
                    [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
                ])
            )

    except Exception as e:
        print(f"Asosiy xatolik: {str(e)}")
        await callback.message.answer("Xatolik yuz berdi, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
            ])
        )

# Mundarija komandasi
@router.message(Command('mundarija'))
async def get_films_list(message: types.Message):
    keyboard = await create_films_pagination(current_page=1)
    
    if keyboard:
        await message.answer(
            "Mavjud filmlar ro'yxati 🎬\nKerakli filmni tanlang:", 
            reply_markup=keyboard
        )
    else:
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
        ])
        await message.answer("Filmlar ro'yxati bo'sh 😔 Yoki bu bo'lim hozir tamirda🛠", reply_markup=back_keyboard)