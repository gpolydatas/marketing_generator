# 🎨 Marketing Content Generator

> AI-powered marketing content creation with interactive chat, banner generation (DALL-E 3), and video generation (Google Veo 3.1)

[![Python 3.10+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![uv](https://img.shields.io/badge/uv-package%20manager-blue)](https://github.com/astral-sh/uv)

---

## 📑 Table of Contents

1. [Features](#-features)
2. [Quick Start](#-quick-start)
3. [Architecture](#-architecture)
4. [Setup Instructions](#-setup-instructions)
5. [Usage & Workflows](#-usage--workflows)
6. [Configuration](#-configuration)
7. [Project Structure](#-project-structure)
8. [API Costs](#-api-costs)
9. [Development](#-development)
10. [Troubleshooting](#-troubleshooting)
11. [4-Week POC Timeline](#-4-week-poc-timeline)
12. [Contributing](#-contributing)
13. [License](#-license)

---

## 🚀 Features

### 💬 Interactive AI Agent Chat
- **Natural Language Interface**: Conversational interaction for content generation
- **Context Memory**: Maintains last 3 message exchanges for coherent conversations
- **Intelligent Routing**: Automatically detects intent (banner/video/image-to-video)
- **Parameter Extraction**: Extracts campaign details, brand info, specs from conversation

### 🖼️ Banner Generation
- **Engine**: OpenAI DALL-E 3 (HD quality)
- **Sizes**: 
  - Social media (1200×628)
  - Leaderboard (728×90)
  - Square (1024×1024)
- **Speed**: 10-30 seconds per banner
- **Quality Assurance**: Automatic validation using Claude Vision
- **Auto-Retry**: Regenerates up to 3 times if quality validation fails
- **Validation Criteria**:
  - Brand visibility (1-10)
  - Message clarity (1-10)
  - CTA effectiveness (1-10)
  - Visual appeal (1-10)
  - Overall quality (1-10)

### 🎬 Video Generation
- **Engine**: Google Veo 3.1
- **Modes**:
  - Text-to-video: Describe your video concept
  - Image-to-video: Animate existing banners
- **Durations**: Short (4s), Standard (6s), Extended (8s)
- **Quality**: 720p or 1080p
- **Aspect Ratios**: 16:9 (landscape) or 9:16 (portrait)
- **Speed**: 1-3 minutes per video
- **Native Audio**: Videos include generated audio

### 📊 Additional Features
- **Gallery View**: Browse all generated content with filtering
- **Manual Forms**: Alternative to chat for structured input
- **Download**: Direct download of all generated assets
- **Metadata Tracking**: JSON files with generation parameters
- **Session Persistence**: Conversation history maintained during session

---

## ⚡ Quick Start

### Prerequisites
- **Python**: 3.8 or higher
- **uv**: Fast Python package installer
- **API Keys**: OpenAI, Anthropic, Google

### Installation (5 minutes)

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone repository
git clone https://github.com/gpolydatas/marketing_generator.git
cd marketing_generator

# 3. Install dependencies
uv pip install -r requirements.txt

# 4. Configure API keys
cp fastagent.secrets.yaml.template fastagent.secrets.yaml
# Edit fastagent.secrets.yaml with your actual API keys

# 5. Run application
uv run streamlit run app_working.py
```

**Open in browser**: http://localhost:8501

---

## 🏗️ Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────┐
│              USER INTERFACE (Streamlit)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Chat         │  │ Manual       │  │ Gallery      │ │
│  │ Interface    │  │ Forms        │  │ View         │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│         ORCHESTRATION LAYER (FastAgent)                 │
│  ┌───────────────────────────────────────────────────┐ │
│  │      Marketing Orchestrator Agent                 │ │
│  │  • Natural language understanding                 │ │
│  │  • Context management (6 messages)                │ │
│  │  • Intent detection & routing                     │ │
│  │  • Parameter extraction                           │ │
│  └───────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌──────────────────────┐    ┌──────────────────────┐
│  BANNER MCP SERVER   │    │  VIDEO MCP SERVER    │
│                      │    │                      │
│  generate_banner()   │    │  generate_video()    │
│  validate_banner()   │    │  validate_video()    │
│                      │    │                      │
│  ┌───────────────┐  │    │  ┌───────────────┐  │
│  │  DALL-E 3     │  │    │  │  Veo 3.1      │  │
│  │  (OpenAI)     │  │    │  │  (Google)     │  │
│  └───────────────┘  │    │  └───────────────┘  │
│                      │    │                      │
│  ┌───────────────┐  │    │  ┌───────────────┐  │
│  │  Claude       │  │    │  │  Claude       │  │
│  │  (Validation) │  │    │  │  (Validation) │  │
│  └───────────────┘  │    │  └───────────────┘  │
└──────────────────────┘    └──────────────────────┘
              │                         │
              └──────────┬──────────────┘
                         ▼
              ┌──────────────────────┐
              │   STORAGE LAYER      │
              │  (Local Filesystem)  │
              │                      │
              │  • outputs/*.png     │
              │  • outputs/*.mp4     │
              │  • outputs/*.json    │
              └──────────────────────┘
```

### Component Architecture

#### 1. Frontend Layer (`app_working.py`)
- **Streamlit Application**: Web interface
- **Components**:
  - Chat interface with conversation history
  - Manual forms for banner/video/image-to-video
  - Gallery with filtering (banners/videos)
  - Preview and download functionality
- **Session State**: Manages conversation context

#### 2. Orchestration Layer (`agent.py`)
- **FastAgent Framework**: MCP-based agent orchestration
- **Responsibilities**:
  - Parse natural language requests
  - Maintain conversation context (last 6 messages)
  - Detect intent (banner/video/image-to-video)
  - Extract parameters (campaign, brand, specs)
  - Route to appropriate MCP server
  - Handle errors and retries

#### 3. MCP Server Layer

**Banner MCP Server** (`banner_mcp_server.py`):
- **Tools**:
  - `generate_banner`: Creates banner with DALL-E 3
  - `validate_banner`: Quality checks with Claude Vision
- **Process**:
  1. Build enhanced prompt from parameters
  2. Call DALL-E 3 API
  3. Download and save image
  4. Validate with Claude
  5. Regenerate if validation fails (up to 3 attempts)

**Video MCP Server** (`video_mcp_server.py`):
- **Tools**:
  - `generate_video`: Creates video with Veo 3.1
  - `validate_video`: Manual review
- **Process**:
  1. Build prompt (text-to-video or image-to-video)
  2. Call Veo API
  3. Poll for completion (1-3 minutes)
  4. Download and save video
  5. Save metadata

#### 4. External AI Services

**OpenAI DALL-E 3**:
- Model: `dall-e-3`
- Quality: HD
- Sizes: 1024×1024, 1792×1024, 1024×1792
- Cost: ~$0.08 per image

**Google Veo 3.1**:
- Durations: 4s, 6s, 8s
- Resolutions: 720p, 1080p
- Aspect ratios: 16:9, 9:16
- Cost: ~$0.50 per video

**Anthropic Claude**:
- Model: `claude-sonnet-4-20250514`
- Use: Validation and orchestration
- Cost: ~$0.003 per validation

#### 5. Storage Layer
- **Location**: `outputs/` directory
- **File Naming**:
  - Banners: `banner_{type}_{size}_{timestamp}.png`
  - Videos: `video_{duration}_{mode}_{timestamp}.mp4`
  - Metadata: Same name with `.json` extension

---

## 📋 Setup Instructions

### Step 1: Install uv Package Manager

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Verify installation:**
```bash
uv --version
```

### Step 2: Clone Repository

```bash
git clone https://github.com/gpolydatas/marketing_generator.git
cd marketing_generator
```

### Step 3: Install Dependencies

**Production:**
```bash
uv pip install -r requirements.txt
```

**Development (includes testing/linting tools):**
```bash
uv pip install -r requirements-dev.txt
```

### Step 4: Configure API Keys

**Copy template:**
```bash
cp fastagent.secrets.yaml.template fastagent.secrets.yaml
```

**Edit `fastagent.secrets.yaml`:**

```yaml
# FastAgent Secrets Configuration
openai:
    api_key: sk-proj-YOUR_OPENAI_KEY_HERE

anthropic:
    api_key: sk-ant-YOUR_ANTHROPIC_KEY_HERE

google:
    api_key: YOUR_GOOGLE_KEY_HERE

mcp:
    servers:
        banner_tools:
            env:
                OPENAI_API_KEY: sk-proj-YOUR_OPENAI_KEY_HERE
                ANTHROPIC_API_KEY: sk-ant-YOUR_ANTHROPIC_KEY_HERE
        video_tools:
            env:
                GOOGLE_API_KEY: YOUR_GOOGLE_KEY_HERE
                ANTHROPIC_API_KEY: sk-ant-YOUR_ANTHROPIC_KEY_HERE
```

**Get API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **Google**: https://console.cloud.google.com/

### Step 5: Create Outputs Directory

```bash
mkdir -p outputs
```

### Step 6: Run Application

```bash
uv run streamlit run app_working.py
```

**Application will open at**: http://localhost:8501

### Step 7: Test Installation

**Quick test in chat interface:**
```
You: Create a test banner for TechCo
```

Wait 10-30 seconds - you should see a banner generated!

---

## 🎯 Usage & Workflows

### Workflow 1: Banner Creation via Chat

```
┌──────────────────────────────────────────────────────────────┐
│ 1. USER TYPES IN CHAT                                        │
│    "Create a Black Friday banner for Nike with 70% off"      │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. AGENT ANALYZES REQUEST                                    │
│    • Intent: BANNER                                          │
│    • Parameters:                                             │
│      - Campaign: "Black Friday"                              │
│      - Brand: "Nike"                                         │
│      - Type: "social"                                        │
│      - Message: "70% off"                                    │
│      - CTA: "Shop Now"                                       │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. GENERATE BANNER                                           │
│    • Call banner_mcp_server.generate_banner()                │
│    • DALL-E 3 creates image (10-30 seconds)                  │
│    • Save to outputs/banner_social_1792x1024_[timestamp].png │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. VALIDATE BANNER                                           │
│    • Call banner_mcp_server.validate_banner()                │
│    • Claude Vision scores:                                   │
│      - Brand visibility: 9/10                                │
│      - Message clarity: 8/10                                 │
│      - CTA effectiveness: 9/10                               │
│      - Visual appeal: 8/10                                   │
│      - Overall quality: 8.5/10                               │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. CHECK VALIDATION                                          │
│    All scores ≥ 7? YES → Continue                            │
│    Any score < 7? NO → Regenerate (up to 3 times)           │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. DISPLAY RESULTS                                           │
│    • Show success message                                    │
│    • Display validation scores                               │
│    • Preview banner image                                    │
│    • Add to gallery                                          │
└──────────────────────────────────────────────────────────────┘
```

**Example Conversation:**
```
You: Create a Black Friday banner for Nike
🤖: I'll create a Black Friday sale banner for Nike...
    [Generates banner in 15 seconds]
    ✅ Banner created! Validation scores:
    • Brand visibility: 9/10
    • Message clarity: 8/10
    • CTA effectiveness: 9/10

You: Make the text bigger
🤖: I'll regenerate with larger text...
    [Generates improved banner]
    ✅ Updated banner created!
```

### Workflow 2: Video Creation via Chat

```
┌──────────────────────────────────────────────────────────────┐
│ 1. USER TYPES IN CHAT                                        │
│    "Make a 6-second video showcasing headphones"             │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. AGENT ANALYZES REQUEST                                    │
│    • Intent: VIDEO (text-to-video)                           │
│    • Parameters:                                             │
│      - Duration: "standard" (6s)                             │
│      - Description: "showcasing headphones"                  │
│      - Resolution: "720p"                                    │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. GENERATE VIDEO                                            │
│    • Call video_mcp_server.generate_video()                  │
│    • Veo 3.1 generates video (1-3 minutes)                   │
│    • Poll for completion every 10 seconds                    │
│    • Download completed video                                │
│    • Save to outputs/video_standard_6s_[timestamp].mp4       │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. DISPLAY RESULTS                                           │
│    • Show success message                                    │
│    • Display video preview                                   │
│    • Provide download link                                   │
│    • Add to gallery                                          │
└──────────────────────────────────────────────────────────────┘
```

### Workflow 3: Image-to-Video (Animate Banner)

```
┌──────────────────────────────────────────────────────────────┐
│ 1. FIRST: CREATE BANNER                                      │
│    You: "Create a banner for Summer Sale"                    │
│    🤖: [Creates banner_social_1792x1024_20251026.png]        │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. THEN: ANIMATE IT                                          │
│    You: "Now animate it with a zoom effect"                  │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. AGENT UNDERSTANDS CONTEXT                                 │
│    • Intent: IMAGE-TO-VIDEO                                  │
│    • Extract filename from conversation history:             │
│      "banner_social_1792x1024_20251026.png"                  │
│    • Motion: "zoom effect"                                   │
│    • Duration: "standard" (6s default)                       │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. GENERATE VIDEO FROM IMAGE                                 │
│    • Call video_mcp_server.generate_video()                  │
│    • Include input_image_path parameter                      │
│    • Veo 3.1 animates the banner (1-3 minutes)               │
│    • Save to outputs/video_6s_image_[timestamp].mp4          │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. DISPLAY RESULTS                                           │
│    • Show animated video                                     │
│    • Link back to source banner                              │
│    • Add to gallery                                          │
└──────────────────────────────────────────────────────────────┘
```

**Example Multi-turn Conversation:**
```
You: Create a Summer Sale banner for BeachWear
🤖: [Generates banner]
    ✅ Banner created!

You: Now make it a video with a slow zoom
🤖: I'll animate the banner you just created...
    [Animates banner into video]
    ✅ Video created from your banner!

You: Can you make it 8 seconds instead?
🤖: I'll regenerate as an 8-second video...
    [Creates longer version]
    ✅ Extended video ready!
```

### Workflow 4: Manual Forms (Alternative to Chat)

**For users who prefer structured input:**

1. **Navigate to "Manual Forms" section**
2. **Select form type**:
   - Create Banner
   - Create Video
   - Animate Banner (Image-to-Video)
3. **Fill out form fields**:
   - Campaign name
   - Brand name
   - Type/duration/specifications
   - Message/description
4. **Click "Generate"**
5. **Preview and download result**

---

## ⚙️ Configuration

### MCP Server Configuration

**File**: `fastagent.config.yaml`

```yaml
mcp:
  servers:
    banner_tools:
      command: "python"
      args: ["banner_mcp_server.py"]
      env:
        OPENAI_API_KEY: "${OPENAI_API_KEY}"
        ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
    
    video_tools:
      command: "python"
      args: ["video_mcp_server.py"]
      env:
        GOOGLE_API_KEY: "${GOOGLE_API_KEY}"
        ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
```

### Environment Variables (Alternative to secrets file)

```bash
# Set environment variables
export OPENAI_API_KEY="sk-proj-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."

# Run app (will use env vars)
uv run streamlit run app_working.py
```

### Customization Options

**Banner Settings** (in `banner_mcp_server.py`):
- Modify prompt templates
- Adjust validation thresholds
- Change retry logic

**Video Settings** (in `video_mcp_server.py`):
- Adjust polling intervals
- Modify timeout durations
- Change default resolutions

**Agent Behavior** (in `agent.py`):
- Adjust context window size
- Modify intent detection logic
- Change parameter extraction rules

---

## 📁 Project Structure

```
marketing_generator/
├── app_working.py                  # Main Streamlit application
│   ├── Chat interface
│   ├── Manual forms
│   ├── Gallery view
│   └── Session state management
│
├── agent.py                        # FastAgent orchestrator
│   ├── Natural language processing
│   ├── Intent detection
│   ├── Parameter extraction
│   └── Tool routing
│
├── banner_mcp_server.py           # Banner generation MCP server
│   ├── generate_banner() tool
│   ├── validate_banner() tool
│   └── DALL-E 3 integration
│
├── video_mcp_server.py            # Video generation MCP server
│   ├── generate_video() tool
│   ├── validate_video() tool
│   └── Veo 3.1 integration
│
├── fastagent.config.yaml          # MCP server configuration
├── fastagent.secrets.yaml         # API keys (gitignored)
├── fastagent.secrets.yaml.template # API keys template
│
├── requirements.txt               # Python dependencies
├── requirements-dev.txt           # Development dependencies
│
├── .gitignore                     # Git ignore rules
├── LICENSE                        # MIT License
├── README.md                      # This file
│
└── outputs/                       # Generated content (auto-created)
    ├── .gitkeep                   # Keeps directory in git
    ├── banner_*.png               # Generated banners
    ├── banner_*.json              # Banner metadata
    ├── video_*.mp4                # Generated videos
    └── video_*.json               # Video metadata
```

### File Metadata Format

**Banner Metadata** (`banner_*.json`):
```json
{
  "campaign": "Black Friday",
  "brand": "Nike",
  "type": "social",
  "message": "70% off",
  "cta": "Shop Now",
  "filename": "banner_social_1792x1024_20251026_094107.png",
  "size": "1792x1024",
  "file_size_mb": 1.2,
  "timestamp": "2025-10-26T09:41:07",
  "validation": {
    "passed": true,
    "brand_visibility": 9,
    "message_clarity": 8,
    "cta_effectiveness": 9,
    "visual_appeal": 8,
    "overall_quality": 8.5
  }
}
```

**Video Metadata** (`video_*.json`):
```json
{
  "campaign": "Product Launch",
  "brand": "TechCo",
  "duration": "standard",
  "description": "Showcasing new headphones",
  "resolution": "720p",
  "aspect_ratio": "16:9",
  "filename": "video_standard_6s_20251026_100050.mp4",
  "file_size_mb": 5.8,
  "timestamp": "2025-10-26T10:00:50",
  "input_image": "banner_social_1792x1024_20251026_094107.png"
}
```

---

## 💰 API Costs

### Per Asset Pricing

| Asset Type | Service | Cost | Time |
|------------|---------|------|------|
| Banner | DALL-E 3 (HD) | $0.08 | 10-30s |
| Validation | Claude Vision | $0.003 | 3-5s |
| Video (4s) | Veo 3.1 | $0.30 | 1-2 min |
| Video (6s) | Veo 3.1 | $0.50 | 1-3 min |
| Video (8s) | Veo 3.1 | $0.70 | 2-3 min |

### Monthly Estimates

**Small usage** (100 banners + 50 videos):
- Banners: 100 × $0.08 = $8
- Videos: 50 × $0.50 = $25
- Validation: 150 × $0.003 = $0.45
- **Total**: ~$33/month

**Medium usage** (500 banners + 250 videos):
- Banners: 500 × $0.08 = $40
- Videos: 250 × $0.50 = $125
- Validation: 750 × $0.003 = $2.25
- **Total**: ~$167/month

**High usage** (1,000 banners + 500 videos):
- Banners: 1,000 × $0.08 = $80
- Videos: 500 × $0.50 = $250
- Validation: 1,500 × $0.003 = $4.50
- **Total**: ~$335/month

### Cost Optimization Tips

1. **Use caching**: Cache similar prompts
2. **Batch similar requests**: Generate related content together
3. **Use 720p for videos**: Faster and cheaper than 1080p
4. **Set API spending limits**: Monitor usage in dashboards
5. **Use shorter videos**: 4s videos cost 40% less than 8s

---

## 🛠️ Development

### Running Tests

```bash
# Install dev dependencies
uv pip install -r requirements-dev.txt

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test
uv run pytest tests/test_banner.py
```

### Code Quality

```bash
# Format code
uv run black .

# Sort imports
uv run isort .

# Lint
uv run flake8 .

# Type checking
uv run mypy .
```

### Local Development

```bash
# Run with custom port
uv run streamlit run app_working.py --server.port 8502

# Run with debug logging
uv run streamlit run app_working.py --logger.level=debug

# Run MCP servers individually
uv run python banner_mcp_server.py
uv run python video_mcp_server.py
```

---

## 🐛 Troubleshooting

### Installation Issues

**"uv: command not found"**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell
source ~/.bashrc  # or restart terminal
```

**"Module not found"**
```bash
# Reinstall dependencies
uv pip install -r requirements.txt --force-reinstall
```

### Configuration Issues

**"API key not found"**
- Verify `fastagent.secrets.yaml` exists in project root
- Check file format (4 spaces for indentation, no tabs)
- Ensure keys don't have extra spaces or quotes

**"Invalid API key"**
- Verify key copied correctly from provider
- Check key hasn't expired
- Ensure key has correct permissions

### Runtime Issues

**"Agent 'marketing_orchestrator' not found"**
- Check `agent.py` is in same directory as `app_working.py`
- Verify FastAgent is installed: `uv pip list | grep fast-agent`

**"DALL-E rate limit exceeded"**
- Wait 60 seconds and retry
- Check OpenAI usage dashboard
- Consider upgrading plan

**"Video generation timeout"**
- Normal for first videos (cold start)
- Videos take 1-3 minutes to generate
- Check Google API quota

**"Validation always fails"**
- DALL-E text accuracy is ~80%
- System auto-regenerates up to 3 times
- Try simpler prompts

**"Port already in use"**
```bash
# Use different port
uv run streamlit run app_working.py --server.port 8502
```

### Performance Issues

**"App is slow"**
- Check internet connection
- Verify API services are operational
- Monitor system resources

**"Out of memory"**
- Close unused applications
- Reduce Streamlit cache size
- Restart application

---

## 📅 4-Week POC Timeline

### Overview

Complete proof-of-concept delivery in 4 weeks with 4 major milestones.

```
Week 1: Foundation ─────────► M1: Banner Generation Complete
Week 2: Video & Agent ──────► M2: Video & Agent Ready
Week 3: User Interface ─────► M3: Full UI Complete
Week 4: Testing & Launch ───► M4: POC Demo
```

### Week 1: Foundation & Banner Generation

**Goals**:
- Project setup and environment configuration
- Banner generation with DALL-E 3
- Validation system with Claude Vision

**Days 1-2**: Setup
- [ ] Repository setup
- [ ] Environment configuration
- [ ] API key setup
- [ ] Dependencies installation

**Days 3-4**: Banner MCP
- [ ] DALL-E 3 integration
- [ ] Prompt engineering
- [ ] File storage system
- [ ] Metadata generation

**Days 5-7**: Validation
- [ ] Claude Vision integration
- [ ] Validation scoring logic
- [ ] Regeneration workflow
- [ ] Testing and fine-tuning

**Milestone 1 Success Criteria**:
- ✅ 90%+ API success rate
- ✅ 80%+ validation pass rate
- ✅ Banner generation < 30 seconds
- ✅ All 3 banner sizes working

### Week 2: Video Generation & Agent Setup

**Goals**:
- Video generation with Veo 3.1
- FastAgent orchestration
- Tool routing and parameter extraction

**Days 8-10**: Video MCP
- [ ] Veo API integration
- [ ] Text-to-video flow
- [ ] Image-to-video flow
- [ ] Polling mechanism

**Days 11-12**: Agent Setup
- [ ] FastAgent configuration
- [ ] MCP server connections
- [ ] Tool definitions
- [ ] Testing

**Days 13-14**: Agent Logic
- [ ] Intent parsing
- [ ] Parameter extraction
- [ ] Tool routing
- [ ] Context management

**Milestone 2 Success Criteria**:
- ✅ Video generation working (text + image modes)
- ✅ Agent routes requests correctly
- ✅ Parameters extracted accurately
- ✅ Video generation < 3 minutes

### Week 3: User Interface Development

**Goals**:
- Complete Streamlit interface
- Interactive chat
- Gallery and downloads

**Days 15-16**: Basic UI
- [ ] Streamlit layout
- [ ] Banner form
- [ ] Video form
- [ ] File preview

**Days 17-18**: Interactive Chat
- [ ] Chat interface
- [ ] Conversation history
- [ ] Context management
- [ ] Agent integration

**Days 19-21**: Gallery & Polish
- [ ] Gallery view
- [ ] Filtering
- [ ] Download functionality
- [ ] UI polish and styling

**Milestone 3 Success Criteria**:
- ✅ Chat interface functional
- ✅ Conversation context maintained
- ✅ All workflows working
- ✅ Gallery operational

### Week 4: Testing, Documentation & Launch

**Goals**:
- Comprehensive testing
- Complete documentation
- Demo preparation
- Stakeholder presentation

**Days 22-23**: Testing
- [ ] End-to-end testing
- [ ] Bug fixes
- [ ] Performance testing
- [ ] Error scenarios

**Days 24-25**: Documentation
- [ ] README (this file)
- [ ] User guide
- [ ] Deployment guide
- [ ] API documentation

**Days 26-28**: Demo & Launch
- [ ] Sample content creation
- [ ] Demo script preparation
- [ ] Stakeholder demo
- [ ] Feedback collection
- [ ] Next steps planning

**Milestone 4 Success Criteria**:
- ✅ All features tested
- ✅ Zero critical bugs
- ✅ Documentation complete
- ✅ Positive stakeholder feedback
- ✅ Clear production roadmap

### Resource Requirements

**Team**: 2-3 developers
- Developer 1: Backend & APIs (Weeks 1-2)
- Developer 2: Frontend & UX (Weeks 3-4)
- Developer 3 (Optional): QA & Documentation

**Budget**:
- Development: 4 weeks × team cost
- API Testing: ~$50-100
- Infrastructure: Minimal (local dev)

### Success Metrics

**Technical**:
- 90%+ API success rate
- 80%+ validation pass rate
- < 30s banner generation
- < 3min video generation

**User Experience**:
- Intuitive interface
- < 5 clicks to generate
- Clear error messages
- 4+ satisfaction rating

**Business**:
- POC delivered on time
- All features working
- Positive feedback
- Clear production path

---

## 🤝 Contributing

We welcome contributions! Here's how:

### Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/marketing_generator.git
   ```
3. **Create a branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
4. **Make changes**
5. **Test your changes**
   ```bash
   uv run pytest
   ```
6. **Commit**
   ```bash
   git commit -m "Add amazing feature"
   ```
7. **Push**
   ```bash
   git push origin feature/amazing-feature
   ```
8. **Open Pull Request**

### Contribution Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Keep commits atomic and descriptive
- Use uv for all package management

### Code Style

```bash
# Before committing, run:
uv run black .
uv run isort .
uv run flake8 .
uv run pytest
```

---

## 📄 License

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2025 Marketing Content Generator Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgments

### Technologies
- [OpenAI DALL-E 3](https://openai.com/dall-e-3) - Banner generation
- [Google Veo 3.1](https://deepmind.google/technologies/veo/) - Video generation
- [Anthropic Claude](https://www.anthropic.com/claude) - Validation & orchestration
- [FastAgent](https://github.com/evalstate/fast-agent) - Agent framework
- [Streamlit](https://streamlit.io/) - Web interface
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

### Resources
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Anthropic's Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)

---

## 📞 Support

**Need help?**
- Check [Troubleshooting](#-troubleshooting) section
- Review [Configuration](#-configuration) details
- Check API provider status pages
- Create an issue on GitHub

**API Provider Support**:
- OpenAI: https://help.openai.com/
- Anthropic: https://support.anthropic.com/
- Google: https://cloud.google.com/support

---

## 🚀 Next Steps

1. **Follow Setup Instructions** above
2. **Test with sample content**
3. **Explore all features**
4. **Customize for your needs**
5. **Scale to production** when ready

---

<div align="center">

**Made with ❤️ using uv**

[GitHub](https://github.com/gpolydatas/marketing_generator) • [Issues](https://github.com/gpolydatas/marketing_generator/issues) • [Contribute](https://github.com/gpolydatas/marketing_generator/pulls)

**Ready to generate marketing content!** 🎨

</div>