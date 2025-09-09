#!/bin/bash

# StudyMate Startup Script
echo "🚀 Starting StudyMate - AI Study Companion"
echo "==========================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "❌ pip is not installed. Please install pip."
    exit 1
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Installing dependencies..."
    python3 -m pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo "✅ Dependencies installed successfully!"
    else
        echo "❌ Failed to install dependencies. Please check the error messages above."
        exit 1
    fi
else
    echo "❌ requirements.txt not found. Please make sure you're in the correct directory."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📋 Creating .env file from template..."
        cp .env.example .env
        echo "⚠️  Please edit .env file with your API keys (optional for basic functionality)"
    fi
fi

# Start the application
echo "🎯 Starting StudyMate application..."
echo "📱 The app will open in your browser at http://localhost:8501"
echo "🛑 Press Ctrl+C to stop the application"
echo ""

python3 -m streamlit run app.py