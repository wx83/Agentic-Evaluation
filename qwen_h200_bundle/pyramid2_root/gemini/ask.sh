#!/usr/bin/env bash
# Usage: ./ask.sh "your prompt here"
#        echo "long text" | ./ask.sh          # reads stdin if no arg
set -euo pipefail

: "${GEMINI_API_KEY:?export GEMINI_API_KEY first (https://aistudio.google.com/apikey)}"
MODEL="${GEMINI_MODEL:-gemini-2.5-flash}"

PROMPT="${1:-$(cat)}"

curl -sS "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent" \
  -H "x-goog-api-key: ${GEMINI_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg p "$PROMPT" '{
        contents: [{ parts: [{ text: $p }] }],
        generationConfig: { temperature: 0.7, maxOutputTokens: 2048 }
      }')" \
| jq -r '.candidates[0].content.parts[]?.text // ("ERROR: " + (.error.message // tojson))'
