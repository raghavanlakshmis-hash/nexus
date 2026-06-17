# Nexus
## Multi-Agent Post-Hospital Recovery System | Week 3 — Agentic AI Systems

### What it does
Nexus is a multi-agent system that takes a hospital discharge summary
and becomes a 30-day recovery co-pilot — tracking medications, monitoring daily
symptoms, scheduling follow-ups, and escalating to humans before anything goes wrong.

### Architecture
- **Intake Agent** — Parses discharge PDF, extracts structured clinical data
- **Care Plan Agent** — Checks medication interactions (OpenFDA), generates plain-language recovery plan
- **Monitoring Agent** — Daily check-in loop with GREEN/YELLOW/RED classification
- **Escalation Agent** — Tier-based emergency response with human-in-the-loop
- **Admin Agent** — Appointment reminders, family updates, weekly summaries
- **Orchestrator** — LangGraph state machine coordinating all agents

### UI
7 screens built in Streamlit with soft purple theme (`.streamlit/config.toml`):
- Onboarding — PDF upload and patient setup
- Care plan — day-by-day checklists, medications, warning signs
- Daily check-in — ElevenLabs voice input with typed fallback
- Approval queue — human review before any outbound message
- Recovery dashboard — daily vitals log, medication adherence bars
- Provider summary — auto-generated shareable brief with export
- Hospital history — auto-populated from discharge PDFs, manually extensible

### Setup

1. Clone the repo
   git clone https://github.com/YOUR_USERNAME/nexus.git
   cd nexus

2. Install dependencies
   pip install -r requirements.txt

3. Copy .env.example to .env and fill in your API keys
   cp .env.example .env

4. Set up Pinecone index
   - Name: nexus
   - Dimensions: 1536
   - Metric: cosine

5. Run the app
   streamlit run ui/streamlit_app.py

### Demo
Upload the synthetic discharge summary in /data/synthetic_discharge_sample.txt
to see the full pipeline in action. No real patient data is used.

### Week 3 Rubric Compliance
- ✅ Multi-agent system (5 specialized subagents + orchestrator)
- ✅ Tool use (6 tools across the pipeline)
- ✅ Persistent state (Pinecone across 30-day recovery period)
- ✅ Error recovery (retry logic, fallbacks, graceful degradation)
- ✅ Human-in-the-loop (3 distinct handoff types)
- ✅ Nebius Token Factory (care plan generation step)
- ✅ LangGraph (stateful graph orchestration)