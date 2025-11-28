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
❌ ffmpeg is not installed. Video validation requires ffmpeg.

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
    temp_dir = tempfile.mkdtemp(prefix='video_validation_')
    os.chmod(temp_dir, 0o755)
    try:
        yield temp_dir
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


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
            check=False
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
            pass
    
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
    if not check_ffmpeg_installed():
        print("❌ ffmpeg not installed")
        return []
    
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        return []
    
    if not os.access(video_path, os.R_OK):
        print(f"❌ Video not readable: {video_path}")
        return []
    
    with temp_directory() as temp_dir:
        frame_paths = []
        
        duration = get_video_duration(video_path)
        print(f"📊 Video duration: {duration:.2f}s")
        
        start_offset = 0.5
        end_offset = 0.5
        usable_duration = max(duration - start_offset - end_offset, 1.0)
        interval = usable_duration / (num_frames + 1)
        
        extracted_count = 0
        for i in range(1, num_frames + 1):
            timestamp = start_offset + (interval * i)
            
            if timestamp >= duration - 0.1:
                continue
            
            frame_path = os.path.join(temp_dir, f'frame_{i:02d}.jpg')
            
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                frame_path
            ]
            
            success, stdout, stderr = run_ffmpeg_command(cmd, timeout=30)
            
            if success and os.path.exists(frame_path) and os.path.getsize(frame_path) > 0:
                persistent_dir = tempfile.gettempdir()
                persistent_path = os.path.join(persistent_dir, f'video_frame_{os.getpid()}_{i:02d}.jpg')
                shutil.copy2(frame_path, persistent_path)
                frame_paths.append(persistent_path)
                extracted_count += 1
                print(f"  ✅ Frame {i} extracted at {timestamp:.2f}s")
            else:
                print(f"  ⚠️ Frame {i} failed")
        
        if extracted_count == 0:
            print("❌ No frames extracted")
            return []
        
        print(f"✅ Extracted {extracted_count} frames")
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
            
            frame_rate_str = stream.get('r_frame_rate', '0/1')
            try:
                num, den = map(int, frame_rate_str.split('/'))
                frame_rate = num / den if den != 0 else 0
            except:
                frame_rate = 0
            
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
        except:
            pass
    
    return {}


def encode_image_file(image_path: str, max_size_mb: int = 5) -> tuple[str, str]:
    """
    Encode image file to base64, with compression if needed
    
    Returns:
        (base64_data, mime_type)
    """
    file_size_mb = os.path.getsize(image_path) / 1024 / 1024
    
    if file_size_mb > max_size_mb:
        try:
            from PIL import Image
            import io
            
            img = Image.open(image_path)
            
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
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
            pass
    
    with open(image_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')
    
    mime_type = 'image/jpeg'
    if image_path.lower().endswith('.png'):
        mime_type = 'image/png'
    
    return (image_data, mime_type)


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
    """
    
    try:
        print("=" * 80)
        print("🎬 VIDEO VALIDATION START")
        print(f"📁 File: {filepath}")
        print(f"📂 Exists: {os.path.exists(filepath)}")
        if os.path.exists(filepath):
            print(f"📊 Size: {os.path.getsize(filepath) / 1024 / 1024:.2f} MB")
        print("=" * 80)
        
        if not os.path.exists(filepath):
            return {"error": f"Video file not found: {filepath}"}
        
        if not os.access(filepath, os.R_OK):
            return {"error": f"Video file is not readable: {filepath}"}
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"error": "ANTHROPIC_API_KEY environment variable not set"}
        
        print("🔍 Checking ffmpeg installation...")
        if not check_ffmpeg_installed():
            return {
                "error": "ffmpeg is not installed",
                "install_instructions": install_ffmpeg_instructions()
            }
        print("✅ ffmpeg found")
        
        print("📊 Extracting metadata...")
        try:
            video_metadata = get_video_metadata(filepath)
            if video_metadata:
                print(f"✅ Metadata: {video_metadata}")
            else:
                print("⚠️ No metadata extracted")
                video_metadata = {}
        except Exception as e:
            print(f"⚠️ Metadata error: {e}")
            video_metadata = {}
        
        print("🎞️ Extracting frames...")
        try:
            frame_paths = extract_video_frames(filepath, num_frames=6)
        except Exception as e:
            print(f"❌ Frame extraction error: {e}")
            return {
                "error": f"Failed to extract frames: {str(e)}",
                "technical_metadata": video_metadata
            }
        
        if not frame_paths:
            return {
                "error": "Failed to extract video frames",
                "technical_metadata": video_metadata,
                "install_instructions": install_ffmpeg_instructions()
            }
        
        print("🖼️ Encoding frames...")
        encoded_frames = []
        
        for idx, frame_path in enumerate(frame_paths, 1):
            try:
                frame_data, mime_type = encode_image_file(frame_path)
                encoded_frames.append((frame_data, mime_type))
                print(f"  ✅ Frame {idx} encoded")
            except Exception as e:
                print(f"  ⚠️ Frame {idx} encoding error: {e}")
                continue
        
        if not encoded_frames:
            return {
                "error": "Failed to encode any frames",
                "technical_metadata": video_metadata
            }
        
        print(f"✅ {len(encoded_frames)} frames ready for analysis")
        
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

1. **Visual Quality (0-10)**: Image clarity, color grading, lighting, no artifacts
2. **Brand Presence (0-10)**: Is "{brand_name}" clearly visible and prominent?
3. **Content Relevance (0-10)**: Does it match "{description}"?
4. **Production Value (0-10)**: Professional cinematography, smooth movements
5. **Technical Execution (0-10)**: Smooth transitions, consistent quality
6. **Marketing Effectiveness (0-10)**: Attention-grabbing, clear messaging

**Identify Issues:**
- Missing/incorrect brand elements
- Quality problems
- Content mismatches
- Technical issues

**Overall Assessment:**
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

        print("🤖 Calling Claude Vision API...")
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
            timestamp = (video_metadata.get('duration', 6) / (len(encoded_frames) + 1)) * idx
            content.append({
                "type": "text",
                "text": f"Frame {idx} (at {timestamp:.1f}s):"
            })
        
        content.append({
            "type": "text",
            "text": prompt
        })
        
        print("⏳ Waiting for Claude response...")
        client = Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            timeout=120.0
        )
        
        print("✅ Claude response received")
        
        response_text = response.content[0].text
        
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                return {
                    "error": "Failed to parse validation response - no JSON found",
                    "raw_response": response_text[:1000],
                    "technical_metadata": video_metadata
                }
        
        validation_result = json.loads(json_str)
        
        validation_result["technical_metadata"] = video_metadata
        validation_result["frames_analyzed"] = len(encoded_frames)
        
        scores = [
            validation_result.get("visual_quality", 0),
            validation_result.get("brand_presence", 0),
            validation_result.get("content_relevance", 0),
            validation_result.get("production_value", 0),
            validation_result.get("technical_execution", 0),
            validation_result.get("marketing_effectiveness", 0)
        ]
        validation_result["overall_score"] = sum(scores) / len(scores) if scores else 0
        
        validation_result["scores"] = {
            "visual_quality": validation_result.get("visual_quality", 0),
            "brand_presence": validation_result.get("brand_presence", 0),
            "content_relevance": validation_result.get("content_relevance", 0),
            "production_value": validation_result.get("production_value", 0),
            "technical_execution": validation_result.get("technical_execution", 0),
            "marketing_effectiveness": validation_result.get("marketing_effectiveness", 0),
            "overall": validation_result["overall_score"]
        }
        
        print("✅ Validation complete")
        print("=" * 80)
        
        return validation_result
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ VALIDATION ERROR: {e}")
        print(f"📋 Traceback:\n{error_trace}")
        return {
            "error": f"Validation error: {str(e)}",
            "traceback": error_trace,
            "technical_metadata": video_metadata if 'video_metadata' in locals() else {}
        }
    
    finally:
        print("🧹 Cleaning up temporary files...")
        if 'frame_paths' in locals():
            for frame_path in frame_paths:
                try:
                    if os.path.exists(frame_path):
                        os.remove(frame_path)
                        print(f"  🗑️ Removed {frame_path}")
                except Exception as e:
                    print(f"  ⚠️ Could not remove {frame_path}: {e}")


async def validate_video(
    filepath: str,
    campaign_name: str,
    brand_name: str,
    description: str,
    expected_duration: int = None,
    expected_resolution: str = None,
    expected_aspect_ratio: str = None
) -> str:
    """Validate video and return JSON string result"""
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
    
    test_video = "outputs/video_standard_6s_text_20240101_120000.mp4"
    
    if os.path.exists(test_video):
        print("🧪 Testing validation...")
        result = asyncio.run(validate_video(
            test_video,
            "Product Launch",
            "TechGear",
            "Camera slowly zooms in on product with dramatic lighting",
            expected_duration=6,
            expected_resolution="720p",
            expected_aspect_ratio="16:9"
        ))
        print("\n📊 RESULT:")
        print(result)
    else:
        print(f"❌ Test video not found: {test_video}")
