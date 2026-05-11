# Smart Bot Translator

## Overview

Smart Bot Translator is a Telegram bot for natural multilingual translation between Hebrew, Russian, and Ukrainian. It uses a local OpenAI-compatible LLM endpoint for context-aware translation and falls back to Google Translate when the LLM is disabled or unavailable.

## Features

- Telegram polling bot built with `python-telegram-bot`.
- Script-based language detection for Hebrew, Russian, and Ukrainian.
- Translation routing:
  - Hebrew → Russian
  - Russian → Hebrew
  - Ukrainian → Hebrew
- Hebrew nikud/te'amim cleanup for cleaner output.
- Local LLM translation via `/v1/chat/completions`.
- Google Translate fallback through `deep-translator`.
- `/start` and `/status` commands.
- Docker image and Kubernetes deployment/service manifests.

## Architecture / Structure

```text
bot.py                Bot entrypoint, language detection, translation handlers
requirements.txt      Python dependencies
Dockerfile            Container image for the bot
k8s/deployment.yaml   Kubernetes Deployment using a BOT_TOKEN Secret
k8s/service.yaml      Optional Kubernetes Service manifest
.github/workflows/    Infrastructure/deployment workflow
```

Runtime flow:

1. Telegram sends a text message to the bot.
2. `bot.py` detects the source language by Unicode script.
3. The bot calls the configured local LLM endpoint when `USE_LLM=true`.
4. If the LLM call fails, Google Translate is used as fallback.
5. The translation is posted back to the Telegram chat.

## Prerequisites

- Python 3.11+ recommended.
- A Telegram bot token from BotFather.
- Optional: an OpenAI-compatible local LLM endpoint.
- Optional for deployment: Docker and Kubernetes.

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export BOT_TOKEN="<telegram-bot-token>"
export LLM_URL="http://<llm-host>:12434"
export LLM_MODEL="docker.io/ai/qwen3:4B-UD-Q8_K_XL"
python bot.py
```

To run without the local LLM and rely on Google Translate fallback:

```bash
export USE_LLM=false
python bot.py
```

## Configuration

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `BOT_TOKEN` | Yes | none | Telegram bot token. |
| `LLM_URL` | No | local lab endpoint in code | Base URL for an OpenAI-compatible LLM API. Override for your environment. |
| `LLM_MODEL` | No | `docker.io/ai/qwen3:4B-UD-Q8_K_XL` | Model ID sent to the LLM endpoint. |
| `LLM_TIMEOUT` | No | `120` | LLM request timeout in seconds. |
| `USE_LLM` | No | `true` | Set to `false` to skip LLM calls and use Google Translate. |

> Do not commit real Telegram tokens or private endpoint details. Use environment variables and Kubernetes Secrets.

## Deployment / Operations

### Docker

```bash
docker build -t smart-bot-translator:latest .
docker run --rm \
  -e BOT_TOKEN="<telegram-bot-token>" \
  -e LLM_URL="http://<llm-host>:12434" \
  smart-bot-translator:latest
```

### Kubernetes

Create the bot token secret before applying the manifests:

```bash
kubectl create secret generic smart-bot-translator-secrets \
  --from-literal=BOT_TOKEN="<telegram-bot-token>"
kubectl apply -f k8s/
```

Operational checks:

```bash
kubectl get pods
kubectl logs deploy/smart-bot-translator
```

Use `/status` in Telegram to verify bot and LLM connectivity.

## Security Notes

- Keep `BOT_TOKEN` in a secret manager or Kubernetes Secret.
- Treat translated text as user-generated content; avoid logging sensitive messages in production.
- The LLM endpoint may receive private chat text. Run it in a trusted network and apply access controls.
- The bot uses long polling; only one active instance should poll the same Telegram token at a time.

## Author

Jonny Levi — [jonny-levi](https://github.com/jonny-levi)
