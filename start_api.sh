#!/bin/bash

echo "=========================================="
echo "Marketing Content Generator API"
echo "=========================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1)
echo "✓ Python: $python_version"

# Check if required packages are installed
echo ""
echo "Checking dependencies..."

packages=("fastapi" "uvicorn" "requests" "openai")
missing=()

for package in "${packages[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo "✓ $package"
    else
        echo "✗ $package (missing)"
        missing+=("$package")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    echo ""
    echo "⚠️  Missing dependencies detected!"
    echo "Install with: pip install -r requirements_api.txt"
    echo ""
    read -p "Install now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install -r requirements_api.txt
    else
        echo "Exiting..."
        exit 1
    fi
fi

# Check environment variables
echo ""
echo "Checking environment variables..."

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set"
else
    echo "✓ OPENAI_API_KEY"
fi

if [ -z "$OPENWEATHER_API_KEY" ]; then
    echo "⚠️  OPENWEATHER_API_KEY not set (weather features disabled)"
else
    echo "✓ OPENWEATHER_API_KEY"
fi

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  GOOGLE_API_KEY not set (Veo video generation disabled)"
else
    echo "✓ GOOGLE_API_KEY"
fi

# Create outputs directory if it doesn't exist
mkdir -p outputs

echo ""
echo "=========================================="
echo "Starting FastAPI Server..."
echo "=========================================="
echo ""
echo "🌐 API: http://localhost:8000"
echo "📖 Docs: http://localhost:8000/docs"
echo "🎨 Demo: Open api_demo.html in your browser"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the server
python3 fastapi_server.py