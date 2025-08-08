import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
from langdetect import detect

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def smart_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    try:
        lang = detect(text)
        print(f"Received message: {text}")
        if lang == 'he':
            translated = GoogleTranslator(source='iw', target='ru').translate(text)
            await update.message.reply_text(f"🇮🇱 → 🇷🇺: {translated}")
        elif lang == 'ru':
            translated = GoogleTranslator(source='ru', target='iw').translate(text)
            await update.message.reply_text(f"🇷🇺 → 🇮🇱: {translated}")
        else:
            print(f"Ignored language: {lang}")
    except Exception as e:
        print(f"Translation failed: {e}")
        await update.message.reply_text("❌ Translation failed.")

if __name__ == '__main__':
    print(f"BOT_TOKEN: {BOT_TOKEN}")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_translate))
    app.run_polling()