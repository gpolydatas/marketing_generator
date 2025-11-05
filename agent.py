#!/usr/bin/env python3
"""
MARKETING CONTENT ORCHESTRATOR AGENT - FIXED PARAMETER UPDATING
"""

import asyncio
import sys
import os
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the MCP servers directly
from banner_mcp_server import generate_banner, validate_banner
from video_mcp_server import generate_video

class MarketingOrchestrator:
    """Advanced marketing agent with proper parameter updating"""
    
    def __init__(self):
        self.conversation_state = {}
        self.max_context_messages = 3
    
    async def process_request(self, user_input: str, session_id: str = "default") -> str:
        """Process user requests with proper parameter updating"""
        
        # Initialize or get session
        if session_id not in self.conversation_state:
            self.conversation_state[session_id] = {
                'step': 'start',
                'content_type': None,
                'params': {},
                'context': [],
                'attached_image': None,
                'image_filename': None,
                'image_path': None,
                'missing_param': None  # Track what we're currently asking for
            }
        
        session = self.conversation_state[session_id]
        
        # Add user message to context
        session['context'].append({'role': 'user', 'content': user_input, 'timestamp': datetime.now()})
        
        # Keep only last N messages
        if len(session['context']) > self.max_context_messages * 2:
            session['context'] = session['context'][-self.max_context_messages * 2:]
        
        # Extract information from current and previous messages
        extracted_params = self._extract_parameters_from_context(session['context'])
        
        # Update session parameters with extracted info
        session['params'].update(extracted_params)
        
        # If we were asking for a specific parameter, store the user's response
        if session.get('missing_param'):
            param_name = session['missing_param']
            session['params'][param_name] = user_input.strip()
            session['missing_param'] = None
        
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
            session['step'] = 'generate_image_to_video'
        
        # Handle the current step
        if session['step'] == 'start':
            response = await self._handle_start_step(session)
            
        elif session['step'] == 'clarify_intent':
            response = await self._handle_clarify_intent(session)
            
        elif session['step'] == 'collect_banner_details':
            response = await self._handle_collect_banner_details(session)
            
        elif session['step'] == 'collect_video_details':
            response = await self._handle_collect_video_details(session)
            
        elif session['step'] == 'generate_banner':
            response = await self._generate_banner(session)
            
        elif session['step'] == 'generate_video':
            response = await self._generate_video(session)
            
        elif session['step'] == 'generate_image_to_video':
            response = await self._generate_image_to_video(session)
            
        else:
            response = "I'm not sure what to do next. Let's start over."
            session['step'] = 'start'
        
        # Add assistant response to context
        session['context'].append({'role': 'assistant', 'content': response, 'timestamp': datetime.now()})
        
        return response
    
    def _extract_parameters_from_context(self, context: List[Dict]) -> Dict:
        """Extract parameters from conversation context"""
        all_text = " ".join([msg['content'] for msg in context if msg['role'] == 'user'])
        
        params = {}
        
        # Extract brand names
        brand_patterns = [
            r'(?:brand|company|business)[:\s]+([A-Za-z0-9\s&]+?)(?:\s|$|,|\.)',
            r'(?:for|from)\s+([A-Za-z0-9\s&]+?)(?:\s|$|,|\.)',
        ]
        
        for pattern in brand_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                params['brand'] = match.group(1).strip()
                break
        
        # Extract campaign names
        campaign_patterns = [
            r'(?:campaign|promotion)[:\s]+([A-Za-z0-9\s]+?)(?:\s|$|,|\.)',
            r'\b(black friday|christmas|holiday|summer|winter|spring|fall|new year)\b',
        ]
        
        for pattern in campaign_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                params['campaign'] = match.group(1).strip().title()
                break
        
        # Extract messages/offers
        message_patterns = [
            r'(\d+% off)',
            r'(\d+% discount)',
            r'(up to \d+% off)',
            r'(free shipping)',
        ]
        
        for pattern in message_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                params['message'] = match.group(1)
                break
        
        # Extract CTAs
        cta_patterns = [
            r'\b(shop now|buy now|learn more|sign up|get started)\b'
        ]
        
        for pattern in cta_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                params['cta'] = match.group(1).title()
                break
        
        return params
    
    async def _handle_start_step(self, session: Dict) -> str:
        """Handle the initial step"""
        content_type = self._determine_content_type_from_context(session['context'])
        
        if content_type == 'banner':
            session['content_type'] = 'banner'
            if self._has_sufficient_banner_params(session['params']):
                session['step'] = 'generate_banner'
                return await self._generate_banner(session)
            else:
                session['step'] = 'collect_banner_details'
                return await self._handle_collect_banner_details(session)
                
        elif content_type == 'video':
            session['content_type'] = 'video'
            if session['image_path']:  # Image-to-video
                session['step'] = 'generate_image_to_video'
                return await self._generate_image_to_video(session)
            elif self._has_sufficient_video_params(session['params']):
                session['step'] = 'generate_video'
                return await self._generate_video(session)
            else:
                session['step'] = 'collect_video_details'
                return await self._handle_collect_video_details(session)
                
        elif content_type == 'image_to_video':
            session['content_type'] = 'image_to_video'
            session['step'] = 'generate_image_to_video'
            return await self._generate_image_to_video(session)
            
        else:
            session['step'] = 'clarify_intent'
            return await self._handle_clarify_intent(session)
    
    async def _handle_clarify_intent(self, session: Dict) -> str:
        """Ask user to clarify what they want to create"""
        return """What would you like me to create for you?

🎨 **Banner** - Static image for ads/social media
🎬 **Video** - Motion content with camera movements  
✨ **Animate existing image** - Turn a banner into video

Please tell me which you'd like!"""
    
    async def _handle_collect_banner_details(self, session: Dict) -> str:
        """Collect missing banner details"""
        params = session['params']
        
        if not params.get('brand'):
            session['missing_param'] = 'brand'
            return "🎨 I'll create a banner for you! What's your **brand name**? (Keep it short - 2-3 words work best!)"
        
        elif not params.get('message'):
            session['missing_param'] = 'message'
            return f"✅ Brand: {params['brand']}\n\nWhat's the **main message** for your banner? (Keep it concise - under 8 words!)"
        
        elif not params.get('cta'):
            session['missing_param'] = 'cta'
            return f"✅ Great! Message: {params['message']}\n\nWhat **call-to-action** should I use? (Simple 1-3 words like 'Shop Now')"
        
        else:
            # We have all parameters, proceed to generation
            session['step'] = 'generate_banner'
            return await self._generate_banner(session)
    
    async def _handle_collect_video_details(self, session: Dict) -> str:
        """Collect missing video details"""
        params = session['params']
        
        if not params.get('brand'):
            session['missing_param'] = 'brand'
            return "🎬 I'll create a video for you! What's your **brand name**?"
        
        elif not params.get('description'):
            session['missing_param'] = 'description'
            return f"✅ Brand: {params['brand']}\n\nPlease **describe the video**. What should happen visually? (Camera movements, actions, lighting)"
        
        else:
            # We have all parameters, proceed to generation
            session['step'] = 'generate_video'
            return await self._generate_video(session)
    
    async def _generate_banner(self, session: Dict) -> str:
        """Generate banner with collected parameters"""
        try:
            params = session['params']
            
            # Use collected parameters or defaults
            campaign = params.get('campaign', 'Marketing Campaign')
            brand = params.get('brand', 'Brand')
            banner_type = params.get('banner_type', 'social')
            message = params.get('message', 'Special Offer')
            cta = params.get('cta', 'Learn More')
            
            result_json = await generate_banner(
                campaign_name=campaign,
                brand_name=brand,
                banner_type=banner_type,
                message=message,
                cta=cta
            )
            
            result = json.loads(result_json)
            
            if "error" in result:
                session['step'] = 'start'
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
            
            # Reset for next conversation
            session['step'] = 'start'
            session['params'] = {}
            session['missing_param'] = None
            
            if validation.get('passed', False):
                scores = validation.get('scores', {})
                return f"""✅ Banner created successfully!

📋 Details:
• Brand: {brand}
• Message: {message} 
• CTA: {cta}
• Type: {banner_type}

📊 Validation PASSED!
• Brand: {scores.get('brand_visibility', 0)}/10
• Message: {scores.get('message_clarity', 0)}/10
• CTA: {scores.get('cta_effectiveness', 0)}/10

🎯 Your banner is ready: {result['filename']}
📥 Download: /files/{result['filename']}

What would you like to create next?"""
            else:
                return f"""⚠️ Banner created but needs improvement

📁 File: {result['filename']}
❌ Issues: {', '.join(validation.get('issues', []))}

What would you like to create next?"""
                    
        except Exception as e:
            session['step'] = 'start'
            return f"❌ Error: {str(e)}\n\nLet's try again. What would you like to create?"
    
    async def _generate_video(self, session: Dict) -> str:
        """Generate video with collected parameters"""
        try:
            params = session['params']
            
            campaign = params.get('campaign', 'Video Campaign')
            brand = params.get('brand', 'Brand')
            video_type = params.get('video_type', 'standard')
            description = params.get('description', 'Cinematic product showcase')
            
            result_json = await generate_video(
                campaign_name=campaign,
                brand_name=brand,
                video_type=video_type,
                description=description,
                resolution='720p',
                aspect_ratio='16:9',
                model='veo'
            )
            
            result = json.loads(result_json)
            
            session['step'] = 'start'
            session['params'] = {}
            session['missing_param'] = None
            
            if "error" in result:
                return f"❌ Error creating video: {result['error']}\n\nLet's try again. What would you like to create?"
            
            duration = self._get_video_duration(video_type)
            return f"""✅ Video created successfully!

📋 Details:
• Brand: {brand}
• Duration: {duration} seconds
• Description: {description}

⏳ Generation complete!
🎯 Your video is ready: {result['filename']}
📥 Download: /files/{result['filename']}

What would you like to create next?"""
                
        except Exception as e:
            session['step'] = 'start'
            return f"❌ Error: {str(e)}\n\nLet's try again. What would you like to create?"
    
    async def _generate_image_to_video(self, session: Dict) -> str:
        """Generate video from existing image"""
        try:
            if not session['image_path']:
                return "I need an image to animate. Please specify a filename like 'banner_social_123.png'"
            
            description = session['params'].get('description', 'Cinematic slow zoom with dynamic lighting effects')
            
            result_json = await generate_video(
                campaign_name="Banner Animation",
                brand_name="Brand",
                video_type='standard',
                description=description,
                resolution='720p',
                aspect_ratio='16:9',
                input_image_path=session['image_path'],
                model='veo'
            )
            
            result = json.loads(result_json)
            
            session['step'] = 'start'
            session['params'] = {}
            session['missing_param'] = None
            session['image_filename'] = None
            session['image_path'] = None
            
            if "error" in result:
                return f"❌ Error creating video: {result['error']}\n\nLet's try again. What would you like to create?"
            
            return f"""✅ Animated your image into a video!

🎬 Motion: {description}
📁 Generated: {result['filename']}
📥 Download: /files/{result['filename']}

What would you like to create next?"""
                
        except Exception as e:
            session['step'] = 'start'
            return f"❌ Error: {str(e)}\n\nLet's try again. What would you like to create?"
    
    def _determine_content_type_from_context(self, context: List[Dict]) -> str:
        """Determine content type from conversation context"""
        all_text = " ".join([msg['content'] for msg in context if msg['role'] == 'user']).lower()
        
        # Image-to-video has highest priority
        if any(indicator in all_text for indicator in ['animate', 'turn into video', 'make video from', '.png', '.jpg']):
            return 'image_to_video'
        
        # Banner indicators
        banner_score = sum(1 for indicator in ['banner', 'image', 'poster', 'static'] if indicator in all_text)
        
        # Video indicators
        video_score = sum(1 for indicator in ['video', 'clip', 'motion', 'animated', 'camera'] if indicator in all_text)
        
        if banner_score > video_score:
            return 'banner'
        elif video_score > banner_score:
            return 'video'
        else:
            return 'ambiguous'
    
    def _has_sufficient_banner_params(self, params: Dict) -> bool:
        """Check if we have enough parameters to generate a banner"""
        return all(key in params and params[key] for key in ['brand', 'message', 'cta'])
    
    def _has_sufficient_video_params(self, params: Dict) -> bool:
        """Check if we have enough parameters to generate a video"""
        return 'brand' in params and params['brand'] and 'description' in params and params['description']
    
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
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                filename = match.group(1)
                filepath = os.path.join("outputs", filename)
                return filename, filepath
        
        return None, None
    
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
    print("🎨 MARKETING CONTENT GENERATOR")
    print("="*80)
    print("🤖 Assistant: Hello! Tell me what you'd like to create.")
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
