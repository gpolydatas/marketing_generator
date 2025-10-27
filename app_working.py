#!/usr/bin/env python3
"""
STREAMLIT WEB INTERFACE - FULLY FUNCTIONAL
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

def parse_prompt(prompt):
    """Parse prompt to extract parameters for banner or video generation"""
    prompt_lower = prompt.lower()
    
    # Determine type
    is_video = any(word in prompt_lower for word in ['video', 'clip', 'motion', 'animate'])
    is_banner = any(word in prompt_lower for word in ['banner', 'image', 'poster', 'ad'])
    
    result = {'type': None}
    
    if is_video:
        result['type'] = 'video'
        
        # CHECK FOR FILENAME - this means image-to-video!
        import re
        filename_match = re.search(r'(banner_[\w\-]+\.(?:png|jpg|jpeg))', prompt, re.IGNORECASE)
        if filename_match:
            result['input_image_path'] = f"outputs/{filename_match.group(1)}"
            result['source_filename'] = filename_match.group(1)
            result['is_image_to_video'] = True
            # Remove filename from description for motion-only description
            result['description'] = re.sub(r'banner_[\w\-]+\.(?:png|jpg|jpeg)', '', prompt, flags=re.IGNORECASE).strip()
            # Clean up description - remove "use banner", "to create", etc.
            result['description'] = re.sub(r'use\s+banner\s+|to\s+create\s+|from\s+', '', result['description'], flags=re.IGNORECASE).strip()
            if not result['description'] or len(result['description']) < 10:
                result['description'] = "Cinematic slow zoom into center with dynamic lighting effects"
        else:
            result['input_image_path'] = None
            result['source_filename'] = None
            result['is_image_to_video'] = False
            result['description'] = prompt
        
        # Extract video duration
        if 'short' in prompt_lower or '4 second' in prompt_lower or '4s' in prompt_lower:
            result['video_type'] = 'short'
        elif 'extended' in prompt_lower or 'long' in prompt_lower or '8 second' in prompt_lower or '8s' in prompt_lower:
            result['video_type'] = 'extended'
        else:
            result['video_type'] = 'standard'  # default 6s
        
        # Extract resolution
        if '1080p' in prompt_lower or '1080' in prompt_lower or 'high res' in prompt_lower or 'hd' in prompt_lower:
            result['resolution'] = '1080p'
        else:
            result['resolution'] = '720p'
        
        # Extract aspect ratio
        if '9:16' in prompt or '9x16' in prompt_lower or 'vertical' in prompt_lower or 'portrait' in prompt_lower or 'story' in prompt_lower or 'reel' in prompt_lower:
            result['aspect_ratio'] = '9:16'
        else:
            result['aspect_ratio'] = '16:9'  # default landscape
        
        # Description already set above (either cleaned or full prompt)
        
        # Try to extract brand/campaign from common patterns
        import re
        
        # Look for "for [brand]" or "[brand] video"
        brand_match = re.search(r'for\s+([A-Z][a-zA-Z0-9\s]+?)(?:\s+video|\s+with|\s*$)', prompt)
        if brand_match:
            result['brand'] = brand_match.group(1).strip()
        else:
            result['brand'] = 'Brand'
        
        # Look for campaign name
        campaign_match = re.search(r'([\w\s]+?)\s+(?:video|campaign)', prompt)
        if campaign_match:
            result['campaign'] = campaign_match.group(1).strip()
        else:
            result['campaign'] = 'Video Campaign'
    
    elif is_banner:
        result['type'] = 'banner'
        
        # Extract banner type
        if 'leaderboard' in prompt_lower:
            result['banner_type'] = 'leaderboard'
        elif 'square' in prompt_lower:
            result['banner_type'] = 'square'
        else:
            result['banner_type'] = 'social'  # default
        
        # Try to extract components using patterns
        import re
        
        # Look for brand name
        brand_match = re.search(r'for\s+([A-Z][a-zA-Z0-9]+)', prompt)
        if brand_match:
            result['brand'] = brand_match.group(1)
        else:
            result['brand'] = 'Brand'
        
        # Look for percentage/discount
        discount_match = re.search(r'(\d+%?\s*(?:off|discount|sale))', prompt, re.IGNORECASE)
        if discount_match:
            result['message'] = discount_match.group(1)
        else:
            result['message'] = 'Special Offer'
        
        # Look for CTA keywords
        if 'shop now' in prompt_lower:
            result['cta'] = 'Shop Now'
        elif 'buy now' in prompt_lower:
            result['cta'] = 'Buy Now'
        elif 'learn more' in prompt_lower:
            result['cta'] = 'Learn More'
        elif 'sign up' in prompt_lower:
            result['cta'] = 'Sign Up'
        else:
            result['cta'] = 'Learn More'
        
        # Campaign name
        campaign_match = re.search(r'([\w\s]+?)\s+(?:banner|sale|campaign)', prompt)
        if campaign_match:
            result['campaign'] = campaign_match.group(1).strip()
        else:
            result['campaign'] = 'Campaign'
    
    return result

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
        # Import the banner generation function
        from banner_mcp_server import generate_banner
        
        # Call the function
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

async def generate_video_direct(campaign_name, brand_name, video_type, description, resolution, aspect_ratio, input_image_path=""):
    """Generate video by calling MCP server directly - supports image-to-video"""
    try:
        from video_mcp_server import generate_video
        
        result_json = await generate_video(
            campaign_name=campaign_name,
            brand_name=brand_name,
            video_type=video_type,
            description=description,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            input_image_path=input_image_path  # NEW: Support for image-to-video
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
                # Import the agent
                from agent import fast
                
                # Build conversation history for the agent
                async def run_agent_with_conversation(prompt, history):
                    async with fast.run() as agent:
                        # If there's conversation history, include context
                        if history:
                            # Build conversation context
                            context_messages = []
                            for msg in history[-6:]:  # Last 3 exchanges (6 messages)
                                context_messages.append(f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}")
                            
                            full_context = "\n\n".join(context_messages)
                            full_prompt = f"CONVERSATION HISTORY:\n{full_context}\n\nCURRENT USER MESSAGE:\n{prompt}"
                        else:
                            full_prompt = prompt
                        
                        # Call the agent
                        response = await agent.marketing_orchestrator.send(full_prompt)
                        return response
                
                # Run the agent with conversation history
                with st.spinner("🤖 Agent is thinking..."):
                    result = asyncio.run(run_agent_with_conversation(
                        user_prompt, 
                        st.session_state.agent_conversation
                    ))
                    
                    # Add to conversation history
                    st.session_state.agent_conversation.append({
                        'role': 'user',
                        'content': user_prompt
                    })
                    st.session_state.agent_conversation.append({
                        'role': 'assistant',
                        'content': result
                    })
                    
                    # Show success and rerun to update display
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
                
                # IMAGE UPLOAD for style reference
                st.markdown("##### 🎨 Optional: Upload Reference Image")
                reference_image = st.file_uploader(
                    "Upload an image for style inspiration (optional)",
                    type=['png', 'jpg', 'jpeg'],
                    help="Upload a reference image to guide the style, colors, and composition",
                    key="banner_ref_img"
                )
                
                submitted = st.form_submit_button("🎨 Generate Banner", type="primary", use_container_width=True)
            
            # Handle submission OUTSIDE the form
            if submitted:
                if not all([campaign, brand, message, cta]):
                    st.error("Please fill in all required fields")
                else:
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
                    
                    with st.spinner("🎨 Generating banner... (10-30 seconds)"):
                        # Generate with reference image
                        result = asyncio.run(generate_banner_direct(
                            campaign, brand, banner_type, message, cta, 
                            reference_image_path=reference_image_path
                        ))
                        
                        if "error" in result:
                            st.error(f"❌ Error: {result['error']}")
                        elif result.get("success"):
                            filepath = result['filepath']
                            st.success(f"✅ Banner generated: {result['filename']}")
                            
                            # Validate
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
                            
                            # Display preview (NOW OUTSIDE FORM)
                            st.markdown("### 📦 Preview")
                            metadata = load_metadata(filepath)
                            display_banner(filepath, metadata, key_suffix="create_preview")
                            
                            st.info("💡 Switch to Gallery tab to see all your content!")
        
        # VIDEO CREATION
        with col_video:
            st.markdown("#### 🎬 Create Video")
            
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
            
            # Handle submission OUTSIDE the form
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
                    
                    with st.spinner("🎬 Generating video... This takes 1-3 minutes. Please wait..."):
                        result = asyncio.run(generate_video_direct(
                            v_campaign, v_brand, v_type, v_description, v_resolution, v_aspect,
                            input_image_path=v_input_image_path
                        ))
                        
                        if "error" in result:
                            st.error(f"❌ Error: {result['error']}")
                        elif result.get("success"):
                            st.success(f"✅ Video generated: {result['filename']}")
                            st.info("ℹ️ Please review the video manually")
                            
                            # Display preview (NOW OUTSIDE FORM)
                            st.markdown("### 📦 Preview")
                            filepath = result['filepath']
                            metadata = load_metadata(filepath)
                            display_video(filepath, metadata, key_suffix="create_preview")
                            
                            st.info("💡 Switch to Gallery tab to see all your content!")
        
        st.markdown("---")
        
        # IMAGE-TO-VIDEO SECTION
        st.markdown("### ✨ Animate Banner Into Video")
        st.caption("Turn an existing banner into a dynamic video with motion and effects")
        
        with st.form("image_to_video_form"):
            # Get available banners
            outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
            banner_files = []
            if os.path.exists(outputs_dir):
                banner_files = [f for f in os.listdir(outputs_dir) if f.startswith('banner_') and f.endswith('.png')]
            
            if not banner_files:
                st.info("📭 No banners available yet. Create a banner first, then come back to animate it!")
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
        
        # Handle submission OUTSIDE the form
        if banner_files and i2v_submitted:
            if not all([selected_banner, i2v_campaign, i2v_brand, i2v_description]):
                st.error("Please fill in all required fields")
            else:
                banner_path = os.path.join(outputs_dir, selected_banner)
                
                # Show preview of selected banner
                st.markdown("#### 🖼️ Source Banner")
                st.image(banner_path, width=400)
                
                with st.spinner("✨ Animating banner into video... This takes 1-3 minutes. Please wait..."):
                    result = asyncio.run(generate_video_direct(
                        i2v_campaign, 
                        i2v_brand, 
                        i2v_type, 
                        i2v_description, 
                        i2v_resolution, 
                        i2v_aspect,
                        input_image_path=banner_path  # KEY: Pass the banner path
                    ))
                    
                    if "error" in result:
                        st.error(f"❌ Error: {result['error']}")
                    elif result.get("success"):
                        st.success(f"✅ Video generated from banner: {result['filename']}")
                        st.info("🎬 Your banner has been animated with motion!")
                        
                        # Display preview
                        st.markdown("### 📦 Video Preview")
                        filepath = result['filepath']
                        metadata = load_metadata(filepath)
                        display_video(filepath, metadata, key_suffix="i2v_preview")
                        
                        st.info("💡 Switch to Gallery tab to see all your content!")
    
    with tab2:
        st.markdown("### 🖼️ Gallery - All Generated Content")
        
        content = scan_output_directory()
        
        if not content:
            st.info("📭 No content yet. Go to the Create Content tab to generate your first banner or video!")
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