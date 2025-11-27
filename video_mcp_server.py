#!/usr/bin/env python3
"""
VIDEO GENERATION MCP SERVER - WITH VALIDATION
Supports both Google Veo 3.1 and RunwayML Gen-3 Alpha
Includes comprehensive video validation using Claude Vision
"""

import os
import json
import time
import requests
from datetime import datetime
from google import genai
from google.genai import types
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Import validation module
from video_validation import validate_video_with_claude

# Video specifications
VIDEO_SPECS = {
    "short": {"duration": 4, "description": "4-second video"},
    "standard": {"duration": 6, "description": "6-second video"},
    "extended": {"duration": 8, "description": "8-second video"},
}

# Create MCP server
app = Server("video-tools")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="generate_video",
            description="Generate a promotional video using Google Veo 3.1 or RunwayML Gen-3 Alpha",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_name": {
                        "type": "string",
                        "description": "Name of the advertising campaign"
                    },
                    "brand_name": {
                        "type": "string",
                        "description": "Brand/company name"
                    },
                    "video_type": {
                        "type": "string",
                        "enum": ["short", "standard", "extended"],
                        "description": "Type of video duration (short=4s, standard=6s, extended=8s)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of what should happen in the video"
                    },
                    "resolution": {
                        "type": "string",
                        "enum": ["720p", "1080p"],
                        "description": "Video resolution",
                        "default": "720p"
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["16:9", "9:16"],
                        "description": "Video aspect ratio",
                        "default": "16:9"
                    },
                    "input_image_path": {
                        "type": "string",
                        "description": "OPTIONAL: Full filepath to an existing image to animate into video",
                        "default": ""
                    },
                    "model": {
                        "type": "string",
                        "enum": ["veo", "runway"],
                        "description": "AI model to use: 'veo' for Google Veo 3.1, 'runway' for RunwayML Gen-3 Alpha",
                        "default": "veo"
                    },
                    "auto_validate": {
                        "type": "boolean",
                        "description": "Automatically validate the generated video",
                        "default": True
                    }
                },
                "required": ["campaign_name", "brand_name", "video_type", "description"]
            }
        ),
        Tool(
            name="validate_video",
            description="Validate a generated video using Claude Vision API - analyzes quality, brand presence, content relevance, and technical execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Full path to the video file"
                    },
                    "campaign_name": {
                        "type": "string",
                        "description": "Expected campaign name"
                    },
                    "brand_name": {
                        "type": "string",
                        "description": "Expected brand name"
                    },
                    "description": {
                        "type": "string",
                        "description": "Expected video content description"
                    },
                    "expected_duration": {
                        "type": "integer",
                        "description": "Expected duration in seconds"
                    },
                    "expected_resolution": {
                        "type": "string",
                        "description": "Expected resolution (e.g., '1080p', '720p')"
                    },
                    "expected_aspect_ratio": {
                        "type": "string",
                        "description": "Expected aspect ratio (e.g., '16:9', '9:16')"
                    }
                },
                "required": ["filepath", "campaign_name", "brand_name", "description"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    
    if name == "generate_video":
        result = await generate_video(**arguments)
        return [TextContent(type="text", text=result)]
    
    elif name == "validate_video":
        result = await validate_video(**arguments)
        return [TextContent(type="text", text=result)]
    
    else:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def generate_video(
    campaign_name: str,
    brand_name: str,
    video_type: str,
    description: str,
    resolution: str = "720p",
    aspect_ratio: str = "16:9",
    screen_format: str = "",
    input_image_path: str = "",
    model: str = "veo",
    auto_validate: bool = True
) -> str:
    """Generate video and optionally validate it"""
    
    # Validate video type
    if video_type not in VIDEO_SPECS:
        return json.dumps({
            "error": f"Invalid video_type. Must be one of: {list(VIDEO_SPECS.keys())}"
        })
    
    # Route to appropriate model
    if model == "veo":
        result_json = await generate_video_veo(
            campaign_name, brand_name, video_type, description,
            resolution, aspect_ratio, screen_format, input_image_path
        )
    elif model == "runway":
        result_json = await generate_video_runway(
            campaign_name, brand_name, video_type, description,
            resolution, aspect_ratio, screen_format, input_image_path
        )
    else:
        return json.dumps({
            "error": f"Unknown model: {model}. Must be 'veo' or 'runway'"
        })
    
    result = json.loads(result_json)
    
    # If generation succeeded and auto_validate is True, validate the video
    if result.get("success") and auto_validate:
        print("\n" + "=" * 80)
        print("🔍 AUTO-VALIDATING GENERATED VIDEO")
        print("=" * 80)
        
        validation_result = await validate_video_with_claude(
            filepath=result["filepath"],
            campaign_name=campaign_name,
            brand_name=brand_name,
            description=description,
            expected_duration=VIDEO_SPECS[video_type]["duration"],
            expected_resolution=resolution,
            expected_aspect_ratio=aspect_ratio
        )
        
        # Add validation to result
        result["validation"] = validation_result
        
        # Update metadata file with validation
        metadata_file = result.get("metadata_file")
        if metadata_file and os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            metadata["validation"] = validation_result
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        return json.dumps(result, indent=2)
    
    return result_json


async def validate_video(
    filepath: str,
    campaign_name: str,
    brand_name: str,
    description: str,
    expected_duration: int = None,
    expected_resolution: str = None,
    expected_aspect_ratio: str = None
) -> str:
    """Validate video using Claude Vision API"""
    
    result = await validate_video_with_claude(
        filepath=filepath,
        campaign_name=campaign_name,
        brand_name=brand_name,
        description=description,
        expected_duration=expected_duration,
        expected_resolution=expected_resolution,
        expected_aspect_ratio=expected_aspect_ratio
    )
    
    return json.dumps(result, indent=2)


async def generate_video_veo(
    campaign_name: str,
    brand_name: str,
    video_type: str,
    description: str,
    resolution: str = "720p",
    aspect_ratio: str = "16:9",
    screen_format: str = "",
    input_image_path: str = ""
) -> str:
    """Generate video using Google Veo 3.1 API - supports image-to-video"""
    
    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return json.dumps({
            "error": "GOOGLE_API_KEY environment variable not set"
        })
    
    # Check if input image path is provided
    has_input_image = bool(input_image_path and input_image_path.strip())
    if has_input_image:
        if not os.path.exists(input_image_path):
            return json.dumps({
                "error": f"Input image not found: {input_image_path}"
            })
        print(f"🖼️ Input image will be uploaded: {input_image_path}")
    
    # Generate enhanced prompt
    specs = VIDEO_SPECS[video_type]
    actual_duration = specs['duration']
    
    # Veo API constraint: 1080p REQUIRES exactly 8 seconds duration
    original_resolution = resolution
    if resolution == "1080p" and actual_duration < 8:
        resolution = "720p"
        print(f"⚠️ Veo API requires 8s for 1080p. Adjusted resolution to 720p for {actual_duration}s video")
    
    prompt = f"""Create a professional promotional video for {brand_name}'s {campaign_name}.

VIDEO DESCRIPTION:
{description}

VISUAL REQUIREMENTS:
- Brand: {brand_name} - show branding naturally in the scene
- Duration: {actual_duration} seconds
- Style: Cinematic, professional, high-quality production
- Smooth camera movements and transitions
- Professional lighting and composition
- Engaging visual storytelling
- Suitable for digital advertising

TECHNICAL:
- {resolution} resolution
- {aspect_ratio} aspect ratio
- Professional color grading
- High production value"""
    
    try:
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Upload input image if provided
        input_image = None
        if has_input_image:
            print(f"⏳ Loading image for Veo...")
            try:
                import mimetypes
                
                with open(input_image_path, 'rb') as f:
                    image_bytes = f.read()
                
                mime_type, _ = mimetypes.guess_type(input_image_path)
                if not mime_type:
                    mime_type = 'image/png'
                
                input_image = types.Image(
                    image_bytes=image_bytes,
                    mime_type=mime_type
                )
                print(f"✅ Image loaded successfully ({mime_type})")
                
            except Exception as e:
                return json.dumps({
                    "error": f"Failed to load image: {str(e)}"
                })
        
        # Configure video generation
        config = types.GenerateVideosConfig(
            number_of_videos=1,
            resolution=resolution,
            duration_seconds=actual_duration,
            aspect_ratio=aspect_ratio
        )
        
        # Generate video
        if input_image:
            print(f"⏳ Generating {actual_duration}s video from image with Veo 3.1...")
            operation = client.models.generate_videos(
                model="veo-3.1-generate-preview",
                prompt=prompt,
                image=input_image,
                config=config
            )
        else:
            print(f"⏳ Generating {actual_duration}s video from text with Veo 3.1...")
            operation = client.models.generate_videos(
                model="veo-3.1-generate-preview",
                prompt=prompt,
                config=config
            )
        
        # Wait for completion
        while not operation.done:
            print("   Waiting for video generation...")
            time.sleep(10)
            operation = client.operations.get(operation)
        
        if not hasattr(operation, 'response') or not operation.response:
            return json.dumps({
                "error": "Video generation failed - no response from API"
            })
        
        # Get generated video
        generated_video = operation.response.generated_videos[0]
        
        # Download video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source_type = "image" if input_image else "text"
        
        if screen_format:
            filename = f"video_{screen_format}_{video_type}_{actual_duration}s_{source_type}_{timestamp}.mp4"
        else:
            filename = f"video_{video_type}_{actual_duration}s_{source_type}_{timestamp}.mp4"
        
        output_dir = os.path.join(os.path.dirname(__file__), "outputs")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        filepath = os.path.join(output_dir, filename)
        
        client.files.download(file=generated_video.video)
        generated_video.video.save(filepath)
        
        file_size = os.path.getsize(filepath) / 1024 / 1024
        
        # Save metadata
        metadata = {
            "campaign": campaign_name,
            "brand": brand_name,
            "video_type": video_type,
            "duration": actual_duration,
            "description": description,
            "resolution_requested": original_resolution,
            "resolution_used": resolution,
            "aspect_ratio": aspect_ratio,
            "source_type": source_type,
            "input_image": input_image_path if input_image else None,
            "filename": filename,
            "filepath": filepath,
            "file_size_mb": round(file_size, 2),
            "model": "veo-3.1-generate-preview",
            "timestamp": datetime.now().isoformat()
        }
        
        metadata_file = filepath.replace('.mp4', '.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return json.dumps({
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "duration": actual_duration,
            "resolution_requested": original_resolution,
            "resolution_used": resolution,
            "aspect_ratio": aspect_ratio,
            "source_type": source_type,
            "input_image": input_image_path if input_image else None,
            "file_size_mb": round(file_size, 2),
            "model": "veo-3.1-generate-preview",
            "metadata_file": metadata_file
        }, indent=2)
            
    except Exception as e:
        return json.dumps({"error": f"Veo 3.1 API error: {str(e)}"})


async def generate_video_runway(
    campaign_name: str,
    brand_name: str,
    video_type: str,
    description: str,
    resolution: str = "720p",
    aspect_ratio: str = "16:9",
    screen_format: str = "",
    input_image_path: str = ""
) -> str:
    """Generate video using RunwayML Gen-3 Alpha API - supports image-to-video"""
    
    # Check API key
    api_key = os.getenv("RUNWAYML_API_KEY")
    if not api_key:
        return json.dumps({
            "error": "RUNWAYML_API_KEY environment variable not set"
        })
    
    # Check if input image path is provided
    has_input_image = bool(input_image_path and input_image_path.strip())
    if has_input_image:
        if not os.path.exists(input_image_path):
            return json.dumps({
                "error": f"Input image not found: {input_image_path}"
            })
        print(f"🖼️ Input image for RunwayML: {input_image_path}")
    
    # Generate enhanced prompt
    specs = VIDEO_SPECS[video_type]
    
    prompt = f"""Create a cinematic promotional video for {brand_name}'s {campaign_name}.

VIDEO DESCRIPTION:
{description}

REQUIREMENTS:
- Duration: {specs['duration']} seconds
- Style: Cinematic, professional, high-quality
- Brand: {brand_name} (show branding naturally)
- Smooth camera movements
- Professional lighting and composition
- Engaging visual storytelling
- Suitable for digital advertising"""
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06"
        }
        
        runway_ratio = "1280:768" if aspect_ratio == "16:9" else "768:1280"
        runway_duration = 5 if specs['duration'] <= 5 else 10
        
        payload = {
            "promptText": prompt,
            "model": "gen3a_turbo",
            "duration": runway_duration,
            "ratio": runway_ratio
        }
        
        # Add image if provided
        if has_input_image:
            print(f"⏳ Uploading image to RunwayML...")
            import base64
            import mimetypes
            
            with open(input_image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            mime_type, _ = mimetypes.guess_type(input_image_path)
            if not mime_type:
                mime_type = 'image/png'
            
            payload["promptImage"] = f"data:{mime_type};base64,{image_data}"
            print(f"✅ Image encoded and added to payload")
        
        print(f"⏳ Creating RunwayML generation task...")
        
        response = requests.post(
            "https://api.dev.runwayml.com/v1/image_to_video",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            return json.dumps({
                "error": f"RunwayML API error: {response.status_code} - {response.text}"
            })
        
        result = response.json()
        task_id = result.get("id")
        
        if not task_id:
            return json.dumps({
                "error": "No task ID returned from RunwayML"
            })
        
        print(f"✅ Task created: {task_id}")
        print(f"⏳ Generating video (this takes 1-3 minutes)...")
        
        # Poll for completion
        max_attempts = 60
        for attempt in range(max_attempts):
            time.sleep(5)
            
            status_response = requests.get(
                f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
                headers=headers,
                timeout=30
            )
            
            if status_response.status_code != 200:
                continue
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status == "SUCCEEDED":
                video_url = status_data.get("output", [None])[0]
                if not video_url:
                    return json.dumps({"error": "No video URL in response"})
                
                print(f"✅ Video generated! Downloading...")
                
                video_response = requests.get(video_url, timeout=60)
                
                if video_response.status_code == 200:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    source_type = "image" if has_input_image else "text"
                    
                    if screen_format:
                        filename = f"video_{screen_format}_{video_type}_{specs['duration']}s_{source_type}_{timestamp}.mp4"
                    else:
                        filename = f"video_{video_type}_{specs['duration']}s_{source_type}_{timestamp}.mp4"
                    
                    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(video_response.content)
                    
                    file_size = len(video_response.content) / 1024 / 1024
                    
                    # Save metadata
                    metadata = {
                        "campaign": campaign_name,
                        "brand": brand_name,
                        "video_type": video_type,
                        "duration": specs['duration'],
                        "description": description,
                        "resolution": resolution,
                        "aspect_ratio": aspect_ratio,
                        "source_type": source_type,
                        "input_image": input_image_path if has_input_image else None,
                        "filename": filename,
                        "filepath": filepath,
                        "url": video_url,
                        "file_size_mb": round(file_size, 2),
                        "model": "gen3a_turbo",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    metadata_file = filepath.replace('.mp4', '.json')
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    
                    return json.dumps({
                        "success": True,
                        "filename": filename,
                        "filepath": filepath,
                        "url": video_url,
                        "duration": specs['duration'],
                        "resolution": resolution,
                        "aspect_ratio": aspect_ratio,
                        "source_type": source_type,
                        "input_image": input_image_path if has_input_image else None,
                        "file_size_mb": round(file_size, 2),
                        "model": "gen3a_turbo",
                        "metadata_file": metadata_file
                    }, indent=2)
                else:
                    return json.dumps({"error": "Failed to download video"})
            
            elif status == "FAILED":
                error_msg = status_data.get("error", "Unknown error")
                return json.dumps({"error": f"Video generation failed: {error_msg}"})
            
            if attempt % 6 == 0:
                print(f"   Still processing... ({attempt * 5}s elapsed)")
        
        return json.dumps({"error": "Video generation timed out after 5 minutes"})
            
    except Exception as e:
        return json.dumps({"error": f"RunwayML API error: {str(e)}"})


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
