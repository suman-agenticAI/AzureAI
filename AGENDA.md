# Azure AI — Learning Agenda

## Timeline: March 25 → April 30 (5 weeks)

| Week | Dates | Modules | Focus |
|------|-------|---------|-------|
| Week 1 | Mar 25-31 | Module 1 + 1B + 2 | Prompt Agents + MCP/A2A + Workflows |
| Week 2 | Apr 1-7 | Module 3 + 4 | API Gateway + Hosted Agents |
| Week 3 | Apr 8-14 | Module 5 + 5B + 6 | Memory + Foundry Tools + Evaluation |
| Week 4 | Apr 15-21 | Module 7 + 8 + 9 | Observability + Containers + Security |
| Week 5 | Apr 22-30 | Module 10 + 11 + 12 + 13 | CI/CD + Architecture + Cert + Portfolio |

### Concept-only (no code): Computer Use, Browser Automation, Voice Live, Translator, Load testing, Disaster recovery
### Code + practice: Everything else

## Block 1: Foundry Agent Service (AI Features)

### Module 1: Prompt Agents (Responses API)
- [ ] Setup dev environment (azure-ai-projects 2.x SDK, Responses API)
- [ ] Basic agent — single turn
- [ ] Conversational agent — multi-turn (previous_response_id)
- [ ] Function calling (tools)
- [ ] File Search
- [ ] Code Interpreter
- [ ] Bing Grounding
- [ ] Azure AI Search tool (as agent tool)
- [ ] OpenAPI Tools (call any REST API)
- [ ] Structured output (JSON schema)
- [ ] Streaming
- [ ] Context window management
- [ ] Deep Research tool
- [ ] Foundry IQ (multi-source data grounding)
- [ ] Enterprise connectors (SAP, Salesforce, Dynamics 365, SharePoint)

### Module 1B: Agent Communication Protocols
- [ ] MCP (Model Context Protocol) — build tools as reusable MCP servers
- [ ] A2A (Agent-to-Agent) — cross-platform agent communication + implementation
- [ ] Multi-agent patterns (sequential, fan-out/fan-in, router, group chat)

### Module 2: Workflow Agents
- [ ] Sequential workflow
- [ ] Branching (if/else)
- [ ] Group chat pattern
- [ ] Human-in-the-loop (approvals)
- [ ] YAML definition (VS Code)
- [ ] Variables + Power Fx expressions
- [ ] Workflow versioning

### Module 3: API Gateway (APIM)
- [ ] Setup APIM
- [ ] Authentication (API key, OAuth, Entra ID)
- [ ] Rate limiting
- [ ] Routing to multiple backends
- [ ] Load balancing
- [ ] Request/response transformation
- [ ] Multi-LLM routing by cost/latency/quality + fallback

### Module 4: Hosted Agents
- [ ] Microsoft Agent Framework (MAF) — AutoGen + Semantic Kernel merged
- [ ] Deploy LangGraph agent as Hosted Agent
- [ ] Deploy CrewAI agent as Hosted Agent
- [ ] Docker containerization
- [ ] Agent versioning + rollback
- [ ] Publishing to Teams / Copilot / REST API / Entra Agent Registry
- [ ] Agent identity (Entra Agent ID)
- [ ] Scaling (min/max replicas)
- [ ] Container logs + debugging

### Module 5: Memory Management
- [ ] Redis — caching (RAG cache, tool cache, semantic cache)
- [ ] Redis — session state (crash recovery)
- [ ] Redis — rate limiting
- [ ] Redis — conversation context (recent messages)
- [ ] Cosmos DB — permanent conversation history
- [ ] Cosmos DB — agent run logs + audit trails
- [ ] Cosmos DB — summarization for long conversations
- [ ] Foundry built-in Memory feature (managed long-term memory)

### Module 5B: Foundry Tools (Pre-built AI)
- [ ] Document Intelligence (OCR, invoice/receipt/form processing)
- [ ] Content Safety (moderation, jailbreak detection, XPIA)
- [ ] Speech (speech-to-text, text-to-speech, voice agents)
- [ ] Voice Live (real-time speech-to-speech with agents)
- [ ] Vision (image analysis, OCR)
- [ ] Language (sentiment, entity recognition, summarization)
- [ ] Translator (multi-language support)
- [ ] Computer Use (UI automation)
- [ ] Browser Automation

### Module 6: Evaluation + Safety
- [ ] AI Foundry evaluations (quality, groundedness, relevance, coherence)
- [ ] Custom evaluators
- [ ] Content Safety / guardrails
- [ ] Jailbreak detection + prompt injection (XPIA)
- [ ] Responsible AI
- [ ] Audit trails for agent actions
- [ ] Agent decision tracing (intermediate reasoning steps)

### Module 7: Observability
- [ ] App Insights setup
- [ ] Distributed tracing (end-to-end request flow)
- [ ] Agent tracing in Foundry Control Plane
- [ ] Metrics + dashboards
- [ ] Alerts (error rate, latency, token usage)
- [ ] Cost management + token budgets
- [ ] Cost per task tracking
- [ ] Task success rate measurement

## Block 2: Infrastructure & Deployment

### Module 8: Container Deployment + Service Bus
- [ ] Docker — containerize FastAPI agent app
- [ ] Azure Container Registry (ACR)
- [ ] Azure Container Apps — deploy
- [ ] Auto-scaling rules (HTTP, queue-based, KEDA)
- [ ] Service Bus — queues + topics
- [ ] Service Bus — trigger pattern (KEDA)
- [ ] Azure Functions (serverless alternative)
- [ ] App Service (simple deployment)

### Module 9: VNet + Security
- [ ] Private Endpoints (AI Search, Cosmos, Redis, OpenAI)
- [ ] VNet isolation
- [ ] Key Vault (secrets management)
- [ ] Managed Identity (no secrets in code)
- [ ] Entra Agent ID (identity per agent)
- [ ] RBAC per environment (dev/staging/prod access control)

### Module 10: CI/CD
- [ ] GitHub Actions — CI pipeline (test, build, scan)
- [ ] GitHub Actions — CD pipeline (deploy to dev/staging/prod)
- [ ] Terraform / Bicep — infrastructure as code
- [ ] Multi-environment setup (dev, staging, prod)
- [ ] Container Registry + Container Apps deployment

### Module 10B: Advanced Deployment
- [ ] Blue-green deployment
- [ ] A/B testing agent versions
- [ ] Load testing
- [ ] Multi-tenant architecture
- [ ] Disaster recovery

## Block 3: Architecture + Portfolio

### Module 11: Architecture Patterns
- [ ] Agentic AI architecture (perception, reasoning, action, memory)
- [ ] Separation of concerns (agent reasoning vs tool execution vs safety)
- [ ] Architecture decision records
- [ ] Reference architectures from Azure Architecture Center

### Module 12: Certification
- [ ] Microsoft Certified: Agentic AI Business Solutions Architect
- [ ] AI-102 (Azure AI Engineer)

### Module 13: Portfolio + Interview Prep
- [ ] Architecture diagram (complete system)
- [ ] GitHub README (professional)
- [ ] End-to-end project (combines all modules)
- [ ] Interview talking points
- [ ] System design practice (whiteboard scenarios)
