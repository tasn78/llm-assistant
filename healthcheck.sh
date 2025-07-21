#!/bin/bash
STATUS=$(curl -sk https://127.0.0.1/web --max-time 10 | grep 'LLM Text Summarizer')
if [ -z "$STATUS" ]; then
    echo "LLM app down at $(date)" | mail -s "LLM Service DOWN" talonxv.15@gmail.com
fi
