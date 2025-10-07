import os
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator, MyMemoryTranslator

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Flags
FLAG_MAP = {
    "iw": "🇮🇱",  # Hebrew
    "ru": "🇷🇺",  # Russian
    "uk": "🇺🇦",  # Ukrainian
}

# Detect language by Unicode ranges
def detect_language(text: str) -> str:
    if re.search(r'[\u0590-\u05FF]', text):
        return "iw"
    elif re.search(r'[\u0400-\u04FF]', text):
        return "ru"
    elif re.search(r'[\u0400-\u04FF]', text):  # Cyrillic range, treat Ukrainian as ru
        return "uk"
    return "unknown"

# Remove nikud (vowel marks) and te'amim from Hebrew text
def clean_hebrew(text: str) -> str:
    return re.sub(r'[\u0591-\u05C7]', '', text)

# Check if text contains only numbers/symbols/emojis (no letters)
def is_nonverbal(text: str) -> bool:
    # Remove spaces and check if anything left is not a letter
    stripped = text.strip()
    # Regex: contains no Hebrew, Latin, or Cyrillic letters
    return not re.search(r'[A-Za-z\u0400-\u04FF\u0590-\u05FF]', stripped)

# Translate with fallback
def translate_text(text: str, source: str, target: str) -> str:
    try:
        translated = GoogleTranslator(source=source, target=target).translate(text)
        # Clean Hebrew vowels if translation is to Hebrew
        if target == "iw":
            translated = clean_hebrew(translated)
        return translated
    except Exception as e:
        print(f"⚠️ GoogleTranslator failed: {e}, using MyMemory...")
        try:
            translated = MyMemoryTranslator(source=source, target=target).translate(text)
            if target == "iw":
                translated = clean_hebrew(translated)
            return translated
        except Exception as e2:
            print(f"❌ MyMemory failed: {e2}")
            return "Translation failed"

# Split long texts into smaller chunks
def chunk_text(text: str, max_len: int = 200) -> list[str]:
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) + 1 <= max_len:
            current += " " + s if current else s
        else:
            chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks

async def smart_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if not text:
        return

    # Skip numbers, symbols, or emoji-only messages
    if is_nonverbal(text):
        return  # silently ignore

    source_lang = detect_language(text)
    if source_lang == "unknown":
        await update.message.reply_text("⚠️ Only Hebrew, Russian, and Ukrainian are supported.")
        return

    if source_lang == "iw":
        text = clean_hebrew(text)
        target_lang = "ru"
    else:
        target_lang = "iw"

    # Translate in chunks
    chunks = chunk_text(text)
    translated_chunks = [translate_text(chunk, source_lang, target_lang) for chunk in chunks]
    translated = " ".join(translated_chunks)

    flag_src = FLAG_MAP.get(source_lang, "")
    flag_dst = FLAG_MAP.get(target_lang, "")

    await update.message.reply_text(f"{flag_src} → {flag_dst}\n{translated}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_translate))
    app.run_polling()
