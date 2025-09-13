from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def smart_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    try:
        # Use GoogleTranslator's detection
        lang = GoogleTranslator().detect(text)
        print(f"Detected language: {lang} | Text: {text}")

        if lang not in ["he", "ru"]:
            await update.message.reply_text("⚠️ Language not supported.")
            return

        source_lang = "he" if lang in ["he", "iw"] else "ru"
        target_lang = "ru" if source_lang == "he" else "he"

        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        await update.message.reply_text(f"{source_lang} → {target_lang}: {translated}")

    except Exception as e:
        print(f"Translation failed: {repr(e)}")
        await update.message.reply_text(f"❌ Translation failed: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_translate))
    app.run_polling()
