#!/usr/bin/env python3
"""
STREAMLIT WEB INTERFACE - WITH MODEL SELECTION AND IMAGE UPLOAD
Direct MCP tool calls without agent
"""

import streamlit as st
import os
import json
import asyncio
from datetime import datetime, timedelta
import sys
import nest_asyncio

# Apply nest_asyncio to fix event loop issues
nest_asyncio.apply()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load API keys from secrets file
def load_api_keys():
    """Load API keys from fastagent.secrets.yaml"""
    import yaml
    secrets_path = os.path.join(os.path.dirname(__file__), 'fastagent.secrets.yaml')
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r') as f:
            secrets = yaml.safe_load(f)
            
            # Set environment variables
            if 'openai' in secrets and 'api_key' in secrets['openai']:
                os.environ['OPENAI_API_KEY'] = secrets['openai']['api_key']
            
            if 'anthropic' in secrets and 'api_key' in secrets['anthropic']:
                os.environ['ANTHROPIC_API_KEY'] = secrets['anthropic']['api_key']
            
            if 'google' in secrets and 'api_key' in secrets['google']:
                os.environ['GOOGLE_API_KEY'] = secrets['google']['api_key']
            
            if 'weather' in secrets and 'api_key' in secrets['weather']:
                os.environ['OPENWEATHER_API_KEY'] = secrets['weather']['api_key']
            
            # Also check MCP server env vars
            if 'mcp' in secrets and 'servers' in secrets['mcp']:
                if 'banner_tools' in secrets['mcp']['servers'] and 'env' in secrets['mcp']['servers']['banner_tools']:
                    for key, val in secrets['mcp']['servers']['banner_tools']['env'].items():
                        os.environ[key] = val
                
                if 'video_tools' in secrets['mcp']['servers'] and 'env' in secrets['mcp']['servers']['video_tools']:
                    for key, val in secrets['mcp']['servers']['video_tools']['env'].items():
                        os.environ[key] = val

# Load keys on startup
load_api_keys()

# Page config
st.set_page_config(
    page_title="Marketing Content Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'generation_log' not in st.session_state:
    st.session_state.generation_log = []
if 'selected_video_model' not in st.session_state:
    st.session_state.selected_video_model = 'veo'  # Default to Veo 3.1
if 'agent_conversation' not in st.session_state:
    st.session_state.agent_conversation = []
if 'weather_automation' not in st.session_state:
    st.session_state.weather_automation = False
if 'last_weather_check' not in st.session_state:
    st.session_state.last_weather_check = None
if 'weather_location' not in st.session_state:
    st.session_state.weather_location = "London"
if 'weather_font' not in st.session_state:
    st.session_state.weather_font = "Arial"
if 'weather_primary_color' not in st.session_state:
    st.session_state.weather_primary_color = "#FFFFFF"
if 'weather_secondary_color' not in st.session_state:
    st.session_state.weather_secondary_color = "#000000"

# Helper functions
def load_metadata(filepath):
    """Load metadata JSON if exists"""
    metadata_file = filepath.replace('.png', '.json').replace('.mp4', '.json')
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return None

def fetch_weather(location):
    """Fetch current weather data from OpenWeatherMap API"""
    import requests
    
    # Get API key from environment or secrets
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        return {"error": "OPENWEATHER_API_KEY not set. Get free API key from https://openweathermap.org/api"}
    
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
                "wind_speed": round(data['wind']['speed'] * 3.6)  # Convert m/s to km/h
            }
        else:
            return {"error": f"Weather API error: {response.status_code}"}
    except Exception as e:
        return {"error": f"Failed to fetch weather: {str(e)}"}

async def generate_weather_banner(weather_data, font_family="Arial", primary_color="#FFFFFF", secondary_color="#000000", weather_includes=None):
    """Generate a banner based on current weather"""
    from banner_mcp_server import generate_banner
    
    if weather_includes is None:
        weather_includes = {
            'temperature': True,
            'condition': True,
            'humidity': False,
            'wind': False,
            'description': True
        }
    
    # Create weather-appropriate description
    temp = weather_data['temperature']
    condition = weather_data['condition']
    location = weather_data['location']
    description = weather_data['description']
    humidity = weather_data.get('humidity', 0)
    wind_speed = weather_data.get('wind_speed', 0)
    
    # Build message based on selected weather elements
    message_parts = []
    
    if weather_includes.get('temperature'):
        if condition in ['Clear', 'Clouds']:
            if temp > 25:
                message_parts.append(f"☀️ {temp}°C")
            elif temp > 15:
                message_parts.append(f"🌤️ {temp}°C")
            else:
                message_parts.append(f"☁️ {temp}°C")
        elif condition == 'Rain':
            message_parts.append(f"🌧️ {temp}°C")
        elif condition == 'Snow':
            message_parts.append(f"❄️ {temp}°C")
        elif condition == 'Thunderstorm':
            message_parts.append(f"⛈️ {temp}°C")
        else:
            message_parts.append(f"🌡️ {temp}°C")
    
    if weather_includes.get('condition'):
        message_parts.append(condition)
    
    if weather_includes.get('humidity'):
        message_parts.append(f"💧 {humidity}%")
    
    if weather_includes.get('wind'):
        message_parts.append(f"💨 {wind_speed} km/h")
    
    message = " | ".join(message_parts) if message_parts else f"{temp}°C"
    
    # Use description for CTA
    cta = description.title() if weather_includes.get('description') else condition
    
    # Add font and color instructions to additional_instructions
    style_instructions = f"""
FONT STYLING:
- Use {font_family} font family or similar sans-serif font
- Make text bold and clear

COLOR SCHEME:
- Primary color: {primary_color} (use for main elements and background accents)
- Secondary color: {secondary_color} (use for text or contrast)
- Create a harmonious color palette based on these colors
- Ensure high contrast for readability

WEATHER THEME:
- Reflect the weather condition: {condition}
- Use weather-appropriate imagery and mood
"""
    
    result_json = await generate_banner(
        campaign_name=f"Weather Update - {location}",
        brand_name=location,
        banner_type="social",
        message=message,
        cta=cta,
        additional_instructions=style_instructions,
        reference_image_path="",
        font_family=font_family,
        primary_color=primary_color,
        secondary_color=secondary_color
    )
    
    return json.loads(result_json)

def display_banner(filepath, metadata=None, key_suffix=""):
    """Display a banner with metadata"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.image(filepath, use_container_width=True)
    
    with col2:
        st.markdown("### 📊 Details")
        if metadata:
            st.write(f"**Campaign:** {metadata.get('campaign', 'N/A')}")
            st.write(f"**Brand:** {metadata.get('brand', 'N/A')}")
            st.write(f"**Type:** {metadata.get('banner_type', 'N/A')}")
            st.write(f"**Size:** {metadata.get('file_size_mb', 0):.2f} MB")
            
            if 'validation' in metadata:
                val = metadata['validation']
                if val.get('passed'):
                    st.success("✅ Validated")
                    with st.expander("📊 Scores"):
                        scores = val.get('scores', {})
                        for key, value in scores.items():
                            st.metric(key.replace('_', ' ').title(), f"{value}/10")
                else:
                    st.error("❌ Validation Failed")
        
        with open(filepath, 'rb') as f:
            st.download_button(
                label="📥 Download",
                data=f.read(),
                file_name=os.path.basename(filepath),
                mime="image/png",
                use_container_width=True,
                key=f"download_banner_{os.path.basename(filepath)}_{key_suffix}"
            )

def display_video(filepath, metadata=None, key_suffix=""):
    """Display a video with metadata"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.video(filepath)
    
    with col2:
        st.markdown("### 🎬 Details")
        if metadata:
            st.write(f"**Campaign:** {metadata.get('campaign', 'N/A')}")
            st.write(f"**Brand:** {metadata.get('brand', 'N/A')}")
            st.write(f"**Duration:** {metadata.get('duration', 'N/A')}s")
            st.write(f"**Resolution:** {metadata.get('resolution', 'N/A')}")
            st.write(f"**Model:** {metadata.get('model', 'N/A')}")
            st.write(f"**Size:** {metadata.get('file_size_mb', 0):.2f} MB")
        
        with open(filepath, 'rb') as f:
            st.download_button(
                label="📥 Download",
                data=f.read(),
                file_name=os.path.basename(filepath),
                mime="video/mp4",
                use_container_width=True,
                key=f"download_video_{os.path.basename(filepath)}_{key_suffix}"
            )

def scan_output_directory():
    """Scan output directory for generated content"""
    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    if not os.path.exists(output_dir):
        return []
    
    content = []
    for file in os.listdir(output_dir):
        if file.endswith(('.png', '.mp4')):
            filepath = os.path.join(output_dir, file)
            metadata = load_metadata(filepath)
            content.append({
                'type': 'banner' if file.endswith('.png') else 'video',
                'filepath': filepath,
                'filename': file,
                'metadata': metadata,
                'timestamp': os.path.getmtime(filepath)
            })
    
    content.sort(key=lambda x: x['timestamp'], reverse=True)
    return content

async def generate_banner_direct(campaign_name, brand_name, banner_type, message, cta, reference_image_path=""):
    """Generate banner by calling MCP server directly"""
    try:
        from banner_mcp_server import generate_banner
        
        result_json = await generate_banner(
            campaign_name=campaign_name,
            brand_name=brand_name,
            banner_type=banner_type,
            message=message,
            cta=cta,
            reference_image_path=reference_image_path
        )
        
        result = json.loads(result_json)
        return result
    except Exception as e:
        return {"error": str(e)}

async def validate_banner_direct(filepath, campaign_name, brand_name, message, cta):
    """Validate banner by calling MCP server directly"""
    try:
        from banner_mcp_server import validate_banner
        
        result_json = await validate_banner(
            filepath=filepath,
            campaign_name=campaign_name,
            brand_name=brand_name,
            message=message,
            cta=cta
        )
        
        result = json.loads(result_json)
        return result
    except Exception as e:
        return {"error": str(e)}

async def generate_video_direct(campaign_name, brand_name, video_type, description, resolution, aspect_ratio, input_image_path="", model="veo"):
    """Generate video by calling MCP server directly - supports both models and image-to-video"""
    try:
        from video_mcp_server import generate_video
        
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
        return result
    except Exception as e:
        return {"error": str(e)}

def fetch_weather(location):
    """Fetch weather data from API"""
    import requests
    try:
        # Using Open-Meteo API (free, no key needed)
        # First get coordinates for location
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
        geo_response = requests.get(geocode_url, timeout=10)
        geo_data = geo_response.json()
        
        if not geo_data.get('results'):
            return {"error": f"Location '{location}' not found"}
        
        lat = geo_data['results'][0]['latitude']
        lon = geo_data['results'][0]['longitude']
        
        # Get weather data
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto"
        weather_response = requests.get(weather_url, timeout=10)
        weather_data = weather_response.json()
        
        current = weather_data['current']
        
        # Map weather codes to conditions
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Foggy", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
            61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
            77: "Snow grains", 80: "Light showers", 81: "Showers", 82: "Heavy showers",
            85: "Light snow showers", 86: "Snow showers", 95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Heavy thunderstorm"
        }
        
        condition = weather_codes.get(current['weather_code'], "Unknown")
        
        return {
            "location": location,
            "temperature": current['temperature_2m'],
            "condition": condition,
            "wind_speed": current['wind_speed_10m'],
            "weather_code": current['weather_code']
        }
    except Exception as e:
        return {"error": str(e)}

async def generate_weather_banner(weather_data, font_family="Arial", primary_color="#1E90FF", secondary_color="#FFFFFF"):
    """Generate a banner based on weather conditions"""
    temp = weather_data['temperature']
    condition = weather_data['condition']
    location = weather_data['location']
    
    # Create weather-appropriate message
    if "rain" in condition.lower() or "drizzle" in condition.lower():
        message = f"Rainy Day in {location}"
        emoji = "🌧️"
    elif "snow" in condition.lower():
        message = f"Snowy Day in {location}"
        emoji = "❄️"
    elif "thunder" in condition.lower():
        message = f"Stormy Weather in {location}"
        emoji = "⛈️"
    elif "clear" in condition.lower():
        message = f"Sunny Day in {location}"
        emoji = "☀️"
    elif "cloud" in condition.lower():
        message = f"Cloudy Day in {location}"
        emoji = "☁️"
    elif "fog" in condition.lower():
        message = f"Foggy Day in {location}"
        emoji = "🌫️"
    else:
        message = f"Weather in {location}"
        emoji = "🌤️"
    
    # Generate banner with weather info
    campaign_name = f"Weather Update {datetime.now().strftime('%H:%M')}"
    brand_name = f"{emoji} Weather"
    cta = f"{int(temp)}°C"
    
    # Add font and color instructions to additional_instructions
    style_instructions = f"""
FONT STYLING:
- Use {font_family} font family or similar sans-serif font
- Make text bold and clear

COLOR SCHEME:
- Primary color: {primary_color} (use for main elements and background accents)
- Secondary color: {secondary_color} (use for text or contrast)
- Create a harmonious color palette based on these colors
- Ensure high contrast for readability

WEATHER THEME:
- Reflect the weather condition: {condition}
- Use weather-appropriate imagery and mood
"""
    
    from banner_mcp_server import generate_banner
    
    result_json = await generate_banner(
        campaign_name=campaign_name,
        brand_name=brand_name,
        banner_type="social",
        message=message,
        cta=cta,
        additional_instructions=style_instructions
    )
    
    return json.loads(result_json)

def check_weather_automation():
    """Check if weather automation should run"""
    if not st.session_state.weather_automation:
        return
    
    now = datetime.now()
    last_check = st.session_state.last_weather_check
    
    # Check if 15 minutes have passed or first run
    if last_check is None or (now - last_check).seconds >= 900:  # 900 seconds = 15 minutes
        st.session_state.last_weather_check = now
        
        # Fetch weather and generate banner
        weather_data = fetch_weather(st.session_state.weather_location)
        
        if "error" not in weather_data:
            # Get font and color from session state if available
            font = st.session_state.get('weather_font', 'Arial')
            primary = st.session_state.get('weather_primary_color', '#1E90FF')
            secondary = st.session_state.get('weather_secondary_color', '#FFFFFF')
            
            result = asyncio.run(generate_weather_banner(weather_data, font, primary, secondary))
            
            if result.get('success'):
                st.toast(f"🌤️ Weather banner generated for {weather_data['location']}!", icon="✅")
                return result
    
    return None

def main():
    # Check weather automation (runs every 15 minutes if enabled)
    check_weather_automation()
    
    # Header
    st.markdown('<h1 class="main-header">🎨 Marketing Content Generator</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎯 System")
        
        content = scan_output_directory()
        banners = len([c for c in content if c['type'] == 'banner'])
        videos = len([c for c in content if c['type'] == 'video'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📱 Banners", banners)
        with col2:
            st.metric("🎬 Videos", videos)
        
        st.markdown("---")
        
        # VIDEO MODEL SELECTION
        st.markdown("### 🎬 Video Model")
        video_model = st.radio(
            "Select AI Model:",
            options=['veo', 'runway'],
            format_func=lambda x: {
                'veo': '🔵 Google Veo 3.1 (Recommended)',
                'runway': '🟣 RunwayML Gen-3 Alpha'
            }[x],
            help="Choose which AI model to use for video generation",
            key='video_model_selector'
        )
        st.session_state.selected_video_model = video_model
        
        # Show model info
        if video_model == 'veo':
            st.info("**Veo 3.1**: High quality, up to 8 second long videos, takes 1 to 3 minutes to generate video")
        else:
            st.info("**RunwayML**: Fast generation, up to 10 second long videos, takes 2 min to generate video")
        
        st.markdown("---")
        
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.caption("**For Banners:**")
        st.caption("• Keep text short")
        st.caption("• 2-3 word brand names")
        st.caption("• Simple CTAs")
        st.caption("")
        st.caption("**For Videos:**")
        st.caption("• Describe visuals clearly")
        st.caption("• Include camera movements")
        st.caption("• Takes 1-3 minutes")
    
    # Main tabs
    tab1, tab2 = st.tabs(["🎨 Create Content", "🖼️ Gallery"])
    
    with tab1:
        st.markdown("### Create Marketing Content")
        
        # Add conversational prompt at the top
        st.markdown("#### 💬 Interactive AI Agent Chat")
        st.caption("Have a conversation with the AI agent - it will understand your requests and handle everything automatically")
        
        # Display conversation history
        if st.session_state.agent_conversation:
            st.markdown("##### 📜 Conversation History")
            for msg in st.session_state.agent_conversation:
                if msg['role'] == 'user':
                    with st.chat_message("user"):
                        st.write(msg['content'])
                else:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(msg['content'])
            
            # Clear conversation button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🗑️ Clear Chat", use_container_width=True):
                    st.session_state.agent_conversation = []
                    st.rerun()
        
        with st.form("prompt_form", clear_on_submit=True):
            user_prompt = st.text_area(
                "Your message:",
                placeholder="Examples:\n• use banner banner_social_1792x1024_20251025_162452.png to create a short video\n• Create a Black Friday banner for TechStore with 70% off\n• Slow zoom into center (as follow-up to previous request)\n• Make it 1080p instead",
                height=100,
                help="The agent maintains conversation context - you can ask follow-up questions!"
            )
            
            # IMAGE UPLOAD for AI agent
            st.markdown("##### 📎 Optional: Attach Image")
            agent_image = st.file_uploader(
                "Upload an image with your prompt",
                type=['png', 'jpg', 'jpeg'],
                help="Upload an image for style reference (banner) or to animate (video)",
                key="agent_upload_img"
            )
            
            prompt_submit = st.form_submit_button("💬 Send Message", type="primary", use_container_width=True)
        
        if prompt_submit and user_prompt:
            st.markdown("---")
            
            # Save uploaded image if provided
            agent_image_path = ""
            if agent_image is not None:
                outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
                if not os.path.exists(outputs_dir):
                    os.makedirs(outputs_dir)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                agent_img_filename = f"agent_upload_{timestamp}_{agent_image.name}"
                agent_image_path = os.path.join(outputs_dir, agent_img_filename)
                
                with open(agent_image_path, 'wb') as f:
                    f.write(agent_image.getbuffer())
                
                st.info(f"📎 Image attached: {agent_img_filename}")
                st.image(agent_image_path, caption="Attached image", width=300)
                
                # Add image path to prompt context
                user_prompt += f"\n\n[ATTACHED_IMAGE: {agent_image_path}]"
            
            try:
                from agent import fast
                
                async def run_agent_with_conversation(prompt, history):
                    async with fast.run() as agent:
                        if history:
                            context_messages = []
                            for msg in history[-6:]:
                                context_messages.append(f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}")
                            
                            full_context = "\n\n".join(context_messages)
                            full_prompt = f"CONVERSATION HISTORY:\n{full_context}\n\nCURRENT USER MESSAGE:\n{prompt}"
                        else:
                            full_prompt = prompt
                        
                        response = await agent.marketing_orchestrator.send(full_prompt)
                        return response
                
                with st.spinner("🤖 Agent is thinking..."):
                    result = asyncio.run(run_agent_with_conversation(
                        user_prompt, 
                        st.session_state.agent_conversation
                    ))
                    
                    st.session_state.agent_conversation.append({
                        'role': 'user',
                        'content': user_prompt
                    })
                    st.session_state.agent_conversation.append({
                        'role': 'assistant',
                        'content': result
                    })
                    
                    st.success("✅ Message sent!")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Agent Error: {str(e)}")
                st.info("💡 Try using the manual forms below instead")
        
        st.markdown("---")
        st.markdown("#### 📋 Manual Forms (Alternative)")
        st.caption("Prefer to fill forms manually? Use these instead of the AI agent chat")
        
        col_banner, col_video = st.columns(2)
        
        # BANNER CREATION
        with col_banner:
            st.markdown("#### 📱 Create Banner")
            
            with st.form("banner_form"):
                campaign = st.text_input("Campaign Name*", "Black Friday Sale", help="Name of your campaign")
                brand = st.text_input("Brand Name*", "TechStore", help="Keep it short (2-3 words)")
                banner_type = st.selectbox("Banner Type*", ["social", "leaderboard", "square"], 
                                          help="social: 1200×628, leaderboard: 728×90, square: 1024×1024")
                message = st.text_input("Message*", "Up to 70% Off", help="Keep under 8 words")
                cta = st.text_input("Call to Action*", "Shop Now", help="1-3 words like 'Shop Now'")
                
                # STYLE SETTINGS INSIDE FORM
                st.markdown("##### 🎨 Style Settings")
                col_style1, col_style2 = st.columns(2)
                with col_style1:
                    global_font = st.selectbox(
                        "Font Family",
                        options=['Default', 'Arial', 'Helvetica', 'Times New Roman', 'Georgia', 'Verdana', 'Courier', 'Impact', 'Comic Sans'],
                        help="Font will be used for this banner",
                        key='banner_font'
                    )
                        
                with col_style2:
                    global_color_mode = st.radio(
                        "Color Mode",
                        options=['Auto', 'Custom'],
                        horizontal=True,
                        help="Auto lets AI choose colors, Custom uses your colors",
                        key='banner_color_mode'
                    )
                
                # ALWAYS show color fields - ALWAYS ENABLED
                st.markdown("---")
                st.markdown("**🎨 Brand Colors**")
                
                if global_color_mode == 'Auto':
                    st.caption("ℹ️ Color Mode is set to 'Auto' - AI will choose colors. To use custom colors, select 'Custom' above.")
                else:
                    st.info("🎨 Enter hex color codes (e.g., #FF4B4B for red, #FFFFFF for white)")
                
                col_gc1, col_gc2 = st.columns(2)
                with col_gc1:
                    global_primary = st.text_input(
                        "🔴 Primary Color (Hex)", 
                        value='#FF4B4B', 
                        help="Enter hex code like #FF4B4B (red) or #0000FF (blue)", 
                        key='banner_primary',
                        max_chars=7,
                        placeholder="#FF4B4B"
                    )
                with col_gc2:
                    global_secondary = st.text_input(
                        "⚪ Secondary Color (Hex)", 
                        value='#FFFFFF', 
                        help="Enter hex code like #FFFFFF (white) or #000000 (black)", 
                        key='banner_secondary',
                        max_chars=7,
                        placeholder="#FFFFFF"
                    )
                
                # Show preview and validation only when Custom mode
                if global_color_mode == 'Custom':
                    if global_primary and global_secondary:
                        # Check if valid hex
                        import re
                        if re.match(r'^#[0-9A-Fa-f]{6}$', global_primary) and re.match(r'^#[0-9A-Fa-f]{6}$', global_secondary):
                            col_p1, col_p2 = st.columns(2)
                            with col_p1:
                                st.markdown(f'<div style="background-color: {global_primary}; padding: 15px; border-radius: 5px; text-align: center; color: white; font-weight: bold; border: 2px solid #ddd;">Primary Preview</div>', unsafe_allow_html=True)
                            with col_p2:
                                st.markdown(f'<div style="background-color: {global_secondary}; padding: 15px; border-radius: 5px; text-align: center; border: 2px solid #ddd; font-weight: bold;">Secondary Preview</div>', unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ Please enter valid hex codes (format: #RRGGBB)")
                    
                    # Common color suggestions
                    with st.expander("💡 Common Color Codes - Click to See Examples"):
                        st.markdown("""
                        **Reds:** #FF0000 (bright red) • #FF4B4B (coral red) • #DC143C (crimson)  
                        **Blues:** #0000FF (bright blue) • #1E90FF (dodger blue) • #4169E1 (royal blue)  
                        **Greens:** #00FF00 (bright green) • #32CD32 (lime green) • #228B22 (forest green)  
                        **Neutrals:** #FFFFFF (white) • #000000 (black) • #808080 (gray) • #CCCCCC (light gray)  
                        **Purples:** #800080 (purple) • #9370DB (medium purple) • #8B008B (dark purple)  
                        **Oranges:** #FFA500 (orange) • #FF8C00 (dark orange) • #FFD700 (gold)  
                        **Yellows:** #FFFF00 (yellow) • #FFD700 (gold) • #FFA500 (orange-yellow)
                        
                        💡 **Tip:** Copy and paste these codes into the fields above!
                        """)
                
                # IMAGE UPLOAD for style reference
                st.markdown("##### 📎 Optional: Upload Reference Image")
                reference_image = st.file_uploader(
                    "Upload an image for style inspiration (optional)",
                    type=['png', 'jpg', 'jpeg'],
                    help="Upload a reference image to guide the style, colors, and composition",
                    key="banner_ref_img"
                )
                
                # WEATHER CONDITIONS SELECTION - NOW INSIDE FORM
                st.markdown("##### 🌤️ Weather Conditions (Optional)")
                weather_enabled = st.checkbox(
                    "Include Weather Data",
                    value=st.session_state.get('include_weather', False),
                    help="Add current weather information to the banner",
                    key='include_weather_toggle'
                )
                
                # Initialize w_location with default
                w_location = st.session_state.weather_location
                
                if weather_enabled:
                    w_location = st.text_input(
                        "Location",
                        value=st.session_state.weather_location,
                        help="City name for weather data",
                        key='weather_location_input'
                    )
                    st.session_state.weather_location = w_location
                    
                    st.markdown("**Select Weather Data to Include:**")
                    col_w1, col_w2, col_w3 = st.columns(3)
                    with col_w1:
                        w_temp = st.checkbox("Temperature", value=True, key='w_temp')
                        w_condition = st.checkbox("Condition", value=True, key='w_condition')
                    with col_w2:
                        w_humidity = st.checkbox("Humidity", value=False, key='w_humidity')
                        w_wind = st.checkbox("Wind Speed", value=False, key='w_wind')
                    with col_w3:
                        w_description = st.checkbox("Description", value=True, key='w_description')
                    
                    # Store in session state
                    st.session_state.weather_includes = {
                        'temperature': w_temp,
                        'condition': w_condition,
                        'humidity': w_humidity,
                        'wind': w_wind,
                        'description': w_description
                    }
                
                submitted = st.form_submit_button("🎨 Generate Banner", type="primary", use_container_width=True)
            
            if submitted:
                # Update session state for weather automation to use these settings
                if global_font != 'Default':
                    st.session_state.weather_font = global_font
                if global_color_mode == 'Custom' and global_primary and global_secondary:
                    st.session_state.weather_primary_color = global_primary
                    st.session_state.weather_secondary_color = global_secondary
                
                if not all([campaign, brand, message, cta]):
                    st.error("Please fill in all required fields")
                else:
                    # Check if weather is enabled
                    weather_data = None
                    if weather_enabled and w_location:
                        with st.spinner("Fetching weather data..."):
                            weather_data = fetch_weather(w_location)
                            if "error" in weather_data:
                                st.warning(f"Weather API error: {weather_data['error']}. Generating banner without weather data.")
                                weather_data = None
                    
                    # Save reference image if uploaded
                    reference_image_path = ""
                    if reference_image is not None:
                        outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
                        if not os.path.exists(outputs_dir):
                            os.makedirs(outputs_dir)
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        ref_filename = f"reference_{timestamp}_{reference_image.name}"
                        reference_image_path = os.path.join(outputs_dir, ref_filename)
                        
                        with open(reference_image_path, 'wb') as f:
                            f.write(reference_image.getbuffer())
                        
                        st.info(f"📎 Reference image saved: {ref_filename}")
                    
                    # Use form's font and colors
                    font_to_use = global_font if global_font != 'Default' else 'Arial'
                    primary_to_use = global_primary if global_color_mode == 'Custom' and global_primary else '#FFFFFF'
                    secondary_to_use = global_secondary if global_color_mode == 'Custom' and global_secondary else '#000000'
                    
                    # Build style instructions
                    style_instructions = ""
                    if global_font != 'Default':
                        style_instructions += f"\nFONT: Use {global_font} font family or similar style."
                    if global_color_mode == 'Custom' and global_primary and global_secondary:
                        style_instructions += f"\nCOLORS: Primary color {global_primary}, Secondary color {global_secondary}. Use these colors prominently in the design."
                    
                    # Add weather data to message if available
                    final_message = message
                    final_cta = cta
                    if weather_data and "error" not in weather_data:
                        weather_includes = st.session_state.get('weather_includes', {
                            'temperature': True,
                            'condition': True,
                            'humidity': False,
                            'wind': False,
                            'description': True
                        })
                        
                        # Build weather info string - use .get() for safe access
                        weather_parts = []
                        if weather_includes.get('temperature') and 'temperature' in weather_data:
                            weather_parts.append(f"{weather_data['temperature']}°C")
                        if weather_includes.get('condition') and 'condition' in weather_data:
                            weather_parts.append(weather_data['condition'])
                        if weather_includes.get('humidity') and 'humidity' in weather_data:
                            weather_parts.append(f"{weather_data['humidity']}% humidity")
                        if weather_includes.get('wind') and 'wind_speed' in weather_data:
                            weather_parts.append(f"{weather_data['wind_speed']} km/h wind")
                        
                        weather_str = " | ".join(weather_parts)
                        final_message = f"{message} | {weather_str}" if weather_parts else message
                        
                        # Safely get description for CTA
                        if weather_includes.get('description') and 'description' in weather_data:
                            final_cta = weather_data.get('description', cta).title()
                    
                    with st.spinner("🎨 Generating banner... (10-30 seconds)"):
                        # Call modified function
                        from banner_mcp_server import generate_banner
                        
                        result_json = asyncio.run(generate_banner(
                            campaign_name=campaign,
                            brand_name=brand,
                            banner_type=banner_type,
                            message=final_message,
                            cta=final_cta,
                            additional_instructions=style_instructions,
                            reference_image_path=reference_image_path,
                            font_family=font_to_use,
                            primary_color=primary_to_use,
                            secondary_color=secondary_to_use,
                            weather_data=weather_data  # Pass weather data for scene modification
                        ))
                        result = json.loads(result_json)
                        
                        if "error" in result:
                            st.error(f"❌ Error: {result['error']}")
                        elif result.get("success"):
                            filepath = result['filepath']
                            st.success(f"✅ Banner generated: {result['filename']}")
                            
                            with st.spinner("🔍 Validating..."):
                                val_result = asyncio.run(validate_banner_direct(filepath, campaign, brand, message, cta))
                                
                                if val_result.get("passed"):
                                    st.success("✅ Validation PASSED!")
                                    scores = val_result.get('scores', {})
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("Brand", f"{scores.get('brand_visibility', 0)}/10")
                                    with col2:
                                        st.metric("Message", f"{scores.get('message_clarity', 0)}/10")
                                    with col3:
                                        st.metric("CTA", f"{scores.get('cta_effectiveness', 0)}/10")
                                else:
                                    st.warning("⚠️ Validation issues detected")
                                    if val_result.get('issues'):
                                        for issue in val_result['issues']:
                                            st.write(f"• {issue}")
                            
                            st.markdown("### 📦 Preview")
                            metadata = load_metadata(filepath)
                            display_banner(filepath, metadata, key_suffix="create_preview")
                            
                            st.info("💡 Switch to Gallery tab to see all your content!")
        
        # VIDEO CREATION
        with col_video:
            st.markdown("#### 🎬 Create Video")
            
            # Show selected model
            st.info(f"**Current Model:** {st.session_state.selected_video_model.upper()} (change in sidebar)")
            
            with st.form("video_form"):
                v_campaign = st.text_input("Campaign Name*", "Product Launch", help="Name of your campaign")
                v_brand = st.text_input("Brand Name*", "TechGear", help="Your brand name")
                v_type = st.selectbox("Duration*", ["short", "standard", "extended"], 
                                     help="short: 4s, standard: 6s, extended: 8s")
                v_description = st.text_area("Description*", 
                    "Camera slowly zooms in on product with dramatic lighting and soft electronic music",
                    help="Describe visuals, camera movements, and audio",
                    height=100)
                
                col1, col2 = st.columns(2)
                with col1:
                    v_resolution = st.selectbox("Resolution*", ["720p", "1080p"])
                with col2:
                    v_aspect = st.selectbox("Aspect Ratio*", ["16:9", "9:16"])
                
                # IMAGE UPLOAD for image-to-video
                st.markdown("##### 🎬 Optional: Upload Image to Animate")
                v_input_image = st.file_uploader(
                    "Upload an image to animate into video (optional)",
                    type=['png', 'jpg', 'jpeg'],
                    help="Upload an image that will be animated with the motion description above",
                    key="video_input_img"
                )
                
                v_submitted = st.form_submit_button("🎬 Generate Video", type="primary", use_container_width=True)
            
            if v_submitted:
                if not all([v_campaign, v_brand, v_description]):
                    st.error("Please fill in all required fields")
                else:
                    # Save input image if uploaded
                    v_input_image_path = ""
                    if v_input_image is not None:
                        outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
                        if not os.path.exists(outputs_dir):
                            os.makedirs(outputs_dir)
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        input_filename = f"video_input_{timestamp}_{v_input_image.name}"
                        v_input_image_path = os.path.join(outputs_dir, input_filename)
                        
                        with open(v_input_image_path, 'wb') as f:
                            f.write(v_input_image.getbuffer())
                        
                        st.info(f"📎 Input image saved: {input_filename}")
                        st.image(v_input_image_path, caption="Image to animate", width=300)
                    
                    with st.spinner(f"🎬 Generating video with {st.session_state.selected_video_model.upper()}... This takes 1-3 minutes. Please wait..."):
                        result = asyncio.run(generate_video_direct(
                            v_campaign, v_brand, v_type, v_description, v_resolution, v_aspect, 
                            input_image_path=v_input_image_path,
                            model=st.session_state.selected_video_model
                        ))
                        
                        if "error" in result:
                            st.error(f"❌ Error: {result['error']}")
                        elif result.get("success"):
                            st.success(f"✅ Video generated: {result['filename']}")
                            st.info("ℹ️ Please review the video manually")
                            
                            st.markdown("### 📦 Preview")
                            filepath = result['filepath']
                            metadata = load_metadata(filepath)
                            display_video(filepath, metadata, key_suffix="create_preview")
                            
                            st.info("💡 Switch to Gallery tab to see all your content!")
        
        st.markdown("---")
        
        # IMAGE-TO-VIDEO SECTION
        st.markdown("### ✨ Animate Banner Into Video")
        st.caption("Turn an existing banner into a dynamic video with motion and effects")
        
        # Show selected model
        st.info(f"**Current Model:** {st.session_state.selected_video_model.upper()} (change in sidebar)")
        
        with st.form("image_to_video_form"):
            outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
            banner_files = []
            if os.path.exists(outputs_dir):
                banner_files = [f for f in os.listdir(outputs_dir) if f.startswith('banner_') and f.endswith('.png')]
            
            if not banner_files:
                st.info("🔭 No banners available yet. Create a banner first, then come back to animate it!")
                st.form_submit_button("Generate (No banners available)", disabled=True)
            else:
                selected_banner = st.selectbox("Select Banner*", banner_files, 
                                             help="Choose which banner to animate")
                
                i2v_campaign = st.text_input("Campaign Name*", "Banner Animation", 
                                            help="Name for this video campaign")
                i2v_brand = st.text_input("Brand Name*", "TechStore", 
                                         help="Your brand name")
                
                i2v_type = st.selectbox("Video Duration*", ["short", "standard", "extended"],
                                       help="short: 4s, standard: 6s, extended: 8s",
                                       index=1)
                
                i2v_description = st.text_area("Motion Description*",
                    "Slow zoom into the center with subtle rotation and dramatic lighting sweep",
                    help="Describe camera movements, zoom, lighting effects, transitions",
                    height=100)
                
                col1, col2 = st.columns(2)
                with col1:
                    i2v_resolution = st.selectbox("Resolution*", ["720p", "1080p"], key="i2v_res")
                with col2:
                    i2v_aspect = st.selectbox("Aspect Ratio*", ["16:9", "9:16"], key="i2v_aspect")
                
                i2v_submitted = st.form_submit_button("✨ Animate Banner", type="primary", use_container_width=True)
        
        if banner_files and i2v_submitted:
            if not all([selected_banner, i2v_campaign, i2v_brand, i2v_description]):
                st.error("Please fill in all required fields")
            else:
                banner_path = os.path.join(outputs_dir, selected_banner)
                
                st.markdown("#### 🖼️ Source Banner")
                st.image(banner_path, width=400)
                
                with st.spinner(f"✨ Animating banner into video with {st.session_state.selected_video_model.upper()}... This takes 1-3 minutes. Please wait..."):
                    result = asyncio.run(generate_video_direct(
                        i2v_campaign, 
                        i2v_brand, 
                        i2v_type, 
                        i2v_description, 
                        i2v_resolution, 
                        i2v_aspect,
                        input_image_path=banner_path,
                        model=st.session_state.selected_video_model
                    ))
                    
                    if "error" in result:
                        st.error(f"❌ Error: {result['error']}")
                    elif result.get("success"):
                        st.success(f"✅ Video generated from banner: {result['filename']}")
                        st.info("🎬 Your banner has been animated with motion!")
                        
                        st.markdown("### 📦 Video Preview")
                        filepath = result['filepath']
                        metadata = load_metadata(filepath)
                        display_video(filepath, metadata, key_suffix="i2v_preview")
                        
                        st.info("💡 Switch to Gallery tab to see all your content!")
    
    with tab2:
        st.markdown("### 🖼️ Gallery - All Generated Content")
        
        content = scan_output_directory()
        
        if not content:
            st.info("🔭 No content yet. Go to the Create Content tab to generate your first banner or video!")
        else:
            filter_type = st.radio("Filter:", ["All", "Banners Only", "Videos Only"], horizontal=True)
            
            if filter_type == "Banners Only":
                content = [c for c in content if c['type'] == 'banner']
            elif filter_type == "Videos Only":
                content = [c for c in content if c['type'] == 'video']
            
            st.caption(f"Showing {len(content)} item(s)")
            
            for idx, item in enumerate(content):
                with st.container():
                    st.markdown(f"#### {item['filename']}")
                    st.caption(f"📅 {datetime.fromtimestamp(item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    if item['type'] == 'banner':
                        display_banner(item['filepath'], item['metadata'], key_suffix=f"gallery_{idx}")
                    else:
                        display_video(item['filepath'], item['metadata'], key_suffix=f"gallery_{idx}")
                    
                    st.divider()

if __name__ == "__main__":
    main()