import os
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator, MyMemoryTranslator

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Flags for display
FLAG_MAP = {
    "iw": "🇮🇱",  # Hebrew
    "ru": "🇷🇺",  # Russian
}

# Detect Hebrew vs Russian using Unicode ranges
def detect_language(text: str) -> str:
    if re.search(r'[\u0590-\u05FF]', text):  # Hebrew Unicode range
        return "iw"
    elif re.search(r'[\u0400-\u04FF]', text):  # Cyrillic range
        return "ru"
    return "unknown"

# Normalize Hebrew: remove nikud/te'amim
def clean_hebrew(text: str) -> str:
    return re.sub(r'[\u0591-\u05C7]', '', text)

# Fallback translator
def translate_text(text: str, source: str, target: str) -> str:
    try:
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception as e:
        print(f"⚠️ Google failed: {e}, using MyMemory...")
        return MyMemoryTranslator(source=source, target=target).translate(text)

async def smart_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    source_lang = detect_language(text)

    if source_lang == "unknown":
        await update.message.reply_text("⚠️ Only Hebrew ↔ Russian supported.")
        return

    if source_lang == "iw":
        text = clean_hebrew(text)  # normalize Hebrew
        target_lang = "ru"
    else:  # ru
        target_lang = "iw"

    translated = translate_text(text, source_lang, target_lang)

    flag_src = FLAG_MAP.get(source_lang, "")
    flag_dst = FLAG_MAP.get(target_lang, "")

    await update.message.reply_text(
        f"{flag_src} → {flag_dst}\n{translated}"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_translate))
    app.run_polling()
