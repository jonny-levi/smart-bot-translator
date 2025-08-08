from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from googletrans import Translator

translator = Translator()

# Replace with your actual bot token
BOT_TOKEN = "YOUR_BOT_TOKEN"

async def smart_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    source_lang = translator.detect(text).lang

    if source_lang == 'he':
        translated = translator.translate(text, src='he', dest='ru')
        await update.message.reply_text(f"🇮🇱 → 🇷🇺: {translated.text}")
    elif source_lang == 'ru':
        translated = translator.translate(text, src='ru', dest='he')
        await update.message.reply_text(f"🇷🇺 → 🇮🇱: {translated.text}")
    else:
        pass

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_translate))
    app.run_polling()
