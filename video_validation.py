#!/usr/bin/env python3
"""
VIDEO VALIDATION MODULE
Uses Claude Vision API to analyze video quality, content, and adherence to campaign requirements
"""

import os
import json
import base64
import subprocess
import tempfile
from pathlib import Path
from anthropic import Anthropic


def extract_video_frames(video_path: str, num_frames: int = 6) -> list[str]:
    """
    Extract frames from video for analysis
    
    Args:
        video_path: Path to video file
        num_frames: Number of frames to extract (default: 6 for comprehensive analysis)
    
    Returns:
        List of temporary frame file paths
    """
    try:
        # Create temp directory for frames
        temp_dir = tempfile.mkdtemp()
        frame_paths = []
        
        # Get video duration first
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"⚠️ Could not determine video duration, using default intervals")
            duration = 6.0
        else:
            try:
                duration = float(result.stdout.strip())
            except:
                duration = 6.0
        
        # Calculate frame intervals
        interval = duration / (num_frames + 1)
        
        # Extract frames at calculated intervals
        for i in range(1, num_frames + 1):
            timestamp = interval * i
            frame_path = os.path.join(temp_dir, f'frame_{i:02d}.jpg')
            
            # Use ffmpeg to extract frame
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                frame_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(frame_path):
                frame_paths.append(frame_path)
                print(f"✅ Extracted frame {i} at {timestamp:.2f}s")
            else:
                print(f"⚠️ Failed to extract frame {i}")
        
        return frame_paths
        
    except FileNotFoundError:
        print("❌ ffmpeg not found. Please install ffmpeg to enable video validation.")
        print("   Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("   macOS: brew install ffmpeg")
        print("   Windows: Download from https://ffmpeg.org/download.html")
        return []
    except subprocess.TimeoutExpired:
        print("❌ Frame extraction timed out")
        return []
    except Exception as e:
        print(f"❌ Error extracting frames: {str(e)}")
        return []


def get_video_metadata(video_path: str) -> dict:
    """Extract technical metadata from video file"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,bit_rate,codec_name,r_frame_rate',
            '-show_entries', 'format=size,duration',
            '-of', 'json',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            stream = data.get('streams', [{}])[0]
            format_info = data.get('format', {})
            
            return {
                'width': stream.get('width'),
                'height': stream.get('height'),
                'duration': float(format_info.get('duration', 0)),
                'codec': stream.get('codec_name'),
                'frame_rate': stream.get('r_frame_rate'),
                'file_size_mb': int(format_info.get('size', 0)) / 1024 / 1024
            }
    except Exception as e:
        print(f"⚠️ Could not extract video metadata: {e}")
    
    return {}


async def validate_video_with_claude(
    filepath: str,
    campaign_name: str,
    brand_name: str,
    description: str,
    expected_duration: int = None,
    expected_resolution: str = None,
    expected_aspect_ratio: str = None
) -> dict:
    """
    Validate video using Claude Vision API
    
    Args:
        filepath: Path to video file
        campaign_name: Expected campaign name
        brand_name: Expected brand name
        description: Expected video description/requirements
        expected_duration: Expected duration in seconds
        expected_resolution: Expected resolution (e.g., "1080p", "720p")
        expected_aspect_ratio: Expected aspect ratio (e.g., "16:9", "9:16")
    
    Returns:
        Validation result dictionary
    """
    
    # Check if video exists
    if not os.path.exists(filepath):
        return {"error": f"Video file not found: {filepath}"}
    
    # Load API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set"}
    
    print("=" * 80)
    print("🎬 VIDEO VALIDATION")
    print("=" * 80)
    print(f"📁 Video: {os.path.basename(filepath)}")
    print(f"🎯 Campaign: {campaign_name}")
    print(f"🏢 Brand: {brand_name}")
    print("=" * 80)
    
    # Extract video metadata
    print("📊 Extracting video metadata...")
    video_metadata = get_video_metadata(filepath)
    
    if video_metadata:
        print(f"   Resolution: {video_metadata.get('width')}x{video_metadata.get('height')}")
        print(f"   Duration: {video_metadata.get('duration', 0):.2f}s")
        print(f"   Codec: {video_metadata.get('codec')}")
        print(f"   File size: {video_metadata.get('file_size_mb', 0):.2f}MB")
    
    # Extract frames from video
    print(f"\n🎞️ Extracting frames for analysis...")
    frame_paths = extract_video_frames(filepath, num_frames=6)
    
    if not frame_paths:
        return {
            "error": "Failed to extract video frames. Please ensure ffmpeg is installed.",
            "technical_metadata": video_metadata
        }
    
    print(f"✅ Extracted {len(frame_paths)} frames")
    
    try:
        # Encode frames as base64
        print("\n📤 Encoding frames...")
        encoded_frames = []
        for frame_path in frame_paths:
            with open(frame_path, 'rb') as f:
                frame_data = base64.standard_b64encode(f.read()).decode('utf-8')
                encoded_frames.append(frame_data)
        
        # Build validation prompt
        prompt = f"""Analyze this promotional video by examining the provided frames.

**Campaign Requirements:**
- Campaign: "{campaign_name}"
- Brand: "{brand_name}"
- Expected Content: "{description}"
{f'- Expected Duration: {expected_duration}s' if expected_duration else ''}
{f'- Expected Resolution: {expected_resolution}' if expected_resolution else ''}
{f'- Expected Aspect Ratio: {expected_aspect_ratio}' if expected_aspect_ratio else ''}

**Video Metadata:**
{f'- Actual Resolution: {video_metadata.get("width")}x{video_metadata.get("height")}' if video_metadata.get('width') else ''}
{f'- Actual Duration: {video_metadata.get("duration", 0):.2f}s' if video_metadata.get('duration') else ''}

**Validation Criteria (Score 0-10 for each):**

1. **Visual Quality (0-10)**: 
   - Image clarity and sharpness
   - Professional color grading
   - Proper lighting and exposure
   - No artifacts or glitches

2. **Brand Presence (0-10)**:
   - Is "{brand_name}" clearly visible and prominent?
   - Is branding consistent throughout?
   - Does it match brand identity?

3. **Content Relevance (0-10)**:
   - Does the video match the description: "{description}"?
   - Are all expected visual elements present?
   - Is the storytelling coherent?

4. **Production Value (0-10)**:
   - Professional cinematography
   - Smooth camera movements
   - Engaging composition
   - Attention to detail

5. **Technical Execution (0-10)**:
   - Smooth transitions between frames
   - Consistent quality throughout
   - No technical issues visible
   - Professional post-production

6. **Marketing Effectiveness (0-10)**:
   - Attention-grabbing opening
   - Clear messaging
   - Compelling call-to-action (if applicable)
   - Suitable for target audience

**Identify Specific Issues:**
- Missing or incorrect brand elements
- Quality problems (blur, artifacts, poor lighting)
- Content mismatches with requirements
- Technical issues
- Areas for improvement

**Overall Assessment:**
- Does the video PASS validation? (true/false)
  - PASS if all scores >= 6 and no critical issues
  - FAIL if any score < 6 or critical issues found

Respond in JSON format:
{{
    "visual_quality": <score 0-10>,
    "brand_presence": <score 0-10>,
    "content_relevance": <score 0-10>,
    "production_value": <score 0-10>,
    "technical_execution": <score 0-10>,
    "marketing_effectiveness": <score 0-10>,
    "issues": ["issue 1", "issue 2", ...],
    "strengths": ["strength 1", "strength 2", ...],
    "recommendations": ["recommendation 1", "recommendation 2", ...],
    "passed": <true/false>,
    "summary": "brief overall assessment",
    "frame_analysis": {{
        "opening": "analysis of first frames",
        "middle": "analysis of middle frames",
        "closing": "analysis of final frames"
    }}
}}"""

        # Call Claude Vision API
        print("🤖 Analyzing video with Claude Vision...")
        client = Anthropic(api_key=api_key)
        
        # Build content array with all frames
        content = []
        for idx, frame_data in enumerate(encoded_frames, 1):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": frame_data,
                },
            })
            # Add caption for each frame
            timestamp = (video_metadata.get('duration', 6) / (len(encoded_frames) + 1)) * idx
            content.append({
                "type": "text",
                "text": f"Frame {idx} (at {timestamp:.1f}s):"
            })
        
        # Add main prompt at the end
        content.append({
            "type": "text",
            "text": prompt
        })
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
        )
        
        # Parse response
        response_text = response.content[0].text
        
        print("\n" + "=" * 80)
        print("CLAUDE VISION VALIDATION RESPONSE:")
        print("=" * 80)
        print(response_text)
        print("=" * 80)
        
        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            validation_result = json.loads(json_match.group(0))
        else:
            print(f"❌ Could not find JSON in response")
            return {
                "error": "Failed to parse validation response",
                "raw_response": response_text,
                "technical_metadata": video_metadata
            }
        
        # Add metadata
        validation_result["technical_metadata"] = video_metadata
        validation_result["frames_analyzed"] = len(frame_paths)
        
        # Calculate overall score
        scores = [
            validation_result.get("visual_quality", 0),
            validation_result.get("brand_presence", 0),
            validation_result.get("content_relevance", 0),
            validation_result.get("production_value", 0),
            validation_result.get("technical_execution", 0),
            validation_result.get("marketing_effectiveness", 0)
        ]
        validation_result["overall_score"] = sum(scores) / len(scores)
        
        # Create scores dict for compatibility
        validation_result["scores"] = {
            "visual_quality": validation_result.get("visual_quality", 0),
            "brand_presence": validation_result.get("brand_presence", 0),
            "content_relevance": validation_result.get("content_relevance", 0),
            "production_value": validation_result.get("production_value", 0),
            "technical_execution": validation_result.get("technical_execution", 0),
            "marketing_effectiveness": validation_result.get("marketing_effectiveness", 0),
            "overall": validation_result["overall_score"]
        }
        
        print("\n✅ VALIDATION COMPLETE")
        print(f"Overall Score: {validation_result['overall_score']:.1f}/10")
        print(f"Status: {'✅ PASSED' if validation_result.get('passed') else '❌ FAILED'}")
        print("=" * 80)
        
        return validation_result
        
    except Exception as e:
        return {
            "error": f"Validation error: {str(e)}",
            "technical_metadata": video_metadata
        }
    
    finally:
        # Cleanup temporary frame files
        for frame_path in frame_paths:
            try:
                os.remove(frame_path)
            except:
                pass
        
        # Try to remove temp directory
        if frame_paths:
            try:
                temp_dir = os.path.dirname(frame_paths[0])
                os.rmdir(temp_dir)
            except:
                pass


# Standalone validation function for external use
async def validate_video(
    filepath: str,
    campaign_name: str,
    brand_name: str,
    description: str,
    expected_duration: int = None,
    expected_resolution: str = None,
    expected_aspect_ratio: str = None
) -> str:
    """
    Validate video and return JSON string result
    Compatible with existing MCP server interface
    """
    result = await validate_video_with_claude(
        filepath,
        campaign_name,
        brand_name,
        description,
        expected_duration,
        expected_resolution,
        expected_aspect_ratio
    )
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    import asyncio
    
    # Test validation
    test_video = "outputs/video_standard_6s_text_20240101_120000.mp4"
    
    if os.path.exists(test_video):
        result = asyncio.run(validate_video(
            test_video,
            "Product Launch",
            "TechGear",
            "Camera slowly zooms in on product with dramatic lighting",
            expected_duration=6,
            expected_resolution="720p",
            expected_aspect_ratio="16:9"
        ))
        print("\n" + "=" * 80)
        print("VALIDATION RESULT:")
        print("=" * 80)
        print(result)
    else:
        print(f"Test video not found: {test_video}")
