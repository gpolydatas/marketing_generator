#!/bin/bash

# Marketing Content Generator - Combined Setup & Start Script
# Run with: ./start.sh

set -e  # Exit on any error

echo "=========================================="
echo "🎨 Marketing Content Generator"
echo "=========================================="
echo ""

# Function to setup the application
setup_application() {
    echo "🔧 Setting up application..."
    
    # Check Python version
    python_version=$(python3 --version 2>&1 || echo "Python3 not found")
    echo "✓ Python: $python_version"

    # Create necessary directories
    echo ""
    echo "📁 Creating directories..."
    mkdir -p outputs
    mkdir -p static
    echo "✅ Directories created"

    # Check if secrets file exists
    if [ ! -f "fastagent.secrets.yaml" ]; then
        echo ""
        echo "⚠️  IMPORTANT: API keys configuration required!"
        echo "=========================================="
        echo "Please create fastagent.secrets.yaml with your API keys:"
        echo ""
        echo "Example structure:"
        cat << 'EOF'
# FastAgent Secrets Configuration
openai:
  api_key: sk-your-openai-key-here
anthropic:
  api_key: sk-your-anthropic-key-here  
google:
  api_key: your-google-key-here
weather:
  api_key: your-openweather-key-here

# Optional MCP server environment variables
mcp:
  servers:
    banner_tools:
      env:
        OPENAI_API_KEY: sk-your-openai-key-here
        ANTHROPIC_API_KEY: sk-your-anthropic-key-here
    video_tools:
      env:
        GOOGLE_API_KEY: your-google-key-here
        RUNWAYML_API_KEY: your-runwayml-key-here
EOF
        echo ""
        echo "You can copy from template if available:"
        echo "  cp fastagent.secrets.yaml.template fastagent.secrets.yaml"
        echo "Then edit with your actual API keys"
        echo ""
        read -p "Continue without API keys? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Exiting... Please configure API keys and run again."
            exit 1
        fi
    else
        echo "✅ Secrets file found: fastagent.secrets.yaml"
    fi

    echo ""
    echo "✅ Setup complete!"
}

# Function to start the application
start_application() {
    echo ""
    echo "=========================================="
    echo "🚀 Starting Marketing Content Generator"
    echo "=========================================="
    echo ""
    echo "🌐 Backend API: http://localhost:8000"
    echo "📖 API Docs:    http://localhost:8000/docs"
    echo "🎨 Frontend:    http://localhost:8501"
    echo ""
    echo "Starting services..."
    echo ""

    # Check if we're in the right directory
    if [ ! -f "fastapi_server.py" ] || [ ! -f "streamlit_app.py" ]; then
        echo "❌ Error: Required files not found!"
        echo "Please run this script from the marketing_generator directory"
        exit 1
    fi

    # Function to handle cleanup on exit
    cleanup() {
        echo ""
        echo "🛑 Shutting down services..."
        kill $FASTAPI_PID 2>/dev/null || true
        kill $STREAMLIT_PID 2>/dev/null || true
        echo "✅ Services stopped"
        exit 0
    }

    # Set trap to cleanup on exit
    trap cleanup SIGINT SIGTERM

    # Start FastAPI backend
    echo "Starting FastAPI backend..."
    uv run python fastapi_server.py &
    FASTAPI_PID=$!
    
    # Wait a bit for backend to start
    sleep 3
    
    # Check if backend started successfully
    if ! kill -0 $FASTAPI_PID 2>/dev/null; then
        echo "❌ Failed to start FastAPI backend"
        exit 1
    fi
    
    echo "✅ Backend started (PID: $FASTAPI_PID)"

    # Start Streamlit frontend
    echo "Starting Streamlit frontend..."
    uv run streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &
    STREAMLIT_PID=$!
    
    # Wait a bit for frontend to start
    sleep 2
    
    # Check if frontend started successfully
    if ! kill -0 $STREAMLIT_PID 2>/dev/null; then
        echo "❌ Failed to start Streamlit frontend"
        kill $FASTAPI_PID 2>/dev/null
        exit 1
    fi
    
    echo "✅ Frontend started (PID: $STREAMLIT_PID)"

    echo ""
    echo "=========================================="
    echo "🎉 Application is running!"
    echo "=========================================="
    echo ""
    echo "📱 Access points:"
    echo "   Backend API:    http://localhost:8000"
    echo "   API Docs:       http://localhost:8000/docs"
    echo "   Frontend UI:    http://localhost:8501"
    echo ""
    echo "🛑 Press Ctrl+C to stop all services"
    echo ""

    # Wait for both processes
    wait $FASTAPI_PID $STREAMLIT_PID
}

# Main execution
main() {
    # Check if setup is needed
    if [ ! -d "outputs" ] || [ ! -d "static" ] || ! command_exists uv; then
        setup_application
    else
        echo "✅ Application already set up"
    fi

    # Start the application
    start_application
}

# Run main function
main
