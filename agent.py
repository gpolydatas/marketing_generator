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
                    "enum": ["landing_now", "landing_trending", "vista_north", "vista_west1", "vista_west2", "now_north", "digital_6_sheet", "leaderboard", "mpu", "mobile_banner_300x50", "mobile_banner_320x50", "social", "square"],
                    "description": "Banner format. DEFAULT: 'landing_now' (1080x1920 vertical). OUTERNET: landing_now, landing_trending, vista_north (1920x1080), vista_west1, vista_west2, now_north (1920x1080). OTHER: digital_6_sheet, social, square, leaderboard, mpu"
                },
                "message": {"type": "string", "description": "Main message (empty string if no text requested)"},
                "cta": {"type": "string", "description": "Call to action (empty string if no text requested)"},
                "additional_instructions": {"type": "string", "description": "Scene description and visual requirements. Extract from user request: 'car driving in countryside with sunny conditions', 'rainy atmosphere', 'no text mode', etc. Put the COMPLETE scene description here."},
                "reference_image_path": {"type": "string", "description": "Path to FIRST reference image if user attached one"},
                "reference_image_path_2": {"type": "string", "description": "Path to SECOND reference image if provided"},
                "reference_image_path_3": {"type": "string", "description": "Path to THIRD reference image if provided"},
                "reference_image_path_4": {"type": "string", "description": "Path to FOURTH reference image if provided"},
                "reference_image_path_5": {"type": "string", "description": "Path to FIFTH reference image if provided"},
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
                "screen_format": {"type": "string", "description": "Screen format name (e.g., 'vista_north', 'landing_now', 'social'). Extract from user's request. Will be included in filename."},
                "input_image_path": {"type": "string", "description": "Path to FIRST image to animate (if user attached images and wants to create video from them)"},
                "input_image_path_2": {"type": "string", "description": "Path to SECOND image if provided"},
                "input_image_path_3": {"type": "string", "description": "Path to THIRD image if provided"},
                "input_image_path_4": {"type": "string", "description": "Path to FOURTH image if provided"},
                "input_image_path_5": {"type": "string", "description": "Path to FIFTH image if provided"},
                "model": {"type": "string", "enum": ["veo", "runway"], "description": "Model to use"}
            },
            "required": ["campaign_name", "brand_name", "video_type", "description"]
        }
    }
]

SYSTEM = """You are a helpful marketing content generation assistant that asks questions to gather information before generating content.

YOUR ROLE:
- Have a natural conversation with the user to understand what they want to create
- Ask questions ONE AT A TIME to gather missing information
- Only call tools when you have ALL the required information
- Be friendly and conversational

REQUIRED INFORMATION FOR BANNERS:
1. Content type: Banner or Video?
2. Brand name: What brand/company is this for?
3. Banner type: What size/format? (social, leaderboard, square, digital_6_sheet, mpu, mobile banners, or Outernet screen types)
4. Text inclusion: Should the banner include text or be visual-only?
5. If text is included:
   - Message: What's the main message?
   - CTA: What's the call to action?
6. Weather data: Should we include current weather information?
7. Additional details: Any specific visual requirements, style, colors, etc.?

REQUIRED INFORMATION FOR VIDEOS:
1. Content type: Banner or Video?
2. Brand name: What brand/company is this for?
3. Video duration: Short (4s), standard (6s), or extended (8s)?
4. Resolution: 720p or 1080p?
5. Aspect ratio: 16:9, 9:16, or 1:1?
6. Description: What should happen in the video?
7. Image-to-video: Do they want to animate an existing image?

CONVERSATION FLOW:
1. When user makes a request, analyze what information is provided
2. If critical information is missing, ask for it conversationally (one question at a time)
3. Keep track of what you've learned in the conversation
4. Only when you have all required information, call the appropriate tool
5. If the user's request is vague (e.g., "make me a banner"), start by asking what brand/campaign it's for

EXAMPLES OF GOOD QUESTIONS:
- "What brand or company is this for?"
- "Would you like a banner or a video?"
- "What size banner do you need? (social media, billboard, leaderboard, etc.)"
- "Should this banner include text, or would you prefer a visual-only design?"
- "What message would you like to convey?"
- "Would you like me to include current weather information in the design?"
- "For the video, would you like it to be 4, 6, or 8 seconds long?"

SPECIAL CASES:
- If user says "use image X to create video", you still need to ask about brand, duration, resolution, aspect ratio, and description
- If user attaches an image with their prompt, check if it's for reference (banner) or animation (video)
- Default to 'social' banner type if user doesn't specify
- Default to 'no weather' unless explicitly requested

REMEMBER:
- Be conversational and friendly
- Ask ONE question at a time
- Don't overwhelm the user with multiple questions
- Use the conversation history to avoid asking for information already provided
- Only call tools when you're confident you have all required information"""

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
        
        # Extract attached images (support up to 5)
        img_matches = re.findall(r'\[ATTACHED_IMAGE:\s*(.+?)\]', text)
        img_paths = img_matches[:5] if img_matches else []  # Limit to 5 images
        
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
            
            # ✅ FIXED: Handle tool calls with validation in response
            if response.stop_reason == "tool_use":
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        
                        if tool_name == "generate_banner":
                            # Fetch weather if requested
                            weather_data = None
                            if tool_input.get('weather_location'):
                                weather_location = tool_input.get('weather_location', 'London')
                                weather_data = self._fetch_weather(weather_location)
                                if weather_data:
                                    print(f"🌤️ Weather: {weather_data['condition']}, {weather_data['temperature']}°C in {weather_location}")
                            
                            result = await generate_banner(
                                campaign_name=tool_input.get('campaign_name', 'Campaign'),
                                brand_name=tool_input.get('brand_name', ''),
                                banner_type=tool_input.get('banner_type', 'landing_now'),
                                message=tool_input.get('message', ''),
                                cta=tool_input.get('cta', ''),
                                additional_instructions=tool_input.get('additional_instructions', ''),
                                reference_image_path=tool_input.get('reference_image_path', img_paths[0] if len(img_paths) > 0 else ''),
                                reference_image_path_2=tool_input.get('reference_image_path_2', img_paths[1] if len(img_paths) > 1 else ''),
                                reference_image_path_3=tool_input.get('reference_image_path_3', img_paths[2] if len(img_paths) > 2 else ''),
                                reference_image_path_4=tool_input.get('reference_image_path_4', img_paths[3] if len(img_paths) > 3 else ''),
                                reference_image_path_5=tool_input.get('reference_image_path_5', img_paths[4] if len(img_paths) > 4 else ''),
                                weather_data=weather_data,
                                model=tool_input.get('model', 'imagen4')
                            )
                            
                            res = json.loads(result)
                            
                            if "error" in res:
                                return f"❌ Error: {res['error']}"
                            
                            # ✅ Build response with validation
                            brand = tool_input.get('brand_name', '')
                            message = tool_input.get('message', '')
                            cta = tool_input.get('cta', '')
                            
                            response_text = f"✅ **Banner Created Successfully!**\n\n"
                            response_text += f"📁 **File:** `{res['filename']}`\n"
                            response_text += f"📐 **Dimensions:** {res.get('dimensions', 'N/A')}\n"
                            response_text += f"🔥 **Download:** /files/{res['filename']}\n"
                            
                            if brand or message or cta:
                                response_text += f"\n🔍 **Running Validation...**\n"
                                
                                from banner_mcp_server import validate_banner
                                val_result = await validate_banner(
                                    filepath=res['filepath'],
                                    campaign_name=tool_input.get('campaign_name', 'Campaign'),
                                    brand_name=brand,
                                    message=message,
                                    cta=cta
                                )
                                val_data = json.loads(val_result)
                                
                                if val_data.get('passed'):
                                    response_text += f"\n✅ **VALIDATION PASSED**\n\n"
                                    scores = val_data.get('scores', {})
                                    response_text += f"**Scores:**\n"
                                    response_text += f"• Brand Visibility: **{scores.get('brand_visibility', 0)}/10**\n"
                                    response_text += f"• Message Clarity: **{scores.get('message_clarity', 0)}/10**\n"
                                    response_text += f"• CTA Effectiveness: **{scores.get('cta_effectiveness', 0)}/10**\n"
                                    response_text += f"• Visual Coherence: **{scores.get('visual_coherence', 0)}/10**\n"
                                    response_text += f"• Design Quality: **{scores.get('design_quality', 0)}/10**\n"
                                else:
                                    response_text += f"\n⚠️ **VALIDATION ISSUES DETECTED**\n\n"
                                    scores = val_data.get('scores', {})
                                    response_text += f"**Scores:**\n"
                                    response_text += f"• Brand Visibility: **{scores.get('brand_visibility', 0)}/10**\n"
                                    response_text += f"• Message Clarity: **{scores.get('message_clarity', 0)}/10**\n"
                                    response_text += f"• CTA Effectiveness: **{scores.get('cta_effectiveness', 0)}/10**\n"
                                    response_text += f"• Visual Coherence: **{scores.get('visual_coherence', 0)}/10**\n"
                                    response_text += f"• Design Quality: **{scores.get('design_quality', 0)}/10**\n"
                                    
                                    issues = val_data.get('issues', [])
                                    if issues:
                                        response_text += f"\n**Issues Found:**\n"
                                        for issue in issues:
                                            response_text += f"• {issue}\n"
                                
                                if val_data.get('summary'):
                                    response_text += f"\n**Summary:** {val_data['summary']}\n"
                            
                            return response_text
                            
                        elif tool_name == "generate_video":
                            result = await generate_video(
                                campaign_name=tool_input.get('campaign_name', 'Campaign'),
                                brand_name=tool_input.get('brand_name', 'Brand'),
                                video_type=tool_input.get('video_type', 'standard'),
                                description=tool_input.get('description', 'Cinematic movement'),
                                resolution=tool_input.get('resolution', '720p'),
                                aspect_ratio=tool_input.get('aspect_ratio', '16:9'),
                                screen_format=tool_input.get('screen_format', ''),
                                input_image_path=tool_input.get('input_image_path', img_paths[0] if img_paths else ''),
                                model=tool_input.get('model', 'veo'),
                                auto_validate=True  # ✅ Enable auto-validation
                            )
                            
                            res = json.loads(result)
                            
                            if "error" in res:
                                return f"❌ Error: {res['error']}"
                            
                            # ✅ Build response with validation
                            response_text = f"✅ **Video Created Successfully!**\n\n"
                            response_text += f"🎬 **Description:** {tool_input.get('description', '')}\n"
                            response_text += f"📁 **File:** `{res['filename']}`\n"
                            response_text += f"⏱️ **Duration:** {res.get('duration', 'N/A')}s\n"
                            response_text += f"📐 **Resolution:** {res.get('resolution_used', res.get('resolution', 'N/A'))}\n"
                            response_text += f"🔥 **Download:** /files/{res['filename']}\n"
                            
                            # Add validation results if available
                            if "validation" in res and not res["validation"].get("error"):
                                validation = res["validation"]
                                
                                response_text += f"\n🔍 **VALIDATION RESULTS**\n\n"
                                
                                if validation.get("passed"):
                                    response_text += f"✅ **VALIDATION PASSED**\n\n"
                                else:
                                    response_text += f"⚠️ **VALIDATION ISSUES DETECTED**\n\n"
                                
                                # Overall score
                                overall_score = validation.get("overall_score", 0)
                                response_text += f"**Overall Score: {overall_score:.1f}/10**\n\n"
                                
                                # Detailed scores
                                scores = validation.get("scores", {})
                                response_text += f"**Detailed Scores:**\n"
                                response_text += f"• Visual Quality: **{scores.get('visual_quality', 0)}/10**\n"
                                response_text += f"• Brand Presence: **{scores.get('brand_presence', 0)}/10**\n"
                                response_text += f"• Content Relevance: **{scores.get('content_relevance', 0)}/10**\n"
                                response_text += f"• Production Value: **{scores.get('production_value', 0)}/10**\n"
                                response_text += f"• Technical Execution: **{scores.get('technical_execution', 0)}/10**\n"
                                response_text += f"• Marketing Effectiveness: **{scores.get('marketing_effectiveness', 0)}/10**\n"
                                
                                # Issues
                                issues = validation.get("issues", [])
                                if issues:
                                    response_text += f"\n**Issues Found:**\n"
                                    for issue in issues[:3]:  # Show top 3 issues
                                        response_text += f"• {issue}\n"
                                    if len(issues) > 3:
                                        response_text += f"• _(+{len(issues) - 3} more issues)_\n"
                                
                                # Strengths
                                strengths = validation.get("strengths", [])
                                if strengths:
                                    response_text += f"\n**Strengths:**\n"
                                    for strength in strengths[:3]:  # Show top 3 strengths
                                        response_text += f"• {strength}\n"
                                
                                # Summary
                                if validation.get("summary"):
                                    response_text += f"\n**Summary:** {validation['summary']}\n"
                            
                            return response_text
            
            # If no tool call, return text response (agent asking questions)
            text_response = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    text_response += block.text
            
            # Update conversation history
            self.state[sid] = msgs + [{"role": "assistant", "content": response.content}]
            
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
