#!/usr/bin/env python3
"""
BANNER GENERATION MCP SERVER - WITH IMAGEN 4 + DALL-E 3
Supports both Google Imagen 4 (default) and OpenAI DALL-E 3
"""

import os
import json
import base64
import yaml
from datetime import datetime
from openai import OpenAI
from google import genai
from google.genai import types
from PIL import Image
import io

# Banner specifications
BANNER_SPECS = {
    "digital_6_sheet": {"width": 1080, "height": 1920, "aspect": "9:16"},
    "leaderboard": {"width": 728, "height": 90, "aspect": "16:9"},
    "mpu": {"width": 300, "height": 250, "aspect": "4:3"},
    "mobile_banner_300x50": {"width": 300, "height": 50, "aspect": "16:9"},
    "mobile_banner_320x50": {"width": 320, "height": 50, "aspect": "16:9"},
    "social": {"width": 1200, "height": 628, "aspect": "16:9"},
    "square": {"width": 1024, "height": 1024, "aspect": "1:1"},
}

def load_api_keys():
    """Load API keys from secrets file"""
    secrets_path = os.path.join(os.path.dirname(__file__), 'fastagent.secrets.yaml')
    
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r') as f:
            secrets = yaml.safe_load(f)
        
        if 'openai' in secrets and 'api_key' in secrets['openai']:
            os.environ['OPENAI_API_KEY'] = secrets['openai']['api_key']
        
        if 'google' in secrets and 'api_key' in secrets['google']:
            os.environ['GOOGLE_API_KEY'] = secrets['google']['api_key']
        
        if 'anthropic' in secrets and 'api_key' in secrets['anthropic']:
            os.environ['ANTHROPIC_API_KEY'] = secrets['anthropic']['api_key']


def resize_to_exact(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize image to exact dimensions using smart crop"""
    orig_w, orig_h = image.size
    target_ratio = target_w / target_h
    orig_ratio = orig_w / orig_h
    
    if orig_ratio > target_ratio:
        new_h = target_h
        new_w = int(target_h * orig_ratio)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        image = image.crop((left, 0, left + target_w, target_h))
    else:
        new_w = target_w
        new_h = int(target_w / orig_ratio)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        top = (new_h - target_h) // 2
        image = image.crop((0, top, target_w, top + target_h))
    
    return image


def resize_to_exact(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize image to exact dimensions using smart crop"""
    orig_w, orig_h = image.size
    target_ratio = target_w / target_h
    orig_ratio = orig_w / orig_h
    
    if orig_ratio > target_ratio:
        new_h = target_h
        new_w = int(target_h * orig_ratio)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        image = image.crop((left, 0, left + target_w, target_h))
    else:
        new_w = target_w
        new_h = int(target_w / orig_ratio)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        top = (new_h - target_h) // 2
        image = image.crop((0, top, target_w, top + target_h))
    
    return image


async def generate_banner(
    campaign_name: str,
    brand_name: str,
    banner_type: str,
    message: str,
    cta: str,
    additional_instructions: str = "",
    reference_image_path: str = "",
    model: str = "imagen4",
    font_family: str = "Arial",
    primary_color: str = "#FFFFFF",
    secondary_color: str = "#000000",
    weather_data: dict = None
) -> str:
    """Generate banner using Imagen 4 (default) or DALL-E 3"""
    
    load_api_keys()
    
    if banner_type not in BANNER_SPECS:
        return json.dumps({"error": f"Invalid banner_type. Must be one of: {list(BANNER_SPECS.keys())}"})
    
    specs = BANNER_SPECS[banner_type]
    
    has_scene_description = additional_instructions and len(additional_instructions.strip()) > 10 and "NO TEXT" not in additional_instructions.upper()
    
    no_text = (
        "NO TEXT" in additional_instructions.upper() or
        (not brand_name and not message and not cta and not has_scene_description)
    )
    
    if no_text:
        brand_name = ""
        message = ""
        cta = ""
        print("🚫 NO-TEXT MODE")
    
    scene_only = has_scene_description and not brand_name and not message and not cta
    if scene_only:
        print("🎬 SCENE-ONLY MODE")
    
    weather_scene = ""
    if weather_data and isinstance(weather_data, dict) and "error" not in weather_data:
        condition = weather_data.get('condition', '').lower()
        temp = weather_data.get('temperature', 0)
        location = weather_data.get('location', '')
        weather_scene = f"{condition} weather, {temp}°C in {location}"
    
    if model.lower() in ["imagen", "imagen4", "imagen-4", "gemini"]:
        return await _generate_with_imagen(
            campaign_name, brand_name, banner_type, message, cta,
            additional_instructions, reference_image_path, specs,
            no_text, scene_only, weather_scene
        )
    else:
        return await _generate_with_dalle(
            campaign_name, brand_name, banner_type, message, cta,
            additional_instructions, reference_image_path, specs,
            no_text, scene_only, weather_scene, font_family, primary_color, secondary_color
        )


async def _generate_with_imagen(
    campaign_name, brand_name, banner_type, message, cta,
    additional_instructions, reference_image_path, specs,
    no_text, scene_only, weather_scene
) -> str:
    """Generate with Google Imagen 4"""
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return json.dumps({"error": "GOOGLE_API_KEY not set"})
    
    print("=" * 60)
    print(f"🎨 USING IMAGEN 4 | TARGET: {specs['width']}x{specs['height']}px")
    print("=" * 60)
    
    client = genai.Client(api_key=api_key)
    
    if reference_image_path and os.path.exists(reference_image_path):
        ref_image = Image.open(reference_image_path)
        
        if scene_only:
            is_photo = any(word in additional_instructions.lower() for word in ['hyperrealistic', 'photorealistic', 'realistic', 'photograph', 'photo', 'camera'])
            
            if is_photo:
                prompt = f"""Real photograph. Take the subject from this image and place it in this scene:

{additional_instructions}

{f"Weather: {weather_scene}" if weather_scene else ""}

Natural conditions, motion blur, film grain, authentic photo not CGI"""
            else:
                prompt = f"""Using the subject from this image, create this scene:

{additional_instructions}

{f"Weather: {weather_scene}" if weather_scene else ""}

Photorealistic, no text"""
            
            print(f"📝 PROMPT: {prompt[:150]}...")
            
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt, ref_image],
                config=types.GenerateContentConfig(
                    response_modalities=['Image'],
                    image_config=types.ImageConfig(aspect_ratio=specs.get('aspect', '1:1'))
                )
            )
        else:
            prompt = f"""Transform this image into a professional banner.

Brand: "{brand_name}" (large, bold)
Message: "{message}" (clear)
CTA: "{cta}" (button)

{additional_instructions if additional_instructions else ""}
{f"Weather: {weather_scene}" if weather_scene else ""}"""
            
            print(f"📝 PROMPT: {prompt[:150]}...")
            
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt, ref_image],
                config=types.GenerateContentConfig(
                    response_modalities=['Image'],
                    image_config=types.ImageConfig(aspect_ratio=specs.get('aspect', '1:1'))
                )
            )
    else:
        if no_text and weather_scene:
            prompt = f"""Create abstract visual art that conveys: {weather_scene}

Weather-appropriate colors, mood, and atmosphere.
NO text, NO words, NO letters.
Pure visual design."""
        elif scene_only:
            is_photo = any(word in additional_instructions.lower() for word in ['hyperrealistic', 'photorealistic', 'realistic', 'photograph', 'photo', 'camera'])
            
            if is_photo:
                prompt = f"""Real photograph.

{additional_instructions}

{f"Weather: {weather_scene}" if weather_scene else ""}

Natural lighting, film grain, authentic photo"""
            else:
                prompt = f"""{additional_instructions}

{f"Weather: {weather_scene}" if weather_scene else ""}

Photorealistic, no text"""
        else:
            prompt = f"""Professional banner for {brand_name}.

Brand: "{brand_name}" (prominent)
Message: "{message}"
CTA: "{cta}" (button)

{additional_instructions if additional_instructions else ""}
{f"Weather: {weather_scene}" if weather_scene else ""}"""
        
        print(f"📝 PROMPT: {prompt[:150]}...")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=['Image'],
                image_config=types.ImageConfig(aspect_ratio=specs.get('aspect', '1:1'))
            )
        )
    
    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            
            outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
            os.makedirs(outputs_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_filename = f"temp_{timestamp}.png"
            temp_filepath = os.path.join(outputs_dir, temp_filename)
            
            # Save original
            image.save(temp_filepath)
            
            # Load with PIL and resize
            pil_image = Image.open(temp_filepath)
            print(f"📏 Original: {pil_image.size[0]}x{pil_image.size[1]}px | Resizing to {specs['width']}x{specs['height']}px...")
            resized_image = resize_to_exact(pil_image, specs['width'], specs['height'])
            
            # Save final
            mode = "notext" if no_text else "text"
            filename = f"banner_{banner_type}_{mode}_{timestamp}.png"
            filepath = os.path.join(outputs_dir, filename)
            resized_image.save(filepath, quality=95)
            
            # Delete temp
            os.remove(temp_filepath)
            
            print(f"✅ Saved: {filename} ({specs['width']}x{specs['height']}px)")
            
            return json.dumps({
                "success": True,
                "filename": filename,
                "filepath": filepath,
                "dimensions": f"{specs['width']}x{specs['height']}",
                "model": "imagen4"
            })
    
    return json.dumps({"error": "No image generated"})


async def validate_banner(
    filepath: str,
    campaign_name: str,
    brand_name: str,
    message: str,
    cta: str
) -> str:
    """Validate banner content using Claude Vision API"""
    
    try:
        from anthropic import Anthropic
        from PIL import Image
        import base64
        import os
        
        if not os.path.exists(filepath):
            return json.dumps({"error": "File not found"})
        
        # Load API key
        load_api_keys()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return json.dumps({"error": "ANTHROPIC_API_KEY not set"})
        
        # Read and encode image
        with open(filepath, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        # Get image dimensions
        image = Image.open(filepath)
        width, height = image.size
        
        # Build validation prompt
        prompt = f"""Analyze this marketing banner and validate it against the campaign requirements.

**Campaign Details:**
- Brand: "{brand_name}"
- Message: "{message}"
- CTA: "{cta}"
- Banner Type: {width}x{height}px

**Validation Criteria:**
1. **Brand Visibility (0-10)**: Is the brand name "{brand_name}" clearly visible and prominent?
2. **Message Clarity (0-10)**: Is the message "{message}" clear and easy to read?
3. **CTA Effectiveness (0-10)**: Is the call-to-action "{cta}" prominent and actionable?
4. **Visual Coherence**: Does the imagery match the brand/message? (e.g., if brand is "TechStore" selling electronics, does the image show tech products or unrelated content like cars?)
5. **Design Quality**: Overall professional appearance, color contrast, composition

**Identify specific issues:**
- Brand name not visible or wrong
- Message unclear or missing
- CTA not prominent
- Visual mismatch (e.g., car image for tech store)
- Poor text contrast/readability
- Overcrowded or empty layout

Respond in JSON format:
{{
    "brand_visibility": <score 0-10>,
    "message_clarity": <score 0-10>,
    "cta_effectiveness": <score 0-10>,
    "visual_coherence": <score 0-10>,
    "design_quality": <score 0-10>,
    "issues": ["issue 1", "issue 2", ...],
    "passed": <true/false>,
    "summary": "brief overall assessment"
}}

Be critical and specific about mismatches between content and imagery."""

        # Call Claude Vision
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )
        
        # Parse response
        response_text = response.content[0].text
        
        print("=" * 60)
        print("CLAUDE VISION VALIDATION RESPONSE:")
        print(response_text)
        print("=" * 60)
        
        # Extract JSON from response (handle markdown code blocks)
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            validation_result = json.loads(json_match.group(0))
        else:
            print(f"ERROR: Could not find JSON in response")
            return json.dumps({"error": "Failed to parse validation response", "raw_response": response_text})
        
        # Add metadata
        validation_result["dimensions"] = f"{width}x{height}"
        
        # Calculate scores dict for compatibility
        validation_result["scores"] = {
            "brand_visibility": validation_result.get("brand_visibility", 0),
            "message_clarity": validation_result.get("message_clarity", 0),
            "cta_effectiveness": validation_result.get("cta_effectiveness", 0)
        }
        
        print("FINAL VALIDATION RESULT:")
        print(json.dumps(validation_result, indent=2))
        
        return json.dumps(validation_result)
        
    except Exception as e:
        return json.dumps({"error": str(e)})



async def _generate_with_dalle(
    campaign_name, brand_name, banner_type, message, cta,
    additional_instructions, reference_image_path, specs,
    no_text, scene_only, weather_scene, font_family, primary_color, secondary_color
) -> str:
    """Generate with DALL-E 3"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return json.dumps({"error": "OPENAI_API_KEY not set"})
    
    print("=" * 60)
    print(f"🎨 USING DALL-E 3 | TARGET: {specs['width']}x{specs['height']}px")
    print("=" * 60)
    
    client = OpenAI(api_key=api_key)
    width, height = specs['width'], specs['height']
    
    if scene_only:
        is_photo = any(word in additional_instructions.lower() for word in ['hyperrealistic', 'photorealistic', 'realistic', 'photograph', 'photo', 'camera'])
        
        if is_photo:
            prompt = f"""Real photograph.

{additional_instructions[:200]}

{f"Weather: {weather_scene}" if weather_scene else ""}

Natural conditions, film grain, authentic photo"""
        else:
            prompt = f"""{additional_instructions[:200]}

{f"Weather: {weather_scene}" if weather_scene else ""}

Photorealistic, no text"""
    else:
        prompt = f"""Banner: {width}x{height}px

Brand: "{brand_name}"
Message: "{message}"
CTA: "{cta}"

{additional_instructions[:100] if additional_instructions else ""}"""
    
    print(f"📝 PROMPT: {prompt[:200]}...")
    
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt[:1000],
        size="1792x1024",
        quality="hd",
        n=1
    )
    
    import requests
    img_url = response.data[0].url
    img_data = requests.get(img_url).content
    image = Image.open(io.BytesIO(img_data))
    
    print(f"📏 Original: {image.size[0]}x{image.size[1]}px | Resizing to {specs['width']}x{specs['height']}px...")
    image = resize_to_exact(image, specs['width'], specs['height'])
    
    outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "notext" if no_text else "text"
    filename = f"banner_{banner_type}_{mode}_{timestamp}.png"
    filepath = os.path.join(outputs_dir, filename)
    
    image.save(filepath, quality=95)
    
    print(f"✅ Saved: {filename} ({specs['width']}x{specs['height']}px)")
    
    return json.dumps({
        "success": True,
        "filename": filename,
        "filepath": filepath,
        "dimensions": f"{specs['width']}x{specs['height']}",
        "model": "dalle3"
    })


if __name__ == "__main__":
    import asyncio
    
    # Example usage
    # result = asyncio.run(generate_banner(
    #     campaign_name="Test",
    #     brand_name="",
    #     banner_type="social",
    #     message="",
    #     cta="",
    #     additional_instructions="photorealistic image of a car driving on a highway in rainy conditions",
    #     model="imagen4"
    # ))
    # print(result)
    pass