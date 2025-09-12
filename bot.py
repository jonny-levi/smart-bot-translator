import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
from langdetect import detect

BOT_TOKEN = os.getenv("BOT_TOKEN")

LANG_MAP = {
    'he': 'iw',  # Hebrew fix for Google Translate
    'iw': 'iw',
    'ru': 'ru',
}

async def smart_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    try:
        lang = detect(text)
        print(f"Detected language: {lang} | Text: {text}")

        if lang not in LANG_MAP:
            print(f"Ignored language: {lang}")
            return

        source_lang = LANG_MAP[lang]
        target_lang = 'ru' if source_lang == 'iw' else 'iw'  # Swap target

        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        await update.message.reply_text(f"{source_lang} → {target_lang}: {translated}")

    except Exception as e:
        print(f"Translation failed: {repr(e)}")
        await update.message.reply_text(f"❌ Translation failed: {e}")

if __name__ == '__main__':
    print(f"BOT_TOKEN: {BOT_TOKEN}")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_translate))
    app.run_polling()
