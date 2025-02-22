from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.session.middlewares.request_logging import logger
from loader import db, bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from data.config import ADMINS
from components.messages import buttons, messages
from datetime import datetime

router = Router()

def get_inline_keyboard(language):
    """Foydalanuvchi tiliga mos Inline tugmalarni qaytaradi."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons[language]["btn_films"], callback_data="btn_films")],
        [
            InlineKeyboardButton(text=buttons[language]["btn_namaz_time"], callback_data="btn_namaz_time"), 
            InlineKeyboardButton(text=buttons[language]["btn_change_lang"], callback_data="btn_change_lang")
        ],
        [InlineKeyboardButton(text=buttons[language]["developer"], callback_data="developer")]
    ])

def language_keyboard():
    """Tilni tanlash uchun InlineKeyboardMarkup"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek lotin", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇺🇿 Ўзбек кирил", callback_data="lang_kiril")
        ]
    ])

def get_film_categories_keyboard(language):
    """Film kategoriyalari uchun inline tugmalar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons[language]["btn_prophets"], callback_data="btn_prophets")],
        [InlineKeyboardButton(text=buttons[language]["btn_all_films"], callback_data="btn_all_films")],
        [InlineKeyboardButton(text=buttons[language]["btn_back"], callback_data="main_menu")]
    ])

@router.message(CommandStart())
async def do_start(message: types.Message):
    """Foydalanuvchini tekshirish va u tanlagan til bo'yicha xabar yuborish."""
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name
    user = await db.select_user(telegram_id=telegram_id)

    if user:
        language = user.get("language", "uz")
        text = messages[language]["start_command"].format(name=full_name)
        await message.answer(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_inline_keyboard(language)
        )
    else:
        text = f"Assalomu alaykum, <b>{full_name}</b>! 👋\n{messages['uz']['choose_lang']}"
        await message.answer(
            text=text,
            reply_markup=language_keyboard(),
            parse_mode=ParseMode.HTML
        )

@router.callback_query(F.data.startswith("lang_"))
async def handle_language_selection(callback: types.CallbackQuery):
    """Tanlangan tilni qayta ishlash"""
    selected_language = callback.data.split("_")[1]  # "lang_uz" -> "uz"
    telegram_id = callback.from_user.id
    full_name = callback.from_user.full_name
    username = callback.from_user.username
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        user = await db.select_user(telegram_id=telegram_id)
        if user:
            await db.update_user_language(selected_language, telegram_id)
            update_messages = {
                "uz": "Til muvaffiqiyatli yangilandi ✅",
                "kiril": "Тил муваффиқиятли янгиланди ✅"
            }
            await callback.message.edit_text(
                text=update_messages[selected_language],
                reply_markup=get_inline_keyboard(selected_language)
            )
        else:
            await db.add_user(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username,
                language=selected_language
            )
            welcome_messages = {
                "uz": ("Akkaunt muvaffaqiyatli yaratildi ✅", 
                       f"Assalomu alaykum <b>{full_name}</b>! Bizning Islom Tarixi botga xush kelibsiz 😊"),
                "kiril": ("Аккаунт муваффақиятли яратилди ✅", 
                       f"Ассалому алайкум <b>{full_name}</b>! Бизнинг Islom Tarixi ботга хуш келибсиз 😊")
            }
            success_msg, welcome_msg = welcome_messages[selected_language]
            await callback.message.edit_text(text=success_msg)
            await callback.message.answer(
                text=welcome_msg,
                parse_mode=ParseMode.HTML,
                reply_markup=get_inline_keyboard(selected_language)
            )
            
            # Admin notification
            for admin in ADMINS:
                try:
                    admin_message = f"🆕 Yangi foydalanuvchi qo'shildi:\n👤 Ism: {full_name}\n🔹 Username: @{username}\n🆔 Telegram ID: {telegram_id}\n📅 Qo'shilgan vaqt: {created_at}"
                    await bot.send_message(chat_id=admin, text=admin_message, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"Adminga xabar yuborishda xatolik: {e}")
    
    except Exception as e:
        await callback.message.edit_text(text=f"Xatolik yuz berdi ❌\n{str(e)}")
    
    await callback.answer()

@router.callback_query(F.data == "btn_change_lang")
async def handle_change_language(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text="🌍 Iltimos, tilni tanlang:\n\n🇺🇿 O'zbekcha | 🇺🇿 Ўзбек кирил",
        reply_markup=language_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "btn_films")
async def handle_films_btn(callback: types.CallbackQuery):
    user = await db.select_user(telegram_id=callback.from_user.id)
    language = user.get("language", "uz")
    
    await callback.message.edit_text(
        text=messages[language]["films_section"],
        reply_markup=get_film_categories_keyboard(language)
    )
    await callback.answer()

@router.callback_query(F.data == "btn_namaz_time")
async def handle_namaz_time_btn(callback: types.CallbackQuery):
    user = await db.select_user(telegram_id=callback.from_user.id)
    language = user.get("language", "uz")
    
    back_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons[language]["btn_back"], callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        text=messages[language]["namaz_time_info"],
        reply_markup=back_button
    )
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: types.CallbackQuery):
    user = await db.select_user(telegram_id=callback.from_user.id)
    language = user.get("language", "uz")
    
    await callback.message.edit_text(
        text=messages[language]["main_menu_text"],
        parse_mode=ParseMode.HTML,
        reply_markup=get_inline_keyboard(language)
    )
    await callback.answer()

@router.callback_query(F.data == "developer")
async def show_developer_about(call: types.CallbackQuery):
    user = await db.select_user(telegram_id=call.from_user.id)
    language = user.get("language", "uz")

    back_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons[language]["btn_back"], callback_data="main_menu")]
    ])
    await call.message.edit_text(
        text=messages[language]["developer-about"],
        parse_mode=ParseMode.HTML,
        reply_markup=back_button
    )
    await call.answer()
