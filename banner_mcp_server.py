#!/usr/bin/env python3
"""
BANNER GENERATION MCP SERVER
Exposes banner generation and validation as MCP tools
"""

import os
import json
import base64
from datetime import datetime
from openai import OpenAI
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Banner specifications
BANNER_SPECS = {
    "leaderboard": {"width": 728, "height": 90},
    "social": {"width": 1200, "height": 628},
    "square": {"width": 1024, "height": 1024},
}

# Create MCP server
app = Server("banner-tools")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="generate_banner",
            description="Generate a banner advertisement using DALL-E 3",
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
                    "banner_type": {
                        "type": "string",
                        "enum": ["leaderboard", "social", "square"],
                        "description": "Type of banner"
                    },
                    "message": {
                        "type": "string",
                        "description": "Main marketing message to display"
                    },
                    "cta": {
                        "type": "string",
                        "description": "Call-to-action text"
                    },
                    "additional_instructions": {
                        "type": "string",
                        "description": "Optional additional instructions for regeneration",
                        "default": ""
                    }
                },
                "required": ["campaign_name", "brand_name", "banner_type", "message", "cta"]
            }
        ),
        Tool(
            name="validate_banner",
            description="Validate a generated banner against quality guidelines",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Full path to the banner image file"
                    },
                    "campaign_name": {
                        "type": "string",
                        "description": "Name of campaign for context"
                    },
                    "brand_name": {
                        "type": "string",
                        "description": "Expected brand name"
                    },
                    "message": {
                        "type": "string",
                        "description": "Expected main message"
                    },
                    "cta": {
                        "type": "string",
                        "description": "Expected call-to-action text"
                    }
                },
                "required": ["filepath", "campaign_name", "brand_name", "message", "cta"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    
    if name == "generate_banner":
        result = await generate_banner(**arguments)
        return [TextContent(type="text", text=result)]
    
    elif name == "validate_banner":
        result = await validate_banner(**arguments)
        return [TextContent(type="text", text=result)]
    
    else:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def generate_banner(
    campaign_name: str,
    brand_name: str,
    banner_type: str,
    message: str,
    cta: str,
    additional_instructions: str = ""
) -> str:
    """Generate banner image using DALL-E 3"""
    
    # Validate banner type
    if banner_type not in BANNER_SPECS:
        return json.dumps({
            "error": f"Invalid banner_type. Must be one of: {list(BANNER_SPECS.keys())}"
        })
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return json.dumps({
            "error": "OPENAI_API_KEY environment variable not set"
        })
    
    # Generate prompt
    specs = BANNER_SPECS[banner_type]
    
    # ENHANCED PROMPT - Focus on text clarity and accuracy
    prompt = f"""Create a professional banner advertisement for {brand_name}'s {campaign_name}.

CRITICAL - TEXT MUST BE EXACT AND LEGIBLE:
- Brand name: "{brand_name}" (spell exactly, make it LARGE and BOLD)
- Main message: "{message}" (use these exact words, make it clear and readable)  
- CTA button: "{cta}" (spell exactly, put on a prominent button)

DESIGN REQUIREMENTS:
- Dimensions: {specs['width']}x{specs['height']} pixels
- Style: Clean, modern, professional advertising
- Layout: Simple and uncluttered - text must be the focus
- Typography: Sans-serif fonts, high contrast, very legible
- Brand prominence: Brand name is the largest element
- CTA visibility: Call-to-action button stands out with bright color
- Color scheme: Professional, vibrant, eye-catching
- Background: Clean or subtle - must not interfere with text readability

TEXT HIERARCHY (in order of size):
1. "{brand_name}" - Biggest, boldest, top or center
2. "{message}" - Medium size, center area
3. "{cta}" - On button, bottom or prominent position

CRITICAL RULES:
- Text must be crystal clear and easy to read
- No decorative text or extra words
- No complex patterns behind text
- High contrast between text and background
- Professional advertising quality

Make the text perfect - that's the priority."""
    
    # Add additional instructions if provided
    if additional_instructions:
        prompt += f"\n\nIMPROVEMENTS FOR THIS ATTEMPT:\n{additional_instructions}"
        prompt += f"\n\nREMINDER: Brand='{brand_name}', Message='{message}', CTA='{cta}' - spell exactly!"
    
    prompt = prompt[:4000]  # DALL-E limit
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Determine DALL-E size
    width = specs['width']
    height = specs['height']
    
    if width == height:
        size = "1024x1024"
    elif width > height:
        size = "1792x1024"
    else:
        size = "1024x1792"
    
    try:
        # Generate image
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="hd",
            style="vivid",
            n=1
        )
        
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt
        
        # Download image
        import requests
        img_response = requests.get(image_url)
        
        if img_response.status_code == 200:
            # Save with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"banner_{banner_type}_{size}_{timestamp}.png"
            
            # Save to local outputs directory
            output_dir = os.path.join(os.path.dirname(__file__), "outputs")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            
            file_size = len(img_response.content) / 1024 / 1024
            
            # Save metadata
            metadata = {
                "campaign": campaign_name,
                "brand": brand_name,
                "banner_type": banner_type,
                "message": message,
                "cta": cta,
                "additional_instructions": additional_instructions,
                "filename": filename,
                "filepath": filepath,
                "url": image_url,
                "size": size,
                "file_size_mb": round(file_size, 2),
                "revised_prompt": revised_prompt,
                "timestamp": datetime.now().isoformat()
            }
            
            metadata_file = filepath.replace('.png', '.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return json.dumps({
                "success": True,
                "filename": filename,
                "filepath": filepath,
                "url": image_url,
                "size": size,
                "file_size_mb": round(file_size, 2),
                "revised_prompt": revised_prompt,
                "metadata_file": metadata_file
            }, indent=2)
        else:
            return json.dumps({
                "error": "Failed to download image from DALL-E"
            })
            
    except Exception as e:
        return json.dumps({
            "error": f"DALL-E API error: {str(e)}"
        })


async def validate_banner(
    filepath: str,
    campaign_name: str,
    brand_name: str,
    message: str,
    cta: str
) -> str:
    """Validate banner using Claude's vision capabilities"""
    
    # Check if file exists
    if not os.path.exists(filepath):
        return json.dumps({
            "error": f"File not found: {filepath}"
        })
    
    try:
        # Read the image file
        with open(filepath, 'rb') as f:
            image_data = f.read()
        
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Use Anthropic API to validate the image
        from anthropic import Anthropic
        
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            return json.dumps({
                "error": "ANTHROPIC_API_KEY environment variable not set"
            })
        
        client = Anthropic(api_key=anthropic_key)
        
        validation_prompt = f"""You are an expert banner advertisement validator. Analyze this banner image and validate it against professional standards.

EXPECTED CONTENT:
- Campaign: {campaign_name}
- Brand: {brand_name}
- Main Message: {message}
- Call-to-Action: {cta}

VALIDATION CRITERIA:

1. BRAND VISIBILITY (1-10): Is there a clear brand name visible and prominent? 
   - IMPORTANT: The text doesn't need to be exactly "{brand_name}" - similar text, recognizable brand elements, or close matches are acceptable
   - Focus on: Is there prominent branding? Is it readable? Is it well-positioned?

2. MESSAGE CLARITY (1-10): Is there a clear main message that's readable?
   - IMPORTANT: The message doesn't need to match "{message}" word-for-word
   - Focus on: Is there a clear value proposition? Is the text legible? Does it communicate the offer?

3. CTA EFFECTIVENESS (1-10): Is there a clear call-to-action?
   - IMPORTANT: The CTA doesn't need to say exactly "{cta}" - similar action words work
   - Focus on: Is there a prominent button/CTA? Is it actionable? Does it stand out?

4. VISUAL APPEAL (1-10): Is the design eye-catching, modern, and professional?
   - Focus on: Color scheme, layout, visual hierarchy, professional appearance

5. OVERALL QUALITY (1-10): Overall professional quality for advertising
   - Focus on: Suitable for digital advertising? High quality? Professional appearance?

TEXT ACCURACY GUIDELINES:
- Be LENIENT with text matching - AI-generated images often have imperfect text
- If the brand name is close or recognizable, score it high
- If the message conveys the right idea even with different words, score it high  
- If there's a clear CTA button/text with action words, score it high
- Deduct points only for: completely illegible text, gibberish, or missing elements

SCORING GUIDELINES:
- 9-10: Excellent, professional quality
- 7-8: Good, acceptable for advertising (THIS IS THE PASS THRESHOLD)
- 5-6: Fair, but has issues
- 1-4: Poor, needs significant improvement

Provide your assessment in this exact JSON format:
{{
    "passed": true/false,
    "scores": {{
        "brand_visibility": X,
        "message_clarity": X,
        "cta_effectiveness": X,
        "visual_appeal": X,
        "overall_quality": X
    }},
    "issues": ["list of specific issues found"],
    "recommendations": ["list of improvements if failed"],
    "feedback": "detailed feedback message"
}}

PASS if all scores >= 7 and banner has clear branding, message, and CTA.
FAIL if any score < 7 or critical elements are missing/illegible.

Be reasonable and practical - focus on whether this banner would work for advertising, not whether text matches perfectly."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": validation_prompt
                        }
                    ]
                }
            ]
        )
        
        # Extract the JSON response
        validation_text = response.content[0].text
        
        # Try to extract JSON from the response
        import re
        json_match = re.search(r'\{.*\}', validation_text, re.DOTALL)
        if json_match:
            validation_result = json.loads(json_match.group())
            return json.dumps(validation_result, indent=2)
        else:
            return json.dumps({
                "passed": False,
                "scores": {},
                "issues": ["Could not parse validation response"],
                "recommendations": ["Please regenerate the banner"],
                "feedback": validation_text
            })
            
    except Exception as e:
        return json.dumps({
            "error": f"Validation error: {str(e)}"
        })


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