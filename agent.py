#!/usr/bin/env python3
import asyncio, sys, os, json, yaml, re
from anthropic import Anthropic

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banner_mcp_server import generate_banner
from video_mcp_server import generate_video

def load_keys():
    p = os.path.join(os.path.dirname(__file__), 'fastagent.secrets.yaml')
    if os.path.exists(p):
        with open(p) as f:
            s = yaml.safe_load(f)
        if 'anthropic' in s and 'api_key' in s['anthropic']:
            os.environ['ANTHROPIC_API_KEY'] = s['anthropic']['api_key']
        if 'openai' in s and 'api_key' in s['openai']:
            os.environ['OPENAI_API_KEY'] = s['openai']['api_key']
        if 'weather' in s and 'api_key' in s['weather']:
            os.environ['OPENWEATHER_API_KEY'] = s['weather']['api_key']

def get_model():
    """Get model from config or use default"""
    p = os.path.join(os.path.dirname(__file__), 'fastagent.config.yaml')
    if os.path.exists(p):
        with open(p) as f:
            c = yaml.safe_load(f)
        model = c.get('default_model', 'claude-sonnet-4-5-20250929')
        
        # Map aliases
        if model == 'sonnet':
            return 'claude-sonnet-4-5-20250929'
        elif model == 'sonnet35':
            return 'claude-3-5-sonnet-20241022'
        elif model == 'haiku':
            return 'claude-3-5-haiku-20241022'
        return model
    
    return 'claude-sonnet-4-5-20250929'

TOOLS = [
    {
        "name": "generate_banner",
        "description": "Generate a marketing banner/image. Use when user wants a static image, billboard, banner, poster, or any format like digital 6 sheet, leaderboard, MPU, mobile banner, square, social media post",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_name": {"type": "string", "description": "Campaign name"},
                "brand_name": {"type": "string", "description": "Brand/company name (empty string if no text requested)"},
                "banner_type": {
                    "type": "string",
                    "enum": ["digital_6_sheet", "leaderboard", "mpu", "mobile_banner_300x50", "mobile_banner_320x50", "social", "square"],
                    "description": "Banner format. DEFAULT: 'social' (1080x1080) for generic banners. Use digital_6_sheet (1080x1920) ONLY if user says billboard/6-sheet. leaderboard (728x90), mpu (300x250), mobile_banner_300x50, mobile_banner_320x50, square (600x600)"
                },
                "message": {"type": "string", "description": "Main message (empty string if no text requested)"},
                "cta": {"type": "string", "description": "Call to action (empty string if no text requested)"},
                "additional_instructions": {"type": "string", "description": "Scene description and visual requirements. Extract from user request: 'car driving in countryside with sunny conditions', 'rainy atmosphere', 'no text mode', etc. Put the COMPLETE scene description here."},
                "reference_image_path": {"type": "string", "description": "Path to reference image if user attached one"},
                "weather_location": {"type": "string", "description": "Location for weather API (e.g., 'London', 'New York'). Set this when user says 'use weather API' or 'apply weather conditions'. Default: 'London'"},
                "model": {"type": "string", "enum": ["imagen4", "imagen4ultra", "dalle3"], "description": "Image generation model. DEFAULT: 'imagen4' (best quality). Use 'dalle3' only if user explicitly asks for DALL-E."}
            },
            "required": ["campaign_name", "banner_type"]
        }
    },
    {
        "name": "generate_video",
        "description": "Generate a video OR animate an existing image into video. Use when user wants video, animation, motion content, or says 'use image to create video'",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_name": {"type": "string", "description": "Campaign name"},
                "brand_name": {"type": "string", "description": "Brand name"},
                "video_type": {
                    "type": "string",
                    "enum": ["short", "standard", "extended"],
                    "description": "Video duration: short (4s), standard (6s), extended (8s)"
                },
                "description": {"type": "string", "description": "COMPLETE scene description including: location, weather, action, camera movement. Extract EVERYTHING after 'where' keyword. Example: 'the car is running through the streets of London in snowy conditions'"},
                "resolution": {"type": "string", "enum": ["720p", "1080p"], "description": "Video resolution"},
                "aspect_ratio": {"type": "string", "enum": ["16:9", "9:16", "1:1"], "description": "Aspect ratio"},
                "input_image_path": {"type": "string", "description": "Path to image to animate (if user attached image and wants to create video from it)"},
                "model": {"type": "string", "enum": ["veo", "runway"], "description": "Model to use"}
            },
            "required": ["campaign_name", "brand_name", "video_type", "description"]
        }
    }
]

SYSTEM = """You are a marketing content generation assistant. 

When the user requests content:
1. Understand what they want (banner, video, animation)
2. Extract ALL information from their request
3. Call the appropriate tool with the extracted information

CRITICAL RULES FOR BANNERS:
- Default banner_type is "social" (1080x1080) unless user specifies a format
- If user says "billboard" or "digital 6 sheet" or "1080x1920", use "digital_6_sheet"
- If user says "leaderboard" or "728x90", use "leaderboard"
- Put scene descriptions in additional_instructions: "car driving in highway with rainy conditions"
- Put style keywords in additional_instructions: "hyperrealistic", "photorealistic", "artistic", "cinematic"
- If user says "use image X and create [hyper realistic] image showing Y", put "hyperrealistic Y" in additional_instructions AND set reference_image_path
- If no text requested, use empty strings for brand_name, message, cta
- WEATHER API: When user says "use weather API" or "apply weather conditions", set weather_location to a city name (default: "London")

CRITICAL RULES FOR VIDEOS:
- If user says "use image X to create video", call generate_video with input_image_path
- Extract the COMPLETE description after "where" or "showing" - include location, weather, action, everything
- Map duration: 4 seconds = short, 6 seconds = standard, 8 seconds = extended

NEVER ask for information if you can infer it. Just call the tool with your best interpretation."""

class Agent:
    def __init__(self):
        load_keys()
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = get_model()
        self.state = {}
    
    def _fetch_weather(self, location: str):
        """Fetch weather data from OpenWeather API"""
        try:
            import requests
            api_key = os.getenv("OPENWEATHER_API_KEY")
            if not api_key:
                return None
            
            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'condition': data['weather'][0]['main'],
                    'description': data['weather'][0]['description'],
                    'temperature': data['main']['temp'],
                    'humidity': data['main']['humidity'],
                    'location': location
                }
        except Exception as e:
            print(f"Weather API error: {e}")
        
        return None
    
    async def process(self, text: str, sid: str = "default") -> str:
        if sid not in self.state:
            self.state[sid] = []
        
        # Extract attached image
        img = re.search(r'\[ATTACHED_IMAGE:\s*(.+?)\]', text)
        img_path = img.group(1) if img else None
        
        # Build messages
        msgs = self.state[sid] + [{"role": "user", "content": text}]
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM,
                tools=TOOLS,
                messages=msgs
            )
            
            # Handle tool calls
            if response.stop_reason == "tool_use":
                tool_results = []
                
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        
                        # Call the actual tool
                        if tool_name == "generate_banner":
                            # Fetch weather if requested
                            weather_data = None
                            if tool_input.get('weather_location'):
                                weather_location = tool_input.get('weather_location', 'London')
                                weather_data = self._fetch_weather(weather_location)
                                if weather_data:
                                    print(f"🌤️  Weather: {weather_data['condition']}, {weather_data['temperature']}°C in {weather_location}")
                            
                            result = await generate_banner(
                                campaign_name=tool_input.get('campaign_name', 'Campaign'),
                                brand_name=tool_input.get('brand_name', ''),
                                banner_type=tool_input.get('banner_type', 'social'),
                                message=tool_input.get('message', ''),
                                cta=tool_input.get('cta', ''),
                                additional_instructions=tool_input.get('additional_instructions', ''),
                                reference_image_path=tool_input.get('reference_image_path', img_path or ''),
                                weather_data=weather_data,
                                model=tool_input.get('model', 'imagen4')
                            )
                        elif tool_name == "generate_video":
                            result = await generate_video(
                                campaign_name=tool_input.get('campaign_name', 'Campaign'),
                                brand_name=tool_input.get('brand_name', 'Brand'),
                                video_type=tool_input.get('video_type', 'standard'),
                                description=tool_input.get('description', 'Cinematic movement'),
                                resolution=tool_input.get('resolution', '720p'),
                                aspect_ratio=tool_input.get('aspect_ratio', '16:9'),
                                input_image_path=tool_input.get('input_image_path', img_path or ''),
                                model=tool_input.get('model', 'veo')
                            )
                        
                        # Parse result
                        res = json.loads(result)
                        
                        if "error" in res:
                            return f"❌ Error: {res['error']}"
                        
                        # Format success message
                        if tool_name == "generate_banner":
                            return f"✅ Banner created!\n\n📁 {res['filename']}\n📥 /files/{res['filename']}"
                        else:
                            return f"✅ Video created!\n\n🎬 {tool_input.get('description', '')}\n📁 {res['filename']}\n📥 /files/{res['filename']}"
            
            # If no tool call, return text response
            text_response = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    text_response += block.text
            
            return text_response or "What would you like to create?"
            
        except Exception as e:
            return f"❌ Error: {str(e)}"

agent = Agent()

async def run_single_prompt(prompt: str, session_id: str = "default") -> str:
    return await agent.process(prompt, session_id)

async def main():
    print("\n🤖 CLAUDE AGENT WITH TOOL CALLING\n")
    sid = "cli"
    while True:
        try:
            i = input("💬 You: ").strip()
            if i.lower() in ['quit', 'exit', 'bye']:
                break
            r = await run_single_prompt(i, sid)
            print(f"\n🤖 Agent: {r}\n")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ {e}")

if __name__ == "__main__":
    asyncio.run(main())