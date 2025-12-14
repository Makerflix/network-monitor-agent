#!/bin/bash
# Setup script for Network Monitor Agent

set -e

echo "================================"
echo "Network Monitor Agent Setup"
echo "================================"
echo

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "Error: Python 3 not found"; exit 1; }

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Make main.py executable
chmod +x main.py

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo
    echo "WARNING: ANTHROPIC_API_KEY environment variable not set"
    echo "Please set it before running the agent:"
    echo "  export ANTHROPIC_API_KEY='your-api-key-here'"
    echo
fi

# Test configuration
echo "Testing configuration..."
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))" && echo "✓ Config file is valid"

echo
echo "================================"
echo "Setup complete!"
echo "================================"
echo
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Set your API key: export ANTHROPIC_API_KEY='your-key'"
echo "3. Edit config.yaml to customize settings"
echo "4. Run a test: python3 main.py --test"
echo "5. Run continuously: python3 main.py"
echo
echo "For production use, consider setting up as a systemd service."
echo "See README.md for details."
echo
