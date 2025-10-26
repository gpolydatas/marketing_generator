#!/usr/bin/env python3
"""
STREAMLIT WEB INTERFACE - WITH MODEL SELECTION
Direct MCP tool calls without agent
"""

import streamlit as st
import os
import json
import asyncio
from datetime import datetime
import sys

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

# Helper functions
def load_metadata(filepath):
    """Load metadata JSON if exists"""
    metadata_file = filepath.replace('.png', '.json').replace('.mp4', '.json')
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return None

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

async def generate_banner_direct(campaign_name, brand_name, banner_type, message, cta):
    """Generate banner by calling MCP server directly"""
    try:
        from banner_mcp_server import generate_banner
        
        result_json = await generate_banner(
            campaign_name=campaign_name,
            brand_name=brand_name,
            banner_type=banner_type,
            message=message,
            cta=cta
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
    """Generate video by calling MCP server directly - supports both models"""
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
            model=model  # NEW: Pass model selection
        )
        
        result = json.loads(result_json)
        return result
    except Exception as e:
        return {"error": str(e)}

def main():
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
            st.info("**Veo 3.1**: High quality, supports image-to-video, 4-8 seconds, 1-3 min generation")
        else:
            st.info("**RunwayML**: Fast generation, up to 8 seconds, ~2 min generation")
        
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
        
        # Initialize conversation history in session state
        if 'agent_conversation' not in st.session_state:
            st.session_state.agent_conversation = []
        
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
            prompt_submit = st.form_submit_button("💬 Send Message", type="primary", use_container_width=True)
        
        if prompt_submit and user_prompt:
            st.markdown("---")
            
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
                
                submitted = st.form_submit_button("🎨 Generate Banner", type="primary", use_container_width=True)
            
            if submitted:
                if not all([campaign, brand, message, cta]):
                    st.error("Please fill in all required fields")
                else:
                    with st.spinner("🎨 Generating banner... (10-30 seconds)"):
                        result = asyncio.run(generate_banner_direct(campaign, brand, banner_type, message, cta))
                        
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
                
                v_submitted = st.form_submit_button("🎬 Generate Video", type="primary", use_container_width=True)
            
            if v_submitted:
                if not all([v_campaign, v_brand, v_description]):
                    st.error("Please fill in all required fields")
                else:
                    with st.spinner(f"🎬 Generating video with {st.session_state.selected_video_model.upper()}... This takes 1-3 minutes. Please wait..."):
                        result = asyncio.run(generate_video_direct(
                            v_campaign, v_brand, v_type, v_description, v_resolution, v_aspect, 
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