import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
from langdetect import detect

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Normalize Hebrew codes
def normalize_lang(lang: str) -> str:
    if lang in ["iw", "he"]:
        return "he"
    return lang

# Decide target language explicitly
def get_target_lang(source_lang: str) -> str:
    if source_lang == "ru":
        return "he"
    elif source_lang == "he":
        return "ru"
    return "ru"

# Flags for display
FLAG_MAP = {
    "he": "🇮🇱",
    "ru": "🇷🇺",
}

async def smart_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    try:
        detected = detect(text)
        source_lang = normalize_lang(detected)
        print(f"Detected: {detected} (normalized: {source_lang}) | Text: {text}")

        if source_lang not in ["he", "ru"]:
            await update.message.reply_text("⚠️ Only Hebrew ↔ Russian supported.")
            return

        target_lang = get_target_lang(source_lang)
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)

        flag_src = FLAG_MAP.get(source_lang, "")
        flag_dst = FLAG_MAP.get(target_lang, "")

        await update.message.reply_text(
            f"{flag_src} → {flag_dst}\n{translated}"
        )

    except Exception as e:
        print(f"Translation failed: {repr(e)}")
        await update.message.reply_text(f"❌ Translation failed: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_translate))
    app.run_polling()
