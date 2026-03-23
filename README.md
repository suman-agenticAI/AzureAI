# Azure AI — Agentic AI on Azure

4-week accelerated plan: Azure AI Agent Service + Enterprise Deployment.

## About

Building and deploying production-ready AI agents on Microsoft Azure. Covers Azure AI Agent Service (managed platform), Azure AI Search, Container Apps, APIM, Content Safety, and enterprise security patterns.

## 4-Week Plan

### Week 1: Azure AI Agent Service (Managed Platform)

Learn Microsoft's managed agent platform — create agents, use tools, build multi-agent systems.

| # | Lesson | What You Learn | File |
|---|--------|---------------|------|
| 1 | First Agent | Agent, Thread, Run — core concepts | `01_first_agent.py` |
| 2 | Function Calling | Agent using custom tools | `02_function_calling.py` |
| 3 | File Search | Upload docs, agent searches them (built-in RAG) | `03_file_search.py` |
| 4 | Code Interpreter | Agent writes & runs Python in sandbox | `04_code_interpreter.py` |
| 5 | Bing Grounding | Agent searches the web for real-time data | `05_bing_grounding.py` |
| 6 | Multi-Agent | Connected agents collaborating | `06_multi_agent.py` |
| 7 | Streaming | Real-time token streaming | `07_streaming.py` |
| 8 | Enterprise Basics | Tracing, error handling, content safety | `08_enterprise.py` |
| 9 | Real-World Project | End-to-end support pipeline on Agent Service | `project/` |

### Week 2: Azure Infrastructure (AI Search + Container Apps + Cosmos DB)

Deploy your LangGraph agent on Azure — swap backends, containerize, persist state.

| Day | Focus | Azure Services |
|-----|-------|---------------|
| 1 | Azure AI Search setup | AI Search (vector index + hybrid search) |
| 2 | Swap LangGraph retriever | AzureSearch LangChain integration |
| 3 | FastAPI + Docker | Wrap agent as API, containerize |
| 4 | Deploy to Container Apps | Azure Container Apps + ACR |
| 5 | Cosmos DB state | Persistent checkpointing + Key Vault secrets |

### Week 3: Evaluate + Govern (AI Foundry + Content Safety + APIM)

Make your agent measurable, safe, and cost-controlled.

| Day | Focus | Azure Services |
|-----|-------|---------------|
| 1 | Evaluation dataset | AI Foundry eval pipelines |
| 2 | Run evaluators | Groundedness, relevance, coherence scoring |
| 3 | Observability | OpenTelemetry + Application Insights |
| 4 | Content Safety | Prompt shields, jailbreak detection |
| 5 | APIM AI Gateway | Multi-LLM routing, token quotas, fallback |

### Week 4: Security + Portfolio Capstone

Lock it down. Document it. Prepare for interviews.

| Day | Focus | Azure Services |
|-----|-------|---------------|
| 1 | Private Endpoints | Azure OpenAI + AI Search off public internet |
| 2 | VNet + Managed Identity | Zero secrets, VNet isolation |
| 3 | Security audit | Defender for Cloud, fix findings |
| 4 | Architecture doc | System design, decisions, trade-offs, cost |
| 5 | GitHub portfolio | Clean code, README, architecture diagram, demo script |

## Tech Stack

- Python 3.12
- Azure AI Agent Service (Azure AI Foundry)
- Azure OpenAI (GPT-4o)
- Azure AI Search, Container Apps, Cosmos DB, APIM, Content Safety
- azure-ai-projects / azure-ai-agents SDK

## Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install azure-ai-projects azure-ai-agents azure-identity python-dotenv

# Configure (create .env file)
AZURE_AI_PROJECT_CONNECTION_STRING=your-project-connection-string
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Run any lesson
python 01_first_agent.py
```

## Prerequisites

1. Azure subscription with Azure AI Foundry access
2. Azure AI Foundry project created at [ai.azure.com](https://ai.azure.com)
3. Azure OpenAI resource with GPT-4o deployed

## Certification Track (in parallel)

| Cert | When | Notes |
|------|------|-------|
| AI-900 | Week 1 | Quick — you already know the concepts |
| AI-102 | Week 3-4 | Most cited cert in India Agentic AI JDs |
| AZ-305 | After Week 4 | Architect credential (requires AZ-900 first) |

## Author

**Suman Rao Balumuri**
Solution Architect | Agentic AI Enthusiast
