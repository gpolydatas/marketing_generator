#!/usr/bin/env python3
"""
VIDEO VALIDATION MODULE - FIXED FOR EC2 DEPLOYMENT
Uses Claude Vision API to analyze video quality, content, and adherence to campaign requirements

FIXES:
- Better ffmpeg dependency checking with installation hints
- Improved subprocess error handling and timeouts
- Robust temporary file cleanup with context managers
- Memory-efficient frame processing
- Better error messages for debugging
- Proper file permissions handling
"""

import os
import json
import base64
import subprocess
import tempfile
import shutil
from pathlib import Path
from contextlib import contextmanager
from anthropic import Anthropic


def check_ffmpeg_installed() -> bool:
    """Check if ffmpeg and ffprobe are installed"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, timeout=5, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def install_ffmpeg_instructions():
    """Return installation instructions for ffmpeg on Ubuntu"""
    return """
âŒ ffmpeg is not installed. Video validation requires ffmpeg.

To install on Ubuntu 24:
    sudo apt-get update
    sudo apt-get install -y ffmpeg

To verify installation:
    ffmpeg -version
    ffprobe -version
"""


@contextmanager
def temp_directory():
    """Context manager for safe temporary directory handling"""
    temp_dir = None
    temp_dir = tempfile.mkdtemp(prefix='video_validation_')
    # Ensure directory has proper permissions
    os.chmod(temp_dir, 0o755)
    yield temp_dir
def run_ffmpeg_command(cmd: list, timeout: int = 30) -> tuple[bool, str, str]:
    """
    Run ffmpeg/ffprobe command with proper error handling
    
    Returns:
        (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False  # Don't raise on non-zero exit
        )
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "", f"Command timed out after {timeout}s")
    except Exception as e:
        return (False, "", str(e))


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    
    success, stdout, stderr = run_ffmpeg_command(cmd, timeout=10)
    
    if success and stdout.strip():
        try:
            return float(stdout.strip())
        except ValueError:
            
    
    # Fallback: try to get from stream instead
    cmd_alt = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    
    success, stdout, stderr = run_ffmpeg_command(cmd_alt, timeout=10)
    
    if success and stdout.strip():
        try:
            return float(stdout.strip())
        except ValueError:
            pass
    
    
    return 6.0


def extract_video_frames(video_path: str, num_frames: int = 6) -> list[str]:
    """
    Extract frames from video for analysis
    
    Args:
        video_path: Path to video file
        num_frames: Number of frames to extract (default: 6)
    
    Returns:
        List of temporary frame file paths
    """
    # Check ffmpeg first
    if not check_ffmpeg_installed():
        
        return []
    
    # Verify video file exists
    if not os.path.exists(video_path):
        
        return []
    
    # Check file is readable
    if not os.access(video_path, os.R_OK):
        
        return []
    
    with temp_directory() as temp_dir:
        frame_paths = []
        
        # Get video duration
        duration = get_video_duration(video_path)
        
        # Calculate frame intervals (avoid first and last 0.5s)
        start_offset = 0.5
        end_offset = 0.5
        usable_duration = max(duration - start_offset - end_offset, 1.0)
        interval = usable_duration / (num_frames + 1)
        
        # Extract frames at calculated intervals
        extracted_count = 0
        for i in range(1, num_frames + 1):
            timestamp = start_offset + (interval * i)
            
            # Don't exceed video duration
            if timestamp >= duration - 0.1:
                
                continue
            
            frame_path = os.path.join(temp_dir, 'frame_{:02d}.jpg'.format(i))
            
            # Extract frame with ffmpeg
            timestamp_str = str(timestamp)
            cmd = [
                'ffmpeg',
                '-ss', timestamp_str,
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                frame_path
            ]
            
            success, stdout, stderr = run_ffmpeg_command(cmd, timeout=30)
            
            if success and os.path.exists(frame_path) and os.path.getsize(frame_path) > 0:
                # Copy to persistent location before temp_dir cleanup
                persistent_dir = tempfile.gettempdir()
                persistent_path = os.path.join(persistent_dir, 'video_frame_{}_{:02d}.jpg'.format(os.getpid(), i))
                shutil.copy2(frame_path, persistent_path)
                frame_paths.append(persistent_path)
                extracted_count += 1
                
            else:
                
                if stderr:
                    
        
        if extracted_count == 0:
            return []
        
        return frame_paths


def get_video_metadata(video_path: str) -> dict:
    """Extract technical metadata from video file"""
    if not check_ffmpeg_installed():
        return {}
    
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,duration,bit_rate,codec_name,r_frame_rate',
        '-show_entries', 'format=size,duration',
        '-of', 'json',
        video_path
    ]
    
    success, stdout, stderr = run_ffmpeg_command(cmd, timeout=10)
    
    if success and stdout:
        try:
            data = json.loads(stdout)
            stream = data.get('streams', [{}])[0]
            format_info = data.get('format', {})
            
            # Parse frame rate
            frame_rate_str = stream.get('r_frame_rate', '0/1')
            try:
                num, den = map(int, frame_rate_str.split('/'))
                frame_rate = num / den if den != 0 else 0
            except:
                frame_rate = 0
            
            # Get duration (try format first, then stream)
            duration = format_info.get('duration')
            if duration is None:
                duration = stream.get('duration')
            try:
                duration = float(duration) if duration else 0
            except:
                duration = 0
            
            return {
                'width': stream.get('width'),
                'height': stream.get('height'),
                'duration': duration,
                'codec': stream.get('codec_name'),
                'frame_rate': f'{frame_rate:.2f} fps' if frame_rate else 'unknown',
                'file_size_mb': int(format_info.get('size', 0)) / 1024 / 1024
            }
        except json.JSONDecodeError as e:
        except Exception as e:
    else:
    
    return {}


def encode_image_file(image_path: str, max_size_mb: int = 5) -> tuple[str, str]:
    """
    Encode image file to base64, with compression if needed
    
    Returns:
        (base64_data, mime_type)
    """
    try:
        # Check file size
        file_size_mb = os.path.getsize(image_path) / 1024 / 1024
        
        if file_size_mb > max_size_mb:
            # Compress using PIL if available
            try:
                from PIL import Image
                import io
                
                img = Image.open(image_path)
                
                # Convert RGBA to RGB if needed
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                # Compress to target size
                buffer = io.BytesIO()
                quality = 85
                
                while quality > 20:
                    buffer.seek(0)
                    buffer.truncate()
                    img.save(buffer, format='JPEG', quality=quality, optimize=True)
                    compressed_size = buffer.tell() / 1024 / 1024
                    
                    if compressed_size < max_size_mb:
                        break
                    
                    quality -= 10
                
                buffer.seek(0)
                image_data = base64.standard_b64encode(buffer.read()).decode('utf-8')
                
                return (image_data, 'image/jpeg')
                
            except ImportError:
        
        # Read and encode normally
        with open(image_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')
        
        # Determine MIME type
        mime_type = 'image/jpeg'
        if image_path.lower().endswith('.png'):
            mime_type = 'image/png'
        
        return (image_data, mime_type)
        
    except Exception as e:
        raise


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
    
    # Check if readable
    if not os.access(filepath, os.R_OK):
        return {"error": f"Video file is not readable: {filepath}"}
    
    # Load API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY environment variable not set"}
    
    # Check ffmpeg
    if not check_ffmpeg_installed():
        return {
            "error": "ffmpeg is not installed",
            "install_instructions": install_ffmpeg_instructions()
        }
    
    
    
    
    
    # Extract video metadata
    video_metadata = get_video_metadata(filepath)
    
    if video_metadata:
        
        
        
        
        
    else:
    
    # Extract frames from video
    frame_paths = extract_video_frames(filepath, num_frames=6)
    
    if not frame_paths:
        return {
            "error": "Failed to extract video frames. Please ensure ffmpeg is installed and the video is valid.",
            "technical_metadata": video_metadata,
            "install_instructions": install_ffmpeg_instructions()
        }
    
    
    try:
        # Encode frames as base64
        encoded_frames = []
        
        for idx, frame_path in enumerate(frame_paths, 1):
            try:
                
                frame_data, mime_type = encode_image_file(frame_path)
                encoded_frames.append((frame_data, mime_type))
            except Exception as e:
                continue
        
        if not encoded_frames:
            return {
                "error": "Failed to encode any frames",
                "technical_metadata": video_metadata
            }
        
        
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
{f'- Codec: {video_metadata.get("codec")}' if video_metadata.get('codec') else ''}

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
   - Compelling visuals
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
        client = Anthropic(api_key=api_key)
        
        # Build content array with all frames
        content = []
        for idx, (frame_data, mime_type) in enumerate(encoded_frames, 1):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
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
        
        
        
        
        
        
        
        # Extract JSON from response (handle markdown code blocks)
        import re
        
        # Try to find JSON in code block first
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code block
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                return {
                    "error": "Failed to parse validation response - no JSON found",
                    "raw_response": response_text[:1000],
                    "technical_metadata": video_metadata
                }
        
        try:
            validation_result = json.loads(json_str)
        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse validation JSON: {str(e)}",
                "raw_response": response_text[:1000],
                "technical_metadata": video_metadata
            }
        
        # Add metadata
        validation_result["technical_metadata"] = video_metadata
        validation_result["frames_analyzed"] = len(encoded_frames)
        
        # Calculate overall score
        scores = [
            validation_result.get("visual_quality", 0),
            validation_result.get("brand_presence", 0),
            validation_result.get("content_relevance", 0),
            validation_result.get("production_value", 0),
            validation_result.get("technical_execution", 0),
            validation_result.get("marketing_effectiveness", 0)
        ]
        validation_result["overall_score"] = sum(scores) / len(scores) if scores else 0
        
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
        
        
        
        
        return validation_result
        
    except Exception as e:
        import traceback
        
        return {
            "error": f"Validation error: {str(e)}",
            "technical_metadata": video_metadata
        }
    
    finally:
        # Cleanup temporary frame files
        for frame_path in frame_paths:
            try:
                if os.path.exists(frame_path):
                    os.remove(frame_path)
            except Exception as e:


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
        
        
        
        
    else:
        
        
