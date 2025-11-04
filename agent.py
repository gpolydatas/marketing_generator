#!/usr/bin/env python3
"""
MARKETING CONTENT ORCHESTRATOR AGENT - FIXED PARAMETER HANDLING
"""

import asyncio
import sys
import os
import json
import re
from typing import Dict, List, Optional, Tuple

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the MCP servers directly
from banner_mcp_server import generate_banner, validate_banner
from video_mcp_server import generate_video

class MarketingOrchestrator:
    """Marketing agent with fixed parameter handling"""
    
    def __init__(self):
        self.conversation_state = {}
    
    async def process_request(self, user_input: str, session_id: str = "default") -> str:
        """Process user requests with proper conversational flow"""
        
        # Initialize or get session
        if session_id not in self.conversation_state:
            self.conversation_state[session_id] = {
                'step': 'start',
                'content_type': None,
                'params': {},
                'attached_image': None,
                'image_filename': None,
                'image_path': None
            }
        
        session = self.conversation_state[session_id]
        
        # Extract attached image if present
        attached_image_path = self._extract_attached_image(user_input)
        if attached_image_path:
            session['attached_image'] = attached_image_path
            user_input = user_input.replace(f"[ATTACHED_IMAGE: {attached_image_path}]", "").strip()
        
        # Check for image-to-video requests
        image_filename, image_path = self._detect_image_filename(user_input)
        if image_filename:
            session['image_filename'] = image_filename
            session['image_path'] = image_path
            session['content_type'] = 'image_to_video'
            session['step'] = 'ask_video_motion'
            return f"✨ I'll animate {image_filename} for you! What kind of **camera motion** would you like? (e.g., 'slow zoom', 'pan left to right', 'dramatic lighting')"
        
        # Handle based on current step
        if session['step'] == 'start':
            return await self._handle_start_step(user_input, session)
        
        elif session['step'] == 'determine_content_type':
            return await self._handle_content_type_step(user_input, session)
        
        elif session['step'] == 'ask_banner_brand':
            return await self._handle_banner_brand_step(user_input, session)
        
        elif session['step'] == 'ask_banner_message':
            return await self._handle_banner_message_step(user_input, session)
        
        elif session['step'] == 'ask_banner_cta':
            return await self._handle_banner_cta_step(user_input, session)
        
        elif session['step'] == 'ask_banner_type':
            # Parse the banner type and immediately generate
            banner_type = self._parse_banner_type(user_input)
            session['params']['banner_type'] = banner_type
            session['params']['campaign'] = session['params'].get('campaign', 'Marketing Campaign')
            return await self._generate_banner(session)
        
        elif session['step'] == 'ask_video_brand':
            return await self._handle_video_brand_step(user_input, session)
        
        elif session['step'] == 'ask_video_description':
            return await self._handle_video_description_step(user_input, session)
        
        elif session['step'] == 'ask_video_type':
            # Parse the video type and immediately generate
            video_type = self._parse_video_type(user_input)
            session['params']['video_type'] = video_type
            session['params']['campaign'] = session['params'].get('campaign', 'Video Campaign')
            session['params']['resolution'] = '720p'
            session['params']['aspect_ratio'] = '16:9'
            session['params']['model'] = 'veo'
            return await self._generate_video(session)
        
        elif session['step'] == 'ask_video_motion':
            return await self._handle_video_motion_step(user_input, session)
        
        elif session['step'] == 'ask_image_usage':
            return await self._handle_image_usage_step(user_input, session)
        
        else:
            return "I'm not sure what to do next. Let's start over."
    
    def _extract_attached_image(self, user_input: str) -> Optional[str]:
        """Extract attached image path from user input"""
        match = re.search(r'\[ATTACHED_IMAGE:\s*(.+?)\]', user_input)
        return match.group(1) if match else None
    
    def _detect_image_filename(self, user_input: str) -> Tuple[Optional[str], Optional[str]]:
        """Detect image filenames in user input for image-to-video"""
        patterns = [
            r'(\b\w+\.png\b)',
            r'(\b\w+\.jpg\b)',
            r'(\b\w+\.jpeg\b)',
            r'(\bbanner_\w+\.png\b)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                filename = match.group(1)
                filepath = os.path.join("outputs", filename)
                return filename, filepath
        
        return None, None
    
    async def _handle_start_step(self, user_input: str, session: Dict) -> str:
        """Handle the initial step - determine what user wants"""
        content_type = self._determine_content_type(user_input)
        
        if content_type == 'ambiguous':
            session['step'] = 'determine_content_type'
            return """I can help you create marketing content! What would you like?

🎨 **Banner** - Static image for ads/social media
🎬 **Video** - Motion content with camera movements
✨ **Animate existing image** - Turn a banner into video

Please tell me: "banner", "video", or "animate"?"""
        
        elif content_type == 'banner':
            session['content_type'] = 'banner'
            session['step'] = 'ask_banner_brand'
            return "🎨 Great! I'll create a banner for you. First, what's your **brand name**? (Keep it short - 2-3 words work best!)"
        
        elif content_type == 'video':
            session['content_type'] = 'video'
            session['step'] = 'ask_video_brand'
            return "🎬 Great! I'll create a video for you. First, what's your **brand name**?"
        
        elif content_type == 'image_to_video':
            session['content_type'] = 'image_to_video'
            session['step'] = 'ask_video_motion'
            return "✨ I see you want to animate an image! What kind of **camera motion** would you like? (e.g., 'slow zoom', 'pan left to right', 'dramatic lighting')"
        
        else:
            return "I'm not sure what you'd like to create. Please specify 'banner', 'video', or 'animate'."
    
    async def _handle_content_type_step(self, user_input: str, session: Dict) -> str:
        """Handle content type selection"""
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['banner', 'image', 'static', 'poster']):
            session['content_type'] = 'banner'
            session['step'] = 'ask_banner_brand'
            return "🎨 Great! I'll create a banner for you. First, what's your **brand name**? (Keep it short - 2-3 words work best!)"
        
        elif any(word in user_input_lower for word in ['video', 'motion', 'animate', 'clip']):
            session['content_type'] = 'video'
            session['step'] = 'ask_video_brand'
            return "🎬 Great! I'll create a video for you. First, what's your **brand name**?"
        
        else:
            return "I'm not sure what you'd like to create. Please choose: 'banner' or 'video'?"
    
    async def _handle_banner_brand_step(self, user_input: str, session: Dict) -> str:
        """Handle brand name input for banner"""
        session['params']['brand'] = user_input.strip()
        session['step'] = 'ask_banner_message'
        return f"✅ Brand: {user_input}\n\nNext, what's the **main message** for your banner? (Keep it concise - under 8 words!)"
    
    async def _handle_banner_message_step(self, user_input: str, session: Dict) -> str:
        """Handle message input for banner"""
        session['params']['message'] = user_input.strip()
        session['step'] = 'ask_banner_cta'
        return f"✅ Message: {user_input}\n\nNext, what **call-to-action** should I use? (Simple 1-3 words like 'Shop Now', 'Learn More')"
    
    async def _handle_banner_cta_step(self, user_input: str, session: Dict) -> str:
        """Handle CTA input for banner"""
        session['params']['cta'] = user_input.strip()
        session['step'] = 'ask_banner_type'
        return f"✅ CTA: {user_input}\n\nWhat **type of banner** would you like?\n• Social media (1200×628)\n• Leaderboard (728×90)  \n• Square (1024×1024)\n\nPlease tell me which type you prefer."
    
    async def _generate_banner(self, session: Dict) -> str:
        """Generate the banner and return result"""
        try:
            # Save parameters before resetting session
            brand = session['params']['brand']
            message = session['params']['message']
            cta = session['params']['cta']
            banner_type = session['params']['banner_type']
            campaign = session['params']['campaign']
            
            result_json = await generate_banner(
                campaign_name=campaign,
                brand_name=brand,
                banner_type=banner_type,
                message=message,
                cta=cta
            )
            
            result = json.loads(result_json)
            
            if "error" in result:
                # Reset on error
                session['step'] = 'start'
                session['params'] = {}
                return f"❌ Error creating banner: {result['error']}\n\nLet's try again. What would you like to create?"
            
            # Validate the banner
            validation_json = await validate_banner(
                filepath=result['filepath'],
                campaign_name=campaign,
                brand_name=brand,
                message=message,
                cta=cta
            )
            
            validation = json.loads(validation_json)
            
            # Reset session for next request
            session['step'] = 'start'
            session['params'] = {}
            
            if validation.get('passed', False):
                scores = validation.get('scores', {})
                return f"""✅ Banner created successfully!

📋 Your banner:
• Brand: {brand}
• Message: {message}
• CTA: {cta}
• Type: {banner_type} ({self._get_banner_dimensions(banner_type)})

📊 Validation PASSED!
• Brand visibility: {scores.get('brand_visibility', 0)}/10
• Message clarity: {scores.get('message_clarity', 0)}/10
• CTA effectiveness: {scores.get('cta_effectiveness', 0)}/10

🎯 Your banner is ready: {result['filename']}
📥 Download: /files/{result['filename']}

What would you like to create next?"""
            else:
                return f"""⚠️ Banner created but needs improvement

📁 File: {result['filename']}
❌ Issues: {', '.join(validation.get('issues', []))}

💡 Try adjusting your message or CTA and create another banner!

What would you like to create next?"""
                    
        except Exception as e:
            session['step'] = 'start'
            session['params'] = {}
            return f"❌ Error: {str(e)}\n\nLet's try again. What would you like to create?"
    
    async def _handle_video_brand_step(self, user_input: str, session: Dict) -> str:
        """Handle brand name input for video"""
        session['params']['brand'] = user_input.strip()
        session['step'] = 'ask_video_description'
        return f"✅ Brand: {user_input}\n\nNext, please **describe the video**. What should happen visually? (Camera movements, actions, lighting)"
    
    async def _handle_video_description_step(self, user_input: str, session: Dict) -> str:
        """Handle description input for video"""
        session['params']['description'] = user_input.strip()
        session['step'] = 'ask_video_type'
        return f"✅ Description: {user_input}\n\nWhat **duration** would you like?\n• Short (4 seconds)\n• Standard (6 seconds)\n• Extended (8 seconds)\n\nPlease tell me which duration you prefer."
    
    async def _generate_video(self, session: Dict) -> str:
        """Generate the video and return result"""
        try:
            # Save parameters before resetting session
            brand = session['params']['brand']
            description = session['params']['description']
            video_type = session['params']['video_type']
            campaign = session['params']['campaign']
            
            result_json = await generate_video(
                campaign_name=campaign,
                brand_name=brand,
                video_type=video_type,
                description=description,
                resolution=session['params']['resolution'],
                aspect_ratio=session['params']['aspect_ratio'],
                model=session['params']['model']
            )
            
            result = json.loads(result_json)
            
            # Reset session for next request
            session['step'] = 'start'
            session['params'] = {}
            
            if "error" in result:
                return f"❌ Error creating video: {result['error']}\n\nLet's try again. What would you like to create?"
            
            duration = self._get_video_duration(video_type)
            return f"""✅ Video created successfully!

📋 Your video:
• Brand: {brand}
• Duration: {duration} seconds
• Description: {description}

⏳ Generation complete!
🎯 Your video is ready: {result['filename']}
📥 Download: /files/{result['filename']}

What would you like to create next?"""
                
        except Exception as e:
            session['step'] = 'start'
            session['params'] = {}
            return f"❌ Error: {str(e)}\n\nLet's try again. What would you like to create?"
    
    async def _handle_video_motion_step(self, user_input: str, session: Dict) -> str:
        """Handle motion description for image-to-video and generate video"""
        session['params']['description'] = user_input.strip()
        session['params']['campaign'] = "Banner Animation"
        session['params']['brand'] = "Brand"
        session['params']['video_type'] = 'standard'
        session['params']['resolution'] = '720p'
        session['params']['aspect_ratio'] = '16:9'
        session['params']['model'] = 'veo'
        
        # Generate the video
        try:
            result_json = await generate_video(
                campaign_name=session['params']['campaign'],
                brand_name=session['params']['brand'],
                video_type=session['params']['video_type'],
                description=session['params']['description'],
                resolution=session['params']['resolution'],
                aspect_ratio=session['params']['aspect_ratio'],
                input_image_path=session['image_path'],
                model=session['params']['model']
            )
            
            result = json.loads(result_json)
            
            # Reset session for next request
            session['step'] = 'start'
            session['params'] = {}
            session['image_filename'] = None
            session['image_path'] = None
            
            if "error" in result:
                return f"❌ Error creating video: {result['error']}\n\nLet's try again. What would you like to create?"
            
            return f"""✅ Animated your banner into a video!

🎬 Motion: {session['params']['description']}
📁 Generated: {result['filename']}
📥 Download: /files/{result['filename']}

What would you like to create next?"""
                
        except Exception as e:
            session['step'] = 'start'
            session['params'] = {}
            return f"❌ Error: {str(e)}\n\nLet's try again. What would you like to create?"
    
    async def _handle_image_usage_step(self, user_input: str, session: Dict) -> str:
        """Handle how to use attached image"""
        user_input_lower = user_input.lower()
        
        if 'banner' in user_input_lower:
            session['content_type'] = 'banner'
            session['step'] = 'ask_banner_brand'
            return "🎨 Great! I'll use your image as style reference for a banner. First, what's your **brand name**?"
        
        elif 'video' in user_input_lower:
            session['content_type'] = 'video'
            session['step'] = 'ask_video_brand'
            return "🎬 Great! I'll animate your image into a video. First, what's your **brand name**?"
        
        else:
            return "Please tell me: use the image for a 'banner' or 'video'?"
    
    def _determine_content_type(self, user_input: str) -> str:
        """Determine content type from user input"""
        user_input_lower = user_input.lower()
        
        # Image-to-video triggers
        image_to_video_triggers = ['animate', 'turn into video', 'make video from', 'video from', 'use banner']
        if any(trigger in user_input_lower for trigger in image_to_video_triggers):
            return 'image_to_video'
        
        # Banner triggers
        banner_triggers = ['banner', 'image', 'poster', 'static', 'display ad', 'website banner']
        banner_score = sum(1 for trigger in banner_triggers if trigger in user_input_lower)
        
        # Video triggers  
        video_triggers = ['video', 'clip', 'motion', 'animated', 'reel', 'tiktok']
        video_score = sum(1 for trigger in video_triggers if trigger in user_input_lower)
        
        if banner_score > video_score:
            return 'banner'
        elif video_score > banner_score:
            return 'video'
        else:
            return 'ambiguous'
    
    def _parse_banner_type(self, user_input: str) -> str:
        """Smart parsing of banner type from user input"""
        user_input_lower = user_input.lower()
        
        # Social media banner patterns
        social_patterns = [
            'social', 'social media', 'facebook', 'instagram', 'twitter', 'linkedin',
            '1200', '628', '1200×628', '1200x628', 'feed', 'post', 'timeline'
        ]
        
        # Leaderboard banner patterns  
        leaderboard_patterns = [
            'leaderboard', 'banner', 'wide', '728', '90', '728×90', '728x90',
            'header', 'top banner', 'website banner', 'ad banner', 'wide banner'
        ]
        
        # Square banner patterns
        square_patterns = [
            'square', '1024', '1024×1024', '1024x1024', 'instagram story', 'profile',
            '1:1', 'equal', 'profile picture', 'square post'
        ]
        
        # Count matches for each type
        social_score = sum(1 for pattern in social_patterns if pattern in user_input_lower)
        leaderboard_score = sum(1 for pattern in leaderboard_patterns if pattern in user_input_lower) 
        square_score = sum(1 for pattern in square_patterns if pattern in user_input_lower)
        
        # Return the type with highest score, default to social
        if social_score > leaderboard_score and social_score > square_score:
            return "social"
        elif leaderboard_score > social_score and leaderboard_score > square_score:
            return "leaderboard" 
        elif square_score > social_score and square_score > leaderboard_score:
            return "square"
        else:
            # Default to social if no clear winner
            return "social"
    
    def _parse_video_type(self, user_input: str) -> str:
        """Smart parsing of video type from user input"""
        user_input_lower = user_input.lower()
        
        # Short video patterns
        short_patterns = [
            'short', '4', '4s', '4 seconds', 'quick', 'brief', 'reel', 'tiktok',
            'snack', 'bite-sized'
        ]
        
        # Standard video patterns
        standard_patterns = [
            'standard', 'normal', 'regular', '6', '6s', '6 seconds', 'default',
            'medium', 'average'
        ]
        
        # Extended video patterns  
        extended_patterns = [
            'extended', 'long', '8', '8s', '8 seconds', 'full', 'detailed',
            'comprehensive', 'lengthy'
        ]
        
        # Count matches for each type
        short_score = sum(1 for pattern in short_patterns if pattern in user_input_lower)
        standard_score = sum(1 for pattern in standard_patterns if pattern in user_input_lower)
        extended_score = sum(1 for pattern in extended_patterns if pattern in user_input_lower)
        
        # Return the type with highest score, default to standard
        if short_score > standard_score and short_score > extended_score:
            return "short"
        elif extended_score > short_score and extended_score > standard_score:
            return "extended"
        else:
            return "standard"
    
    def _get_banner_dimensions(self, banner_type: str) -> str:
        """Get dimensions for banner type"""
        dimensions = {
            "social": "1200×628 pixels",
            "leaderboard": "728×90 pixels", 
            "square": "1024×1024 pixels"
        }
        return dimensions.get(banner_type, "1200×628 pixels")
    
    def _get_video_duration(self, video_type: str) -> int:
        """Get duration in seconds for video type"""
        durations = {"short": 4, "standard": 6, "extended": 8}
        return durations.get(video_type, 6)

# Create the orchestrator instance
orchestrator = MarketingOrchestrator()

async def run_single_prompt(prompt: str, session_id: str = "default") -> str:
    """Run the agent with a single prompt"""
    return await orchestrator.process_request(prompt, session_id)

async def main():
    """Main interactive loop"""
    print("\n" + "="*80)
    print("🎨 MARKETING CONTENT GENERATION SYSTEM")
    print("="*80)
    print("🤖 Assistant: Hello! I'll guide you through creating marketing content.")
    print("I'll ask one question at a time to make it easy!")
    print("="*80)
    
    session_id = "cli_session"
    
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'bye']:
                break
                
            response = await run_single_prompt(user_input, session_id)
            print(f"\n🤖 Assistant: {response}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
