#!/bin/bash
# Export required variables for content processing and AI summary
# These are read via os.getenv() and not through Settings class
export FETCH_PAGE_CONTENT_ENABLED=true
export SUMMARY_ENABLED=true
export SUMMARY_PROVIDER=openai
export SUMMARY_MODEL=gpt-4o-mini
export SUMMARY_MAX_TOKENS=1200
export SUMMARY_INPUT_TOKEN_LIMIT=6000

python3 main.py
