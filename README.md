# Sleep Agent Deployment Package

This is the minimal deployment package for the Sleep Agent, containing only the essential files needed for production deployment.

## Structure

```
deployment/
├── sleep_agent/          # Main agent
│   ├── __init__.py
│   └── agent.py         # The root_agent definition
├── tools/               # Agent tools
│   ├── knowledge_base_tool.py
│   ├── wake_window_specialist_agent.py
│   ├── wake_window_assessment_tool.py
│   └── wake_window_tools.py
├── knowledge_base/      # Knowledge data
│   └── sleep_knowledge_graph.json
├── requirements.txt     # Minimal dependencies
└── README.md           # This file
```

## Deployment Options

### 1. Vertex AI Agent Engine (Recommended)
```bash
# From the deployment directory
gcloud adk agents deploy sleep-specialist \
    --project=YOUR_PROJECT_ID \
    --location=us-central1 \
    --source=. \
    --agent-module=sleep_agent.agent
```

### 2. Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Test the agent
python -c "from sleep_agent.agent import root_agent; print(root_agent.name)"
```

### 3. Container Deployment
Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "-m", "google.adk.runners.local", "sleep_agent.agent:root_agent"]
```

## Environment Variables

Create a `.env` file for local development:
```bash
# For Vertex AI deployment
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id

# For local testing with API key
GOOGLE_API_KEY=your-api-key
GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

## Key Components

### 1. Main Agent (`sleep_agent/agent.py`)
- Name: `sleep_specialist`
- Model: `gemini-2.0-flash`
- Provides evidence-based sleep consultation

### 2. Knowledge Base Tool
- Searches comprehensive sleep knowledge graph
- Returns problem-specific solutions
- Provides age-appropriate recommendations

### 3. Wake Window Specialist
- Calculates optimal wake windows
- Adjusts based on baby's behavior
- Creates customized schedules

## Production Notes

1. **Session Management**: When deployed to Vertex AI, sessions are automatically persisted
2. **Rate Limiting**: Implement at the API gateway level
3. **Monitoring**: Use Google Cloud Logging and Monitoring
4. **Scaling**: Vertex AI handles auto-scaling

## Testing

Before deployment, test locally:
```python
# Quick test script
from sleep_agent.agent import root_agent
print(f"Agent loaded: {root_agent.name}")
print(f"Tools available: {len(root_agent.tools)}")
```

## Support

For issues or questions, refer to:
- Google ADK documentation
- Vertex AI Agent Engine docs
- The main project repository