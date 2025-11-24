#!/usr/bin/env python3
"""
VIDEO VALIDATION MODULE
Uses Claude Vision API to analyze video quality and content
"""

import os
import json
import base64
import subprocess
import tempfile
from pathlib import Path


async def validate_video_with_claude(
    filepath: str,
    campaign_name: str,
    brand_name: str,
    description: str
) -> str:
    """
    Validate video using Claude Vision API
    Extracts key frames and analyzes them for quality, brand presence, and content relevance
    """
    
    try:
        from anthropic import Anthropic
        
        if not os.path.exists(filepath):
            return json.dumps({"error": "File not found"})
        
        # Load API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return json.dumps({"error": "ANTHROPIC_API_KEY not set"})
        
        # Extract frames from video using ffmpeg
        print(f"🎬 Extracting frames from video for analysis...")
        frames = await extract_video_frames(filepath, num_frames=4)
        
        if not frames:
            return json.dumps({"error": "Failed to extract video frames"})
        
        print(f"✅ Extracted {len(frames)} frames for analysis")
        
        # Build validation prompt
        prompt = f"""Analyze this promotional video and validate it against the campaign requirements.

**Campaign Details:**
- Brand: "{brand_name}"
- Campaign: "{campaign_name}"
- Expected Content: "{description}"

**Validation Criteria:**
1. **Visual Quality (0-10)**: Assess overall image quality, resolution, clarity, lighting, and professional appearance
2. **Brand Presence (0-10)**: Is the brand "{brand_name}" visible and prominent throughout the video?
3. **Content Relevance (0-10)**: Does the video content match the description "{description}"?
4. **Motion Quality (0-10)**: Evaluate smoothness of motion, camera movements, and transitions between frames
5. **Production Value (0-10)**: Overall professional quality, composition, color grading, and attention to detail
6. **Storytelling (0-10)**: Does the video tell a coherent story? Are the frames visually connected?

**Identify specific issues:**
- Brand visibility problems
- Content mismatch with description
- Poor visual quality or motion artifacts
- Abrupt or jarring transitions
- Inconsistent visual style
- Technical issues (blur, pixelation, etc.)

**IMPORTANT**: Analyze ALL frames as a sequence. Look for:
- Visual continuity between frames
- Logical progression of action
- Consistency in lighting, style, and composition
- Smooth visual flow

Respond in JSON format:
{{
    "visual_quality": <score 0-10>,
    "brand_presence": <score 0-10>,
    "content_relevance": <score 0-10>,
    "motion_quality": <score 0-10>,
    "production_value": <score 0-10>,
    "storytelling": <score 0-10>,
    "overall_score": <average of all scores>,
    "issues": ["issue 1", "issue 2", ...],
    "strengths": ["strength 1", "strength 2", ...],
    "passed": <true if overall_score >= 7.0, false otherwise>,
    "summary": "brief overall assessment with specific feedback"
}}"""

        # Call Claude Vision with all frames
        client = Anthropic(api_key=api_key)
        
        # Build message content with all frames
        message_content = []
        
        for idx, frame_data in enumerate(frames, 1):
            message_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": frame_data,
                },
            })
            message_content.append({
                "type": "text",
                "text": f"Frame {idx}/{len(frames)}"
            })
        
        # Add the main prompt at the end
        message_content.append({
            "type": "text",
            "text": prompt
        })
        
        print("🤖 Sending frames to Claude for analysis...")
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": message_content
                }
            ],
        )
        
        # Parse response
        response_text = response.content[0].text
        
        print("=" * 60)
        print("CLAUDE VISION VIDEO VALIDATION RESPONSE:")
        print(response_text)
        print("=" * 60)
        
        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            validation_result = json.loads(json_match.group(0))
        else:
            print(f"ERROR: Could not find JSON in response")
            return json.dumps({
                "error": "Failed to parse validation response",
                "raw_response": response_text
            })
        
        # Add metadata
        file_size = os.path.getsize(filepath) / 1024 / 1024
        validation_result["file_size_mb"] = round(file_size, 2)
        validation_result["frames_analyzed"] = len(frames)
        
        # Calculate scores dict for compatibility
        validation_result["scores"] = {
            "visual_quality": validation_result.get("visual_quality", 0),
            "brand_presence": validation_result.get("brand_presence", 0),
            "content_relevance": validation_result.get("content_relevance", 0),
            "motion_quality": validation_result.get("motion_quality", 0),
            "production_value": validation_result.get("production_value", 0),
            "storytelling": validation_result.get("storytelling", 0),
            "overall_score": validation_result.get("overall_score", 0)
        }
        
        print("FINAL VIDEO VALIDATION RESULT:")
        print(json.dumps(validation_result, indent=2))
        
        return json.dumps(validation_result)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


async def extract_video_frames(video_path: str, num_frames: int = 4) -> list:
    """
    Extract evenly-spaced frames from video using ffmpeg
    Returns list of base64-encoded JPEG frames
    """
    
    frames = []
    temp_dir = None
    
    try:
        # Check if ffmpeg is available
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True,
                timeout=5
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("⚠️  ffmpeg not found. Install it with: sudo apt-get install ffmpeg")
            return []
        
        # Create temp directory for frames
        temp_dir = tempfile.mkdtemp()
        
        # Get video duration first
        duration_cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        result = subprocess.run(
            duration_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"⚠️  Could not get video duration")
            return []
        
        try:
            duration = float(result.stdout.strip())
        except ValueError:
            print(f"⚠️  Invalid duration value")
            return []
        
        # Extract frames at evenly-spaced intervals
        for i in range(num_frames):
            # Calculate timestamp for this frame
            timestamp = (duration / (num_frames + 1)) * (i + 1)
            
            output_path = os.path.join(temp_dir, f"frame_{i:03d}.jpg")
            
            # Extract frame at specific timestamp
            cmd = [
                "ffmpeg",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",  # High quality JPEG
                "-vf", "scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease",
                "-y",
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                # Read and encode frame
                with open(output_path, 'rb') as f:
                    frame_bytes = f.read()
                
                # Check file size (Claude has 5MB limit per image)
                if len(frame_bytes) > 5 * 1024 * 1024:
                    print(f"⚠️  Frame {i} too large, compressing...")
                    # Re-extract with lower quality
                    cmd[-3] = "5"  # Lower quality
                    subprocess.run(cmd, capture_output=True, timeout=30)
                    with open(output_path, 'rb') as f:
                        frame_bytes = f.read()
                
                frame_base64 = base64.standard_b64encode(frame_bytes).decode("utf-8")
                frames.append(frame_base64)
                
                print(f"  ✅ Extracted frame {i+1}/{num_frames} at {timestamp:.2f}s")
            else:
                print(f"  ⚠️  Failed to extract frame {i}")
        
        return frames
        
    except Exception as e:
        print(f"❌ Error extracting frames: {e}")
        return []
    
    finally:
        # Cleanup temp directory
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
