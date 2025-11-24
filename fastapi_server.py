# /home/gpoly/Downloads/poc_eng/fastapi_server.py

#!/usr/bin/env python3
"""
SECURED FastAPI Server for Marketing Content Generation
With API Key Authentication and Rate Limiting
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response, Request, Security, Depends
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
import os
import asyncio
import json
from datetime import datetime, timedelta
import shutil
import requests
import uuid
import secrets
from collections import defaultdict
import time

# Import your existing tools
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

# API Key configuration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Load valid API keys from environment or config file
def load_valid_api_keys():
    """Load valid API keys from api_keys.json or environment"""
    keys_file = os.path.join(os.path.dirname(__file__), 'api_keys.json')
    
    # Try to load from file
    if os.path.exists(keys_file):
        try:
            with open(keys_file, 'r') as f:
                config = json.load(f)
                return config.get('valid_keys', {})
        except Exception as e:
            print(f"⚠️  Error loading API keys file: {e}")
    
    # Fallback to environment variable
    env_keys = os.getenv('VALID_API_KEYS', '')
    if env_keys:
        # Format: "key1:user1,key2:user2"
        keys_dict = {}
        for item in env_keys.split(','):
            if ':' in item:
                key, user = item.split(':', 1)
                keys_dict[key.strip()] = {"user": user.strip(), "tier": "standard"}
        return keys_dict
    
    # Default: Generate a sample key for testing
    sample_key = secrets.token_urlsafe(32)
    print(f"⚠️  No API keys configured!")
    print(f"📝 Sample API key for testing: {sample_key}")
    print(f"💡 Create api_keys.json to configure permanent keys")
    
    return {
        sample_key: {
            "user": "test_user",
            "tier": "standard",
            "created": datetime.now().isoformat()
        }
    }

VALID_API_KEYS = load_valid_api_keys()

# Rate limiting configuration
RATE_LIMITS = {
    "free": {"requests_per_minute": 5, "requests_per_hour": 50},
    "standard": {"requests_per_minute": 20, "requests_per_hour": 500},
    "premium": {"requests_per_minute": 100, "requests_per_hour": 5000}
}

# Store request timestamps for rate limiting
request_history = defaultdict(list)

def validate_api_key(api_key: str = Security(api_key_header)) -> dict:
    """Validate API key and return user info"""
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key. Please check your X-API-Key header."
        )
    
    user_info = VALID_API_KEYS[api_key].copy()
    user_info['api_key'] = api_key  # Include key for rate limiting
    return user_info

def check_rate_limit(user_info: dict = Depends(validate_api_key)):
    """Check if user has exceeded rate limits"""
    api_key = user_info['api_key']
    tier = user_info.get('tier', 'standard')
    limits = RATE_LIMITS.get(tier, RATE_LIMITS['standard'])
    
    now = time.time()
    minute_ago = now - 60
    hour_ago = now - 3600
    
    # Clean old requests
    request_history[api_key] = [ts for ts in request_history[api_key] if ts > hour_ago]
    
    # Count requests
    requests_last_minute = sum(1 for ts in request_history[api_key] if ts > minute_ago)
    requests_last_hour = len(request_history[api_key])
    
    # Check limits
    if requests_last_minute >= limits['requests_per_minute']:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limits['requests_per_minute']} requests per minute for {tier} tier"
        )
    
    if requests_last_hour >= limits['requests_per_hour']:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limits['requests_per_hour']} requests per hour for {tier} tier"
        )
    
    # Record this request
    request_history[api_key].append(now)
    
    return user_info

# ============================================================================
# LOAD AI API KEYS
# ============================================================================

def load_ai_api_keys():
    """Load API keys for AI services from fastagent.secrets.yaml"""
    import yaml
    secrets_path = os.path.join(os.path.dirname(__file__), 'fastagent.secrets.yaml')
    
    if os.path.exists(secrets_path):
        print(f"✓ Loading AI API keys from: {secrets_path}")
        with open(secrets_path, 'r') as f:
            secrets = yaml.safe_load(f)
            
            if 'openai' in secrets and 'api_key' in secrets['openai']:
                os.environ['OPENAI_API_KEY'] = secrets['openai']['api_key']
                print("✓ OPENAI_API_KEY loaded")
            
            if 'anthropic' in secrets and 'api_key' in secrets['anthropic']:
                os.environ['ANTHROPIC_API_KEY'] = secrets['anthropic']['api_key']
                print("✓ ANTHROPIC_API_KEY loaded")
            
            if 'google' in secrets and 'api_key' in secrets['google']:
                os.environ['GOOGLE_API_KEY'] = secrets['google']['api_key']
                print("✓ GOOGLE_API_KEY loaded")
            
            if 'weather' in secrets and 'api_key' in secrets['weather']:
                os.environ['OPENWEATHER_API_KEY'] = secrets['weather']['api_key']
                print("✓ OPENWEATHER_API_KEY loaded")
    else:
        print(f"⚠️  Secrets file not found: {secrets_path}")

load_ai_api_keys()

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(
    title="Marketing Content Generator API (Secured)",
    description="Generate banners and videos for marketing campaigns with AI - API Key Required",
    version="2.0.0",
    openapi_version="3.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/files", StaticFiles(directory=OUTPUTS_DIR), name="files")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

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
    screen_format: str = ""
    model: str = "veo"

class AgentRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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

# ============================================================================
# PUBLIC ENDPOINTS (No Auth Required)
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Public landing page with API documentation link"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Marketing Content Generator API</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 40px auto; 
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255,255,255,0.1);
                padding: 40px;
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            h1 { margin-top: 0; }
            a { color: #ffd700; text-decoration: none; font-weight: bold; }
            a:hover { text-decoration: underline; }
            .code { 
                background: rgba(0,0,0,0.3); 
                padding: 10px; 
                border-radius: 5px; 
                font-family: monospace;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎨 Marketing Content Generator API</h1>
            <p>Professional AI-powered marketing content generation service.</p>
            
            <h2>🔐 Authentication Required</h2>
            <p>All endpoints require an API key in the <code>X-API-Key</code> header.</p>
            
            <h2>📚 Documentation</h2>
            <ul>
                <li><a href="/docs">Interactive API Docs (Swagger UI)</a></li>
                <li><a href="/redoc">ReDoc Documentation</a></li>
                <li><a href="/health">Health Check</a> (no auth)</li>
            </ul>
            
            <h2>🚀 Quick Start</h2>
            <div class="code">
                curl -X POST "https://your-api.com/generate/banner" \\<br>
                &nbsp;&nbsp;-H "X-API-Key: your-api-key-here" \\<br>
                &nbsp;&nbsp;-H "Content-Type: application/json" \\<br>
                &nbsp;&nbsp;-d '{"campaign_name": "Test", "brand_name": "Brand", ...}'
            </div>
            
            <h2>📧 Support</h2>
            <p>Contact your administrator for API keys and support.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/health")
async def health_check():
    """Health check endpoint (no auth required)"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "auth_enabled": True
    }

# ============================================================================
# PROTECTED ENDPOINTS (Auth Required)
# ============================================================================

@app.post("/generate/banner", dependencies=[Depends(check_rate_limit)])
async def generate_banner_endpoint(
    request: BannerRequest,
    user_info: dict = Depends(validate_api_key)
):
    """Generate a banner (requires API key)"""
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
            "weather_applied": bool(weather_data),
            "metadata": result,
            "user": user_info.get('user')
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/video", dependencies=[Depends(check_rate_limit)])
async def generate_video_endpoint(
    request: VideoRequest,
    user_info: dict = Depends(validate_api_key)
):
    """Generate a video (requires API key)"""
    try:
        from video_mcp_server import generate_video
        
        result_json = await generate_video(
            campaign_name=request.campaign_name,
            brand_name=request.brand_name,
            video_type=request.video_type,
            description=request.description,
            resolution=request.resolution,
            aspect_ratio=request.aspect_ratio,
            screen_format=request.screen_format,
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
            "metadata": result,
            "user": user_info.get('user')
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/outputs", dependencies=[Depends(check_rate_limit)])
async def list_outputs(user_info: dict = Depends(validate_api_key)):
    """List all generated files (requires API key)"""
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

@app.get("/weather/{location}", dependencies=[Depends(check_rate_limit)])
async def get_weather(location: str, user_info: dict = Depends(validate_api_key)):
    """Get current weather (requires API key)"""
    weather_data = fetch_weather(location)
    if "error" in weather_data:
        raise HTTPException(status_code=400, detail=weather_data["error"])
    return weather_data

@app.get("/banner-types")
async def get_banner_types():
    """Get available banner types (no auth for info endpoint)"""
    return {
        "banner_types": {
            "social": {"width": 1200, "height": 628, "description": "Social media posts"},
            "leaderboard": {"width": 728, "height": 90, "description": "Website header"},
            "square": {"width": 1024, "height": 1024, "description": "Square format"},
            "digital_6_sheet": {"width": 1080, "height": 1920, "description": "Vertical mobile"},
            "mpu": {"width": 300, "height": 250, "description": "Medium Rectangle"},
            "mobile_banner_300x50": {"width": 300, "height": 50, "description": "Small mobile banner"},
            "mobile_banner_320x50": {"width": 320, "height": 50, "description": "Standard mobile banner"},
            "landing_now": {"width": 1080, "height": 1920, "description": "Outernet Landing Now - 1080x1920"},
            "landing_trending": {"width": 1080, "height": 1920, "description": "Outernet Landing Trending - 1080x1920"},
            "vista_north": {"width": 1920, "height": 1080, "description": "Outernet Vista North - 1920x1080"},
            "vista_west1": {"width": 1080, "height": 1920, "description": "Outernet Vista West1 - 1080x1920"},
            "vista_west2": {"width": 1080, "height": 1920, "description": "Outernet Vista West2 - 1080x1920"},
            "outernet_now": {"width": 1920, "height": 1080, "description": "Outernet Now - 1920x1080"},
        }
    }

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.get("/admin/stats")
async def admin_stats(user_info: dict = Depends(validate_api_key)):
    """Get usage statistics (requires API key)"""
    # Only allow premium tier to see stats
    if user_info.get('tier') != 'premium':
        raise HTTPException(status_code=403, detail="Premium tier required")
    
    stats = {}
    for api_key, timestamps in request_history.items():
        user = VALID_API_KEYS.get(api_key, {}).get('user', 'unknown')
        stats[user] = {
            "total_requests": len(timestamps),
            "requests_last_hour": sum(1 for ts in timestamps if ts > time.time() - 3600)
        }
    
    return {"stats": stats}

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("🔐 SECURED Marketing Content Generator API")
    print("=" * 80)
    print(f"📁 Outputs directory: {OUTPUTS_DIR}")
    print(f"🔑 API Keys loaded: {len(VALID_API_KEYS)}")
    print(f"⚡ Rate limiting: Enabled")
    print(f"🌐 Starting server on http://0.0.0.0:8000")
    print(f"📖 API Documentation: http://0.0.0.0:8000/docs")
    print("=" * 80)
    print("\n🔑 Valid API Keys:")
    for key, info in VALID_API_KEYS.items():
        print(f"   {key[:16]}... ({info.get('user')}, tier: {info.get('tier')})")
    print("=" * 80)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)