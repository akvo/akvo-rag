#!/bin/bash
# Create and set up a virtual environment for RAG evaluation

# Check if we're inside the container
if [ ! -f "/.dockerenv" ]; then
  echo "This script should be run inside the Docker container"
  exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "/app/RAG_evaluation/venv" ]; then
  echo "Creating virtual environment..."
  python -m venv /app/RAG_evaluation/venv
fi

# Activate virtual environment and install dependencies
echo "Installing dependencies in virtual environment..."
source /app/RAG_evaluation/venv/bin/activate
pip install --upgrade pip
pip install -r /app/RAG_evaluation/requirements.txt

echo "Virtual environment setup complete."
echo "To activate: source /app/RAG_evaluation/venv/bin/activate"