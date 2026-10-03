#!/bin/zsh
cd "$(dirname "$0")" || exit 1
if [[ -z "${DEEPL_AUTH_KEY:-}" ]]; then
  read -rs 'DEEPL_AUTH_KEY?Paste your DeepL API Free key, then press Return: '
  echo
  export DEEPL_AUTH_KEY
fi
if [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
  read -rs 'ELEVENLABS_API_KEY?Paste your ElevenLabs API key, then press Return: '
  echo
  export ELEVENLABS_API_KEY
fi
printf 'Open http://127.0.0.1:8787 in your browser. Keep this terminal open.\n'
exec .venv/bin/python -m moin_studio
