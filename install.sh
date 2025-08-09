#!/usr/bin/env bash
# Install the required Python packages for the project.
# This script assumes you have pip available in your environment.
# Run it from the root of the repository:
#   bash install.sh

# Update pip to the latest version (optional but recommended)
pip install --upgrade pip

# Install dependencies from requirements.txt
pip install -r requirements.txt

echo "✅ Installation complete."
