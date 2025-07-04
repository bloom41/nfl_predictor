#!/bin/bash

# NFL Predictor Cleanup Script
# Removes temporary files, build artifacts, and caches

set -e

echo "🧹 NFL Predictor - Cleanup Script"
echo "================================="

# Function to safely remove directory/file if it exists
safe_remove() {
    if [ -e "$1" ]; then
        echo "🗑️  Removing: $1"
        rm -rf "$1"
    fi
}

# Remove build artifacts
echo "📦 Cleaning build artifacts..."
safe_remove "backend-ts/dist/"
safe_remove "backend-ts/coverage/"
safe_remove "frontend/client/build/"
safe_remove "frontend/client/coverage/"

# Remove log files
echo "📋 Cleaning log files..."
safe_remove "*.log"
safe_remove "backend-ts/*.log"
safe_remove "ts_output.log"
safe_remove "flask_output.log"

# Remove cache directories
echo "💾 Cleaning cache files..."
safe_remove "__pycache__/"
safe_remove "src/__pycache__/"
safe_remove "nfl_api/__pycache__/"
safe_remove "*.pyc"
safe_remove ".pytest_cache/"
safe_remove ".coverage"

# Remove temporary databases (optional - comment out to keep data)
echo "🗄️  Database files..."
echo "ℹ️  Keeping database files (comment out to remove):"
echo "   - nfl_predictor.db (SQLite main)"
echo "   - nfl_assistant.db (SQLite backup)"
# safe_remove "nfl_predictor.db*"
# safe_remove "nfl_assistant.db*"

# Remove development artifacts
echo "🔧 Cleaning development files..."
safe_remove ".DS_Store"
safe_remove "Thumbs.db"
safe_remove "*.tmp"
safe_remove "*.temp"

# Remove IDE files (optional)
echo "💻 IDE files..."
echo "ℹ️  Keeping .vscode/ (comment out to remove):"
# safe_remove ".vscode/"

# Clean npm/node caches (optional)
read -p "🧹 Clean npm caches? This will require reinstalling dependencies (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning npm caches..."
    safe_remove "backend-ts/node_modules/"
    safe_remove "frontend/client/node_modules/"
    safe_remove "frontend/node_modules/"
    
    # Also clean package-lock files
    safe_remove "backend-ts/package-lock.json"
    safe_remove "frontend/client/package-lock.json"
    safe_remove "frontend/package-lock.json"
    
    echo "ℹ️  Run 'npm install' in backend-ts/ and frontend/client/ to reinstall"
fi

# Clean Python virtual environment (optional)
read -p "🐍 Clean Python virtual environment? This will require reinstalling dependencies (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning Python virtual environment..."
    safe_remove "venv/"
    safe_remove "nfl_env/"
    safe_remove "nfl_flask_env/"
    echo "ℹ️  Run 'python -m venv venv && source venv/bin/activate && pip install -r requirements.txt' to recreate"
fi

echo ""
echo "✅ Cleanup completed!"
echo ""
echo "📊 Current project size:"
du -sh . 2>/dev/null || echo "Unable to calculate project size"
echo ""
echo "🚀 To rebuild after cleanup:"
echo "   ./scripts/setup.sh"