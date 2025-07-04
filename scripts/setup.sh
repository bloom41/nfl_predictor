#!/bin/bash

# NFL Predictor Development Setup Script

set -e  # Exit on any error

echo "🏈 NFL Predictor - Development Setup"
echo "===================================="

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ required. Current version: $(node --version)"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f2)
if [ "$PYTHON_VERSION" -lt 8 ]; then
    echo "❌ Python 3.8+ required. Current version: $(python3 --version)"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend-ts
npm install
echo "✅ Backend dependencies installed"

# Build backend
echo "🔨 Building backend..."
npm run build
echo "✅ Backend built successfully"

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd ../frontend/client
npm install
echo "✅ Frontend dependencies installed"

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
cd ../..
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt
echo "✅ Python dependencies installed"

# Setup database (optional)
echo "🗄️  Database setup..."
if command -v psql &> /dev/null; then
    echo "PostgreSQL detected. You can run database migrations manually:"
    echo "  python manage.py migrate"
    echo "  cd backend-ts && npm run db:migrate"
else
    echo "PostgreSQL not found. Using SQLite fallback."
fi

# Create environment files if they don't exist
echo "⚙️  Setting up environment files..."

# Backend .env
if [ ! -f "backend-ts/.env" ]; then
    cat > backend-ts/.env << EOF
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/nfl_predictor
SQLITE_DATABASE=./nfl_predictor.db

# API Configuration
PORT=3001
NODE_ENV=development
API_BASE_URL=http://localhost:3001

# ML Service
PYTHON_ML_SERVICE_URL=http://localhost:5000
PYTHON_ML_SERVICE_TIMEOUT=30000

# Security
CORS_ORIGIN=http://localhost:3000
EOF
    echo "✅ Backend .env created"
fi

# Frontend .env
if [ ! -f "frontend/client/.env" ]; then
    cat > frontend/client/.env << EOF
# API Configuration
REACT_APP_API_BASE_URL=http://localhost:3001
REACT_APP_API_TIMEOUT=30000

# Environment
REACT_APP_ENV=development
EOF
    echo "✅ Frontend .env created"
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "🚀 Quick Start Commands:"
echo "======================"
echo ""
echo "1. Start Backend (Terminal 1):"
echo "   cd backend-ts && npm run dev"
echo ""
echo "2. Start Frontend (Terminal 2):"
echo "   cd frontend/client && npm start"
echo ""
echo "3. Start ML Service (Terminal 3):"
echo "   source venv/bin/activate && python app.py"
echo ""
echo "🌐 URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:3001"
echo "   ML API:   http://localhost:5000"
echo ""
echo "📚 Documentation:"
echo "   Architecture: docs/ARCHITECTURE.md"
echo "   Development:  docs/DEVELOPMENT.md"
echo "   API Reference: docs/API.md"
echo ""
echo "Happy coding! 🏈⚡"