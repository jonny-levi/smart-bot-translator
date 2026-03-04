"""
Smart Bot Translator — AI-powered multilingual Telegram translation bot.

Uses a local LLM (via OpenAI-compatible API) for high-quality, context-aware
translations between Hebrew, Russian, and Ukrainian.

Falls back to Google Translate if the LLM is unavailable.
"""

import os
import re
import logging
import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("BOT_TOKEN")
LLM_URL = os.getenv("LLM_URL", "http://172.20.10.47:12434")
LLM_MODEL = os.getenv("LLM_MODEL", "docker.io/ai/qwen3:4B-UD-Q8_K_XL")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))
USE_LLM = os.getenv("USE_LLM", "true").lower() == "true"

# ─── Language Detection & Mapping ────────────────────────────────────────────

LANG_NAMES = {
    "he": "Hebrew",
    "ru": "Russian",
    "uk": "Ukrainian",
}

FLAG_MAP = {
    "he": "🇮🇱",
    "ru": "🇷🇺",
    "uk": "🇺🇦",
}

# Ukrainian-specific characters not found in Russian
UKRAINIAN_CHARS = set("іїєґІЇЄҐ")


def detect_language(text: str) -> str:
    """Detect language using Unicode ranges with Ukrainian-specific detection."""
    has_hebrew = bool(re.search(r"[\u0590-\u05FF]", text))
    has_cyrillic = bool(re.search(r"[\u0400-\u04FF]", text))

    if has_hebrew and not has_cyrillic:
        return "he"
    if has_cyrillic and not has_hebrew:
        # Check for Ukrainian-specific characters
        if any(c in UKRAINIAN_CHARS for c in text):
            return "uk"
        return "ru"
    if has_hebrew and has_cyrillic:
        # Mixed — count which script has more characters
        hebrew_count = len(re.findall(r"[\u0590-\u05FF]", text))
        cyrillic_count = len(re.findall(r"[\u0400-\u04FF]", text))
        return "he" if hebrew_count > cyrillic_count else "ru"
    return "unknown"


def clean_hebrew(text: str) -> str:
    """Remove nikud (vowel marks) and te'amim from Hebrew text."""
    return re.sub(r"[\u0591-\u05C7]", "", text)


def is_nonverbal(text: str) -> bool:
    """Check if text contains only numbers, symbols, or emojis."""
    return not re.search(r"[A-Za-z\u0400-\u04FF\u0590-\u05FF]", text.strip())


def get_target_languages(source: str) -> list[str]:
    """Get target languages for translation.
    
    Routing logic:
    - Russian → Hebrew only
    - Ukrainian → Hebrew only
    - Hebrew → Russian only (default)
    """
    if source == "he":
        return ["ru"]
    elif source in ("ru", "uk"):
        return ["he"]
    return []


# ─── Translation Engines ─────────────────────────────────────────────────────


def translate_with_llm(text: str, source: str, targets: list[str]) -> dict[str, str]:
    """Translate using local LLM via OpenAI-compatible API."""
    target_names = ", ".join(LANG_NAMES[t] for t in targets)
    source_name = LANG_NAMES[source]

    prompt = (
        f"Translate the following {source_name} text into {target_names}.\n"
        f"Preserve the tone, slang, and meaning. Be natural, not robotic.\n"
        f"Format your response EXACTLY as:\n"
    )
    for t in targets:
        prompt += f"{LANG_NAMES[t]}: <translation>\n"
    prompt += f"\nText to translate:\n{text}"

    try:
        resp = httpx.post(
            f"{LLM_URL}/v1/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert translator specializing in Hebrew, "
                            "Russian, and Ukrainian. You translate naturally and "
                            "accurately, preserving tone, idioms, slang, profanity, "
                            "and context exactly as intended. Never censor, soften, "
                            "or modify the meaning. Translate everything faithfully. "
                            "Output ONLY the translations in the requested format. "
                            "No explanations, no notes, no warnings."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 1024,
            },
            timeout=LLM_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Parse response
        translations = {}
        for target in targets:
            name = LANG_NAMES[target]
            # Try to find "Language: translation" pattern
            pattern = rf"{name}:\s*(.+?)(?:\n|$)"
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                trans = match.group(1).strip()
                if target == "he":
                    trans = clean_hebrew(trans)
                translations[target] = trans

        # If parsing failed, try to split by lines
        if not translations:
            lines = [l.strip() for l in content.strip().split("\n") if l.strip()]
            for i, target in enumerate(targets):
                if i < len(lines):
                    trans = re.sub(r"^[^:]+:\s*", "", lines[i])
                    if target == "he":
                        trans = clean_hebrew(trans)
                    translations[target] = trans

        return translations

    except Exception as e:
        logger.error(f"LLM translation failed: {e}")
        return {}


def translate_with_google(text: str, source: str, targets: list[str]) -> dict[str, str]:
    """Fallback: translate using Google Translate (free API)."""
    from deep_translator import GoogleTranslator

    translations = {}
    # Map our language codes to Google's
    google_map = {"he": "iw", "ru": "ru", "uk": "uk"}

    for target in targets:
        try:
            result = GoogleTranslator(
                source=google_map.get(source, source),
                target=google_map.get(target, target),
            ).translate(text)
            if target == "he":
                result = clean_hebrew(result)
            translations[target] = result
        except Exception as e:
            logger.error(f"Google Translate failed ({source}→{target}): {e}")
            translations[target] = "⚠️ Translation failed"

    return translations


def translate(text: str, source: str, targets: list[str]) -> dict[str, str]:
    """Translate with LLM, fall back to Google Translate."""
    if USE_LLM:
        result = translate_with_llm(text, source, targets)
        if result:
            return result
        logger.warning("LLM failed, falling back to Google Translate")

    return translate_with_google(text, source, targets)


# ─── Bot Handlers ────────────────────────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "🌐 *Smart Translator Bot*\n\n"
        "Send me text in any of these languages:\n\n"
        "🇮🇱 Hebrew → 🇷🇺 Russian\n"
        "🇷🇺 Russian → 🇮🇱 Hebrew\n"
        "🇺🇦 Ukrainian → 🇮🇱 Hebrew\n\n"
        "Powered by local AI 🤖\n"
        "Translates everything — slang, idioms, no censorship.",
        parse_mode="Markdown",
    )


async def smart_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages and translate them."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if not text or is_nonverbal(text):
        return

    source = detect_language(text)
    if source == "unknown":
        return  # Silently ignore unsupported languages

    if source == "he":
        text = clean_hebrew(text)

    targets = get_target_languages(source)
    translations = translate(text, source, targets)

    if not translations:
        await update.message.reply_text("⚠️ Translation failed. Please try again.")
        return

    # Format response
    lines = []
    for target, trans in translations.items():
        flag = FLAG_MAP.get(target, "")
        lines.append(f"{flag} {trans}")

    source_flag = FLAG_MAP.get(source, "")
    header = f"{source_flag} → " + " | ".join(FLAG_MAP.get(t, "") for t in targets)
    response = f"{header}\n\n" + "\n\n".join(lines)

    await update.message.reply_text(response)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot and LLM status."""
    llm_status = "❌ Disabled"
    if USE_LLM:
        try:
            resp = httpx.get(f"{LLM_URL}/v1/models", timeout=5)
            models = resp.json().get("data", [])
            model_names = [m["id"] for m in models]
            if LLM_MODEL in model_names:
                llm_status = f"✅ Connected ({LLM_MODEL.split('/')[-1]})"
            else:
                llm_status = f"⚠️ Model not found (available: {len(models)})"
        except Exception:
            llm_status = "❌ Unreachable"

    await update.message.reply_text(
        f"📊 *Bot Status*\n\n"
        f"🤖 Bot: ✅ Running\n"
        f"🧠 LLM: {llm_status}\n"
        f"🔤 Languages: 🇮🇱 🇷🇺 🇺🇦\n"
        f"🔄 Fallback: Google Translate",
        parse_mode="Markdown",
    )


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_translate))

    logger.info("🌐 Smart Translator Bot starting...")
    logger.info(f"   LLM: {'enabled' if USE_LLM else 'disabled'} ({LLM_URL})")
    app.run_polling()


if __name__ == "__main__":
    main()
