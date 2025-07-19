#!/bin/bash
# Activate Python virtual environment for CivitAI Tools

echo "🐍 Activating Python virtual environment..."
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo "📦 Python version: $(python --version)"
echo "📦 Pip version: $(pip --version)"
echo ""
echo "💡 To deactivate, run: deactivate"
echo "💡 To install dependencies: pip install -r requirements.txt"
echo ""

# Keep shell open
$SHELL