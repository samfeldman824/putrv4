#!/bin/bash
# Start script for Render deployment
# This matches the Render start command

exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
