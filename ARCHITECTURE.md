# Marketing Content Generator - Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [API Integration](#api-integration)
7. [Security Architecture](#security-architecture)
8. [Deployment Architecture](#deployment-architecture)

---

## System Overview

### Purpose
AI-powered marketing content generation system that creates banner advertisements and promotional videos through natural language conversation with an intelligent agent.

### Key Capabilities
- **Interactive AI Agent**: Natural language interface with conversation memory
- **Banner Generation**: DALL-E 3 powered image creation with validation
- **Video Generation**: Google Veo 3.1 for motion content
- **Image-to-Video**: Animate static banners into dynamic videos
- **Quality Assurance**: Automated validation using Claude vision

### Users
- Marketing teams
- Content creators
- Campaign managers
- Creative agencies

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
│                    (Streamlit Web App)                           │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Chat Interface│  │ Manual Forms │  │   Gallery    │         │
│  │  (Interactive)│  │  (Structured)│  │   (Browse)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                           │
│                   (FastAgent Framework)                          │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Marketing Orchestrator Agent                    │  │
│  │  • Natural language understanding                         │  │
│  │  • Context management (3 exchanges)                       │  │
│  │  • Workflow routing                                       │  │
│  │  • Parameter extraction                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│    MCP SERVER LAYER      │  │    MCP SERVER LAYER      │
│   (Banner Generation)    │  │   (Video Generation)     │
│                          │  │                          │
│  ┌──────────────────┐   │  │  ┌──────────────────┐   │
│  │ generate_banner  │   │  │  │ generate_video   │   │
│  │ validate_banner  │   │  │  │ validate_video   │   │
│  └──────────────────┘   │  │  └──────────────────┘   │
└───────────┬──────────────┘  └───────────┬──────────────┘
            │                             │
            ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│    EXTERNAL AI APIs      │  │    EXTERNAL AI APIs      │
│                          │  │                          │
│  ┌──────────────────┐   │  │  ┌──────────────────┐   │
│  │   DALL-E 3       │   │  │  │   Google Veo     │   │
│  │   (OpenAI)       │   │  │  │   3.1 (Video)    │   │
│  └──────────────────┘   │  │  └──────────────────┘   │
│                          │  │                          │
│  ┌──────────────────┐   │  │  ┌──────────────────┐   │
│  │  Claude Sonnet   │   │  │  │  Claude Sonnet   │   │
│  │  (Validation)    │   │  │  │  (Validation)    │   │
│  └──────────────────┘   │  │  └──────────────────┘   │
└──────────────────────────┘  └──────────────────────────┘
            │                             │
            └─────────────┬───────────────┘
                          ▼
            ┌──────────────────────────┐
            │    STORAGE LAYER         │
            │                          │
            │  • Generated banners     │
            │  • Generated videos      │
            │  • Metadata (JSON)       │
            │  • Validation results    │
            └──────────────────────────┘
```

---

## Component Architecture

### 1. Frontend Layer (Streamlit App)

**File**: `app.py`

**Components**:
- **Chat Interface**
  - Message input form
  - Conversation history display
  - Context management (last 6 messages)
  - Clear chat functionality

- **Manual Forms**
  - Banner creation form
  - Video creation form
  - Image-to-video form

- **Gallery**
  - Content browser
  - Filter by type (banner/video)
  - Preview and download

**Responsibilities**:
- User interaction
- Session state management
- Display logic
- File handling

### 2. Orchestration Layer (FastAgent)

**File**: `agent.py`

**Components**:
- **Marketing Orchestrator Agent**
  - Natural language understanding
  - Intent detection
  - Parameter extraction
  - Tool selection
  - Workflow coordination

**Responsibilities**:
- Parse user requests
- Maintain conversation context
- Route to appropriate MCP servers
- Aggregate results
- Handle errors

### 3. MCP Server Layer

#### Banner MCP Server
**File**: `banner_mcp_server.py`

**Tools**:
1. `generate_banner`
   - Input: campaign, brand, type, message, CTA
   - Output: Banner image (PNG) + metadata
   - Process: Prompt engineering → DALL-E 3 → Save file

2. `validate_banner`
   - Input: filepath, expected content
   - Output: Validation scores + pass/fail
   - Process: Image → Claude Vision → Quality assessment

#### Video MCP Server
**File**: `video_mcp_server.py`

**Tools**:
1. `generate_video`
   - Input: campaign, brand, duration, description, optional image
   - Output: Video file (MP4) + metadata
   - Process: Prompt engineering → Veo 3.1 → Save file

2. `validate_video`
   - Input: filepath, expected content
   - Output: Validation scores + pass/fail
   - Process: Manual review (video validation not automated)

### 4. External AI Services

**OpenAI DALL-E 3**:
- Purpose: Banner image generation
- Model: `dall-e-3`
- Quality: HD
- Sizes: 1024x1024, 1792x1024, 1024x1792

**Google Veo 3.1**:
- Purpose: Video generation
- Durations: 4s, 6s, 8s
- Resolutions: 720p, 1080p
- Aspect ratios: 16:9, 9:16

**Anthropic Claude**:
- Purpose: Validation and orchestration
- Model: `claude-sonnet-4-20250514`
- Capabilities: Vision, text analysis

### 5. Storage Layer

**Local Filesystem**:
```
outputs/
├── banner_social_1792x1024_20251026_094107.png
├── banner_social_1792x1024_20251026_094107.json
├── video_short_4s_image_20251026_100050.mp4
└── video_short_4s_image_20251026_100050.json
```

**Metadata Structure**:
```json
{
  "campaign": "Campaign Name",
  "brand": "Brand Name",
  "type": "banner",
  "filename": "banner_social_1792x1024_timestamp.png",
  "filepath": "/outputs/banner_social_1792x1024_timestamp.png",
  "url": "https://...",
  "size": "1792x1024",
  "file_size_mb": 1.2,
  "timestamp": "2025-10-26T09:41:07",
  "validation": {
    "passed": true,
    "scores": {...}
  }
}
```

---

## Data Flow

### Scenario 1: Banner Creation via Chat

```
User Input
   │
   ├─> "Create a Black Friday banner for Nike"
   │
   ▼
Streamlit Form
   │
   ├─> Capture message
   ├─> Add to session state
   │
   ▼
FastAgent Orchestrator
   │
   ├─> Parse intent: "banner"
   ├─> Extract parameters:
   │   • campaign: "Black Friday"
   │   • brand: "Nike"
   │   • type: "social"
   │   • message: "Sale"
   │   • CTA: "Shop Now"
   │
   ▼
Banner MCP Server
   │
   ├─> generate_banner()
   │   ├─> Build DALL-E prompt
   │   ├─> Call OpenAI API
   │   ├─> Download image
   │   ├─> Save to outputs/
   │   └─> Save metadata JSON
   │
   ▼
Agent Response
   │
   ├─> Return filepath + metadata
   │
   ▼
Banner MCP Server (Validation)
   │
   ├─> validate_banner()
   │   ├─> Load image
   │   ├─> Encode base64
   │   ├─> Call Claude Vision
   │   ├─> Parse validation results
   │   └─> Return scores
   │
   ▼
FastAgent Response
   │
   ├─> Format results
   ├─> Include validation
   │
   ▼
Streamlit Display
   │
   ├─> Show success message
   ├─> Display validation scores
   ├─> Add to conversation history
   └─> Update gallery
```

### Scenario 2: Image-to-Video via Chat

```
User Input (Follow-up)
   │
   ├─> "Now animate it with a zoom effect"
   │
   ▼
Streamlit Form
   │
   ├─> Capture message
   ├─> Load conversation history (last 6 messages)
   │
   ▼
FastAgent Orchestrator
   │
   ├─> Understand context from history
   ├─> Extract filename from previous exchange
   ├─> Parse intent: "image-to-video"
   ├─> Extract parameters:
   │   • input_image_path: "outputs/banner_social_*.png"
   │   • description: "zoom effect"
   │   • duration: "short"
   │
   ▼
Video MCP Server
   │
   ├─> generate_video()
   │   ├─> Build Veo prompt (motion only)
   │   ├─> Call Google Veo API with image
   │   ├─> Poll for completion
   │   ├─> Download video
   │   ├─> Save to outputs/
   │   └─> Save metadata JSON
   │
   ▼
FastAgent Response
   │
   ├─> Return filepath + metadata
   │
   ▼
Streamlit Display
   │
   ├─> Show success message
   ├─> Add to conversation history
   └─> Update gallery
```

---

## Technology Stack

### Frontend
- **Framework**: Streamlit 1.28+
- **Language**: Python 3.8+
- **UI Components**: Native Streamlit widgets
- **Session Management**: Streamlit session state

### Backend/Orchestration
- **Agent Framework**: FastAgent (MCP-based)
- **Protocol**: Model Context Protocol (MCP)
- **Async Runtime**: asyncio
- **Configuration**: YAML

### AI Services
- **Image Generation**: OpenAI DALL-E 3
- **Video Generation**: Google Veo 3.1
- **Validation**: Anthropic Claude Sonnet 4
- **Orchestration**: Anthropic Claude

### Storage
- **Type**: Local filesystem
- **Formats**: PNG (images), MP4 (videos), JSON (metadata)
- **Structure**: Timestamped filenames

### Dependencies
```
streamlit>=1.28.0
anthropic>=0.18.0
openai>=1.12.0
pyyaml>=6.0
requests>=2.31.0
fast-agent
mcp
Pillow>=10.0.0
```

---

## API Integration

### OpenAI Integration (DALL-E 3)

**Endpoint**: `https://api.openai.com/v1/images/generations`

**Authentication**: Bearer token (API key)

**Request**:
```python
{
  "model": "dall-e-3",
  "prompt": "Enhanced marketing prompt...",
  "size": "1792x1024",
  "quality": "hd",
  "style": "vivid",
  "n": 1
}
```

**Response**:
```python
{
  "data": [{
    "url": "https://...",
    "revised_prompt": "..."
  }]
}
```

**Rate Limits**: 
- 50 images/minute
- Cost: ~$0.08/image (HD)

### Google Veo Integration

**Endpoint**: Custom Google API endpoint

**Authentication**: API key

**Request**:
```python
{
  "prompt": "Video description...",
  "duration": 6,
  "resolution": "720p",
  "aspect_ratio": "16:9",
  "input_image": "base64..." (optional)
}
```

**Response**:
```python
{
  "video_url": "https://...",
  "status": "completed",
  "duration": 6
}
```

**Generation Time**: 1-3 minutes

### Anthropic Integration (Claude)

**Endpoint**: `https://api.anthropic.com/v1/messages`

**Authentication**: x-api-key header

**Request (Vision)**:
```python
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 2000,
  "messages": [{
    "role": "user",
    "content": [
      {
        "type": "image",
        "source": {
          "type": "base64",
          "media_type": "image/png",
          "data": "..."
        }
      },
      {
        "type": "text",
        "text": "Validation prompt..."
      }
    ]
  }]
}
```

**Response**:
```python
{
  "content": [{
    "type": "text",
    "text": "JSON validation results..."
  }]
}
```

---

## Security Architecture

### API Key Management

**Storage**:
- **File**: `fastagent.secrets.yaml` (local only, gitignored)
- **Environment Variables**: Fallback option
- **Never committed**: Protected by .gitignore

**Structure**:
```yaml
openai:
  api_key: "sk-..."

anthropic:
  api_key: "sk-ant-..."

google:
  api_key: "..."
```

### Data Security

**Sensitive Data**:
- API keys (never logged or exposed)
- Generated content (stored locally)
- User conversations (in-memory, not persisted)

**Protection Measures**:
- Secrets file gitignored
- No API keys in logs
- Local storage only
- No database (no data breach risk)

### Network Security

**HTTPS**: All API calls use HTTPS
**Token-based auth**: No password storage
**Rate limiting**: Handled by API providers

---

## Deployment Architecture

### Development Environment

```
Developer Machine
├── Python 3.8+ virtual environment
├── Local file storage (outputs/)
├── Streamlit dev server (localhost:8501)
└── API keys in fastagent.secrets.yaml
```

**Command**:
```bash
streamlit run app.py
```

### Production Deployment Options

#### Option 1: Streamlit Cloud
```
Streamlit Cloud
├── GitHub repository sync
├── Secrets in cloud dashboard
├── Auto-deploy on push
└── Public URL: https://app-name.streamlit.app
```

#### Option 2: Self-Hosted Server
```
Linux Server (Ubuntu)
├── systemd service for auto-start
├── nginx reverse proxy
├── SSL certificate (Let's Encrypt)
├── File storage: /var/marketing-generator/outputs
└── Logs: /var/log/marketing-generator
```

#### Option 3: Docker Container
```
Docker Container
├── Python base image
├── App files copied in
├── Volume mount for outputs/
├── Environment variables for secrets
└── Port 8501 exposed
```

**Dockerfile**:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

---

## Scalability Considerations

### Current Limitations
- **Local storage**: Single machine
- **Synchronous processing**: One request at a time
- **No queue**: Can't handle burst traffic
- **Session state**: In-memory only

### Future Improvements

**Phase 1: Storage**
- Move to cloud storage (S3, GCS)
- Database for metadata (PostgreSQL)
- CDN for content delivery

**Phase 2: Processing**
- Background job queue (Celery, Redis)
- Async processing
- Multiple workers

**Phase 3: Infrastructure**
- Load balancer
- Auto-scaling
- Distributed storage
- Session persistence (Redis)

---

## Monitoring and Logging

### Current Approach
- Streamlit console logs
- Error display in UI
- No persistent logging

### Production Needs
- **Application logs**: Structured JSON logs
- **API call tracking**: Success/failure rates
- **Performance metrics**: Response times
- **Error tracking**: Sentry or similar
- **Usage analytics**: User behavior patterns

---

## Cost Estimation

### API Costs (Per Request)

**Banner Generation**:
- DALL-E 3 HD: ~$0.08
- Claude validation: ~$0.003
- **Total**: ~$0.083 per banner

**Video Generation**:
- Veo 3.1 (6s): ~$0.50 (estimated)
- Claude validation: ~$0.003
- **Total**: ~$0.503 per video

**Monthly Estimate (100 banners + 50 videos)**:
- Banners: 100 × $0.083 = $8.30
- Videos: 50 × $0.503 = $25.15
- **Total**: ~$33.45/month

---

## Future Architecture Enhancements

### Short Term (3-6 months)
1. **User Authentication**: Multi-user support
2. **Cloud Storage**: S3/GCS integration
3. **Asset Library**: Reusable brand assets
4. **Templates**: Pre-configured banner/video templates

### Medium Term (6-12 months)
1. **Batch Processing**: Generate multiple variants
2. **A/B Testing**: Generate test variations
3. **Brand Guidelines**: Automated brand compliance
4. **Analytics**: Performance tracking

### Long Term (12+ months)
1. **Multi-platform**: Web, mobile, desktop
2. **API Access**: REST API for integrations
3. **Enterprise Features**: Teams, approval workflows
4. **AI Training**: Custom models on brand data

---

## Appendix

### Configuration Files

**fastagent.config.yaml**:
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

### File Naming Conventions

**Banners**: `banner_{type}_{size}_{timestamp}.png`
- Example: `banner_social_1792x1024_20251026_094107.png`

**Videos**: `video_{duration}_{mode}_{timestamp}.mp4`
- Example: `video_short_4s_image_20251026_100050.mp4`

**Metadata**: Same as content file with `.json` extension

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-26 | System | Initial architecture documentation |

---

**Document Status**: ✅ Current
**Last Updated**: October 26, 2025
**Next Review**: January 2026
