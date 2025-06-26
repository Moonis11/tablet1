from fastapi import FastAPI, Request
import telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Dispatcher, CallbackQueryHandler, CommandHandler, ContextTypes
import logging
import os
from dotenv import load_dotenv


load_dotenv()  # .env faylni yuklash

TOKEN = os.getenv("BOT_TOKEN")
TABLET_APP_URL = os.getenv("APP_URL")

# 🌍 Tillar
languages = {
    "🇺🇿 Uzbek": "uz",
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en"
}

translations = {
    "uz": {
        "welcome": "👋 Assalomu alaykum! Tilni tanlang 👇",
        "go_app": "🔬 Tablet ilovasiga o'tish"
    },
    "ru": {
        "welcome": "👋 Здравствуйте! Пожалуйста, выберите язык 👇",
        "go_app": "🔬 Перейти к приложению Tablet"
    },
    "en": {
        "welcome": "👋 Hello! Please choose a language 👇",
        "go_app": "🔬 Go to Tablet App"
    }
}

# 🔧 Bot va Dispatcher
app = FastAPI()
bot = telegram.Bot(token=TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None)

# 🔘 /start komandasi
def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(flag, callback_data=code)] for flag, code in languages.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("🇺🇿 🇷🇺 🇬🇧\nTilni tanlang / Choose language / Выберите язык:", reply_markup=reply_markup)

# 🔘 Til tanlanganda
def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang_code = query.data

    text = translations[lang_code]["welcome"]
    button_text = translations[lang_code]["go_app"]
    button = [[InlineKeyboardButton(button_text, url=TABLET_APP_URL)]]
    reply_markup = InlineKeyboardMarkup(button)

    query.edit_message_text(text=text, reply_markup=reply_markup)

# 🔌 Handlers qo‘shish
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(language_selected))

# 📥 Webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return {"ok": True}
