#!/usr/bin/env python3
"""
FastAPI Server for Marketing Content Generation
With Agent Integration
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os
import asyncio
import json
from datetime import datetime
import shutil
import requests
import uuid

# Import your existing tools
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load API keys from secrets file
def load_api_keys():
    """Load API keys from fastagent.secrets.yaml"""
    import yaml
    secrets_path = os.path.join(os.path.dirname(__file__), 'fastagent.secrets.yaml')
    
    if os.path.exists(secrets_path):
        print(f"✓ Loading API keys from: {secrets_path}")
        with open(secrets_path, 'r') as f:
            secrets = yaml.safe_load(f)
            
            # Set environment variables
            if 'openai' in secrets and 'api_key' in secrets['openai']:
                os.environ['OPENAI_API_KEY'] = secrets['openai']['api_key']
                print("✓ OPENAI_API_KEY loaded from secrets")
            
            if 'anthropic' in secrets and 'api_key' in secrets['anthropic']:
                os.environ['ANTHROPIC_API_KEY'] = secrets['anthropic']['api_key']
                print("✓ ANTHROPIC_API_KEY loaded from secrets")
            
            if 'google' in secrets and 'api_key' in secrets['google']:
                os.environ['GOOGLE_API_KEY'] = secrets['google']['api_key']
                print("✓ GOOGLE_API_KEY loaded from secrets")
            
            if 'weather' in secrets and 'api_key' in secrets['weather']:
                os.environ['OPENWEATHER_API_KEY'] = secrets['weather']['api_key']
                print("✓ OPENWEATHER_API_KEY loaded from secrets")
    else:
        print(f"⚠️  Secrets file not found: {secrets_path}")
        print("⚠️  Will use environment variables instead")
        return False

# Load keys on startup
load_api_keys()

# Create FastAPI app
app = FastAPI(
    title="Marketing Content Generator API",
    description="Generate banners and videos for marketing campaigns with AI",
    version="1.0.0"
)

# Enable CORS for web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure outputs directory exists
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Mount static files for serving the frontend
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mount outputs directory for file downloads
app.mount("/files", StaticFiles(directory=OUTPUTS_DIR), name="files")

# Store conversation sessions
conversation_sessions = {}

# Pydantic models
class BannerRequest(BaseModel):
    campaign_name: str
    brand_name: str
    banner_type: str = "social"
    message: str
    cta: str
    font_family: str = "Arial"
    primary_color: str = "#FFFFFF"
    secondary_color: str = "#000000"
    additional_instructions: Optional[str] = ""
    weather_location: Optional[str] = None
    weather_enabled: bool = False

class VideoRequest(BaseModel):
    campaign_name: str
    brand_name: str
    video_type: str = "standard"
    description: str
    resolution: str = "1080p"
    aspect_ratio: str = "16:9"
    model: str = "veo"

class AgentRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

# Helper function to fetch weather
def fetch_weather(location: str) -> dict:
    """Fetch weather data from OpenWeatherMap API"""
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        return {"error": "OPENWEATHER_API_KEY not set"}
    
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "location": data['name'],
                "temperature": round(data['main']['temp']),
                "condition": data['weather'][0]['main'],
                "description": data['weather'][0]['description'],
                "humidity": data['main']['humidity'],
                "wind_speed": round(data['wind']['speed'] * 3.6)
            }
        else:
            return {"error": f"Weather API error: {response.status_code}"}
    except Exception as e:
        return {"error": f"Failed to fetch weather: {str(e)}"}

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        basic_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Marketing Content Generator</title>
            <style>body { font-family: Arial, sans-serif; margin: 40px; }</style>
        </head>
        <body>
            <h1>Marketing Content Generator</h1>
            <p>Place index.html in the static directory.</p>
            <a href="/docs">API Docs</a>
        </body>
        </html>
        """
        return HTMLResponse(content=basic_html)

# Agent chat endpoint
@app.post("/agent/chat")
async def agent_chat(request: AgentRequest):
    """Handle agent conversation - THIS WILL WORK"""
    try:
        from agent import run_single_prompt
        result = await run_single_prompt(request.message)
        
        return JSONResponse(content={
            "success": True,
            "response": result
        })
        
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        }, status_code=500)

# Weather endpoint
@app.get("/weather/{location}")
async def get_weather(location: str):
    """Get current weather for a location"""
    weather_data = fetch_weather(location)
    if "error" in weather_data:
        raise HTTPException(status_code=400, detail=weather_data["error"])
    return weather_data

# Banner generation endpoint
@app.post("/generate/banner")
async def generate_banner_endpoint(request: BannerRequest):
    """Generate a banner without reference image"""
    try:
        from banner_mcp_server import generate_banner
        
        # Fetch weather if enabled
        weather_data = None
        if request.weather_enabled and request.weather_location:
            weather_data = fetch_weather(request.weather_location)
            if "error" in weather_data:
                weather_data = None
        
        # Generate banner
        result_json = await generate_banner(
            campaign_name=request.campaign_name,
            brand_name=request.brand_name,
            banner_type=request.banner_type,
            message=request.message,
            cta=request.cta,
            additional_instructions=request.additional_instructions,
            reference_image_path="",
            font_family=request.font_family,
            primary_color=request.primary_color,
            secondary_color=request.secondary_color,
            weather_data=weather_data
        )
        
        result = json.loads(result_json)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return JSONResponse(content={
            "success": True,
            "filename": result["filename"],
            "filepath": result["filepath"],
            "download_url": f"/files/{result['filename']}",
            "metadata": result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Banner generation with file upload
@app.post("/generate/banner-with-upload")
async def generate_banner_with_upload(
    campaign_name: str = Form(...),
    brand_name: str = Form(...),
    banner_type: str = Form("social"),
    message: str = Form(...),
    cta: str = Form(...),
    font_family: str = Form("Arial"),
    primary_color: str = Form("#FFFFFF"),
    secondary_color: str = Form("#000000"),
    additional_instructions: str = Form(""),
    weather_enabled: bool = Form(False),
    weather_location: Optional[str] = Form(None),
    reference_image: Optional[UploadFile] = File(None)
):
    """Generate a banner with optional reference image upload"""
    try:
        from banner_mcp_server import generate_banner
        
        # Save uploaded reference image
        reference_image_path = ""
        if reference_image:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reference_{timestamp}_{reference_image.filename}"
            reference_image_path = os.path.join(OUTPUTS_DIR, filename)
            
            with open(reference_image_path, "wb") as f:
                shutil.copyfileobj(reference_image.file, f)
        
        # Fetch weather if enabled
        weather_data = None
        if weather_enabled and weather_location:
            weather_data = fetch_weather(weather_location)
            if "error" in weather_data:
                weather_data = None
        
        # Generate banner
        result_json = await generate_banner(
            campaign_name=campaign_name,
            brand_name=brand_name,
            banner_type=banner_type,
            message=message,
            cta=cta,
            additional_instructions=additional_instructions,
            reference_image_path=reference_image_path,
            font_family=font_family,
            primary_color=primary_color,
            secondary_color=secondary_color,
            weather_data=weather_data
        )
        
        result = json.loads(result_json)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return JSONResponse(content={
            "success": True,
            "filename": result["filename"],
            "filepath": result["filepath"],
            "download_url": f"/files/{result['filename']}",
            "reference_used": bool(reference_image_path),
            "weather_applied": bool(weather_data),
            "metadata": result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Video generation endpoint
@app.post("/generate/video")
async def generate_video_endpoint(request: VideoRequest):
    """Generate a video without input image"""
    try:
        from video_mcp_server import generate_video
        
        # Generate video
        result_json = await generate_video(
            campaign_name=request.campaign_name,
            brand_name=request.brand_name,
            video_type=request.video_type,
            description=request.description,
            resolution=request.resolution,
            aspect_ratio=request.aspect_ratio,
            input_image_path="",
            model=request.model
        )
        
        result = json.loads(result_json)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return JSONResponse(content={
            "success": True,
            "filename": result["filename"],
            "filepath": result["filepath"],
            "download_url": f"/files/{result['filename']}",
            "metadata": result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Video generation with file upload
@app.post("/generate/video-with-upload")
async def generate_video_with_upload(
    campaign_name: str = Form(...),
    brand_name: str = Form(...),
    video_type: str = Form("standard"),
    description: str = Form(...),
    resolution: str = Form("1080p"),
    aspect_ratio: str = Form("16:9"),
    model: str = Form("veo"),
    input_image: Optional[UploadFile] = File(None)
):
    """Generate a video with optional input image upload"""
    try:
        from video_mcp_server import generate_video
        
        # Save uploaded input image
        input_image_path = ""
        if input_image:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"video_input_{timestamp}_{input_image.filename}"
            input_image_path = os.path.join(OUTPUTS_DIR, filename)
            
            with open(input_image_path, "wb") as f:
                shutil.copyfileobj(input_image.file, f)
        
        # Generate video
        result_json = await generate_video(
            campaign_name=campaign_name,
            brand_name=brand_name,
            video_type=video_type,
            description=description,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            input_image_path=input_image_path,
            model=model
        )
        
        result = json.loads(result_json)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return JSONResponse(content={
            "success": True,
            "filename": result["filename"],
            "filepath": result["filepath"],
            "download_url": f"/files/{result['filename']}",
            "input_image_used": bool(input_image_path),
            "metadata": result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List all outputs
@app.get("/outputs")
async def list_outputs():
    """List all generated files"""
    try:
        files = []
        for filename in os.listdir(OUTPUTS_DIR):
            filepath = os.path.join(OUTPUTS_DIR, filename)
            if os.path.isfile(filepath) and not filename.startswith('.'):
                stat = os.stat(filepath)
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "download_url": f"/files/{filename}"
                })
        
        return JSONResponse(content={
            "total": len(files),
            "files": sorted(files, key=lambda x: x['created'], reverse=True)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "outputs_dir": OUTPUTS_DIR,
        "outputs_writable": os.access(OUTPUTS_DIR, os.W_OK)
    }

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 Marketing Content Generator API")
    print("=" * 60)
    print(f"📁 Outputs directory: {OUTPUTS_DIR}")
    print(f"📁 Static directory: {STATIC_DIR}")
    print(f"🌐 Starting server on http://0.0.0.0:8000")
    print(f"📖 API Documentation: http://0.0.0.0:8000/docs")
    print(f"🎨 Web Interface: http://0.0.0.0:8000")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
