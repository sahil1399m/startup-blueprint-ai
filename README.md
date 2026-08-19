<div align="center">

# 🚀 Startup Blueprint Generator
### AI-Powered Startup Intelligence Platform for the Indian Ecosystem

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![IBM Granite](https://img.shields.io/badge/IBM%20Granite%204.0-0530AD?style=for-the-badge&logo=ibm&logoColor=white)](https://www.ibm.com/watsonx)
[![Groq](https://img.shields.io/badge/Groq%20Llama%203.3-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com)
[![Gemini](https://img.shields.io/badge/Gemini%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/gemini)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**Generate a complete, policy-grounded startup blueprint in minutes — powered by CRAG, IBM Granite 4.0, Groq Llama 3.3 & Gemini Flash**

[Live Demo](https://startupgenratingragmodel-ehjsvexardml5voavk29rk.streamlit.app) · [Report Bug](https://github.com/sahil1399m/Project-startup_genrating_RAG_model/issues) · [Request Feature](https://github.com/sahil1399m/Project-startup_genrating_RAG_model/issues)

</div>

---

## 📸 Preview

> Sign in → Describe your idea → Get a full blueprint in under 60 seconds

---

## ✨ What It Does

The **Startup Blueprint Generator** takes a raw startup idea and produces a complete, investor-ready business blueprint grounded in real Indian government policy documents and live web data.

| Section | What You Get |
|---|---|
| 📋 Business Model Canvas | All 9 building blocks auto-generated |
| 💰 Phase-wise Budget | MVP → Launch → Growth with visual charts |
| 📣 Go-to-Market Strategy | Launch plan + 12-month milestone roadmap |
| 🤝 Investor & Scheme Matcher | DPIIT, MSME, Startup India schemes |
| 🏆 Competitor Landscape | Market share + differentiator analysis |
| ⚠️ Risk Matrix | Probability × severity with mitigations |
| 🧠 AI Mentor | Interactive Q&A grounded in your blueprint |

---

## 🧠 How It Works — The CRAG Pipeline

This project implements **Corrective RAG (Yan et al. 2024, arXiv:2401.15884)** with a custom CrossEncoder evaluator and Gemini Flash query rewriter.

User Idea
↓
[Gemini Flash] — Query Rewriting (10-field structured brief)
↓
[ChromaDB + SentenceTransformer] — Dense retrieval over 13 policy PDFs
↓
[CrossEncoder] — Relevance scoring via raw logits
↓
├── CORRECT  (logit ≥ -3.0)  → PDF only → IBM Granite 4.0
├── AMBIGUOUS (between)      → PDF + Tavily → IBM Granite 4.0
└── INCORRECT (logit < -6.5) → Tavily only → Groq (no blueprint)
↓
[Groq Llama 3.3] — 6-section structured blueprint generation
↓
[Supabase PostgreSQL] — History persistence

---

## 🤖 AI Models Used

| Model | Role |
|---|---|
| **IBM Granite 4.0** (`ibm/granite-4-h-small`) | Policy brief synthesis from grounded PDF context |
| **Groq Llama 3.3 70B** | 6-section blueprint generation (BMC, Budget, GTM, etc.) |
| **Google Gemini 2.5 Flash** | Query rewriting — rough idea → structured 10-field brief |
| **SentenceTransformer** `all-MiniLM-L6-v2` | Dense embeddings for ChromaDB retrieval |
| **CrossEncoder** `ms-marco-MiniLM-L-6-v2` | CRAG relevance evaluation using raw logits |
| **Tavily** | Live web search for real-time market intelligence |

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit (custom dark theme, professional UI) |
| **Authentication** | IBM App ID (OAuth2/OIDC, Cloud Directory, Google login) |
| **Vector DB** | ChromaDB (persistent, 13 Indian policy PDFs embedded) |
| **Relational DB** | Supabase PostgreSQL (blueprints, mentor sessions) |
| **AI Orchestration** | Python (custom CRAG pipeline) |
| **Deployment** | Streamlit Cloud |
| **News Feed** | NewsAPI (live Indian startup ecosystem news) |

---

## 📁 Project Structure

```
IBM_PROJ/
├── app.py                   # Main Streamlit app & UI orchestrator
├── crag.py                  # CRAG pipeline (Corrective RAG engine)
├── auth.py                  # IBM App ID authentication
├── history_db.py            # Supabase PostgreSQL — blueprint history
├── history_ui.py            # History page UI
├── history.py               # History save/load helpers
├── data_ingestion.py        # PDF → ChromaDB ingestion
├── news_feed.py             # NewsAPI live feed
├── mentor_ui.py             # AI Mentor chat UI
├── mentor/
│   ├── mentor_agent.py      # Mentor AI logic
│   ├── mentor_db.py         # Supabase — mentor conversations
│   ├── context.py           # Blueprint context builder
│   ├── intent_classifier.py # 14-intent Groq classifier
│   ├── synthesizer.py       # Granite answer synthesizer
│   ├── tool_router.py       # Tool selection router
│   └── memory.py            # Conversation memory
├── data/
│   ├── government/          # DPIIT, Startup India PDFs
│   ├── funding/             # BCG, funding guides
│   ├── legal/               # Legal frameworks
│   ├── incubators/          # AIM, AIC guidelines
│   └── ...                  # 13 policy PDFs total
├── requirements.txt
└── .env.example
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Git

### 1. Clone the repo
```bash
git clone https://github.com/sahil1399m/Project-startup_genrating_RAG_model.git
cd Project-startup_genrating_RAG_model
```

### 2. Create virtual environment
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy `.env.example` to `.env` and fill in your keys:

```env
# IBM watsonx.ai
IBM_API_KEY=your_ibm_api_key
IBM_PROJECT_ID=your_project_id
IBM_URL=https://us-south.ml.cloud.ibm.com

# IBM App ID (Authentication)
APPID_CLIENT_ID=your_client_id
APPID_SECRET=your_secret
APPID_TENANT_ID=your_tenant_id
APPID_OAUTH_URL=https://us-south.appid.cloud.ibm.com/oauth/v4/YOUR_TENANT
APPID_PROFILES_URL=https://us-south.appid.cloud.ibm.com
APPID_REDIRECT_URI=http://localhost:8501

# AI APIs
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_gemini_key
TAVILY_API_KEY=your_tavily_key
NEWS_API_KEY=your_newsapi_key

# Supabase PostgreSQL
DB_HOST=aws-0-ap-south-1.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.your_project_id
DB_PASSWORD=your_password
```

### 5. Run the app
```bash
python -m streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 🔐 Security Features

- **IBM App ID** — Enterprise OAuth2/OIDC with Cloud Directory and Google login
- **Rate Limiting** — 5 failed login attempts → 5 minute lockout
- **Password Validation** — Uppercase, lowercase, number requirements
- **Session Timeout** — Auto logout after 8 hours
- **bcrypt** — Industry-standard password hashing (not SHA-256)
- **Supabase RLS** — Row Level Security enabled on all tables
- **No secrets in code** — All keys via `.env` / Streamlit secrets

---

## 📊 Knowledge Base

The CRAG pipeline retrieves from **13 curated Indian government policy PDFs**:

| Category | Documents |
|---|---|
| 🏛️ Government | Startup India Kit, DPIIT Playbook, MSME e-Book |
| 💰 Funding | BCG India Startup Report, Digital Lending Guide |
| ⚖️ Legal | Legal Framework Guides |
| 🏢 Incubators | AIC Guidelines, AIM Brochure, AIM-CSR Guidebook |
| 📊 Business | Business Model Canvas Manual |
| 📈 Reports | Annual Report 2024-25 |
| 📋 Templates | Pitch Deck Guidelines |

---

## 🌐 Deployment

### Streamlit Cloud (Current)
1. Push to GitHub
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Connect your repo → select `app.py`
4. Add all secrets in **Advanced Settings → Secrets**
5. Update `APPID_REDIRECT_URI` to your Streamlit Cloud URL
6. Add the Streamlit Cloud URL to IBM App ID redirect URLs

---

## 🗺️ Roadmap

- [x] CRAG pipeline with CrossEncoder evaluation
- [x] IBM App ID authentication
- [x] Supabase PostgreSQL persistence
- [x] AI Mentor with 14 intent types
- [x] Blueprint history with favorites
- [x] Live news feed
- [ ] Multi-language support (Hindi, Marathi, Tamil)
- [ ] IBM Code Engine deployment
- [ ] Startup progress tracker
- [ ] Investor pitch deck PDF export
- [ ] Real competitor data (Crunchbase, Tracxn APIs)

---

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [Yan et al. 2024](https://arxiv.org/abs/2401.15884) — Corrective RAG paper
- [IBM watsonx.ai](https://www.ibm.com/watsonx) — Granite 4.0 foundation model
- [Startup India](https://www.startupindia.gov.in) — Policy knowledge base
- [DPIIT](https://dpiit.gov.in) — Startup recognition framework

---

<div align="center">
Built with ❤️ for the Indian startup ecosystem
<br>
<b>IBM Granite 4.0 · Groq Llama 3.3 · Gemini Flash · CRAG · Supabase · IBM App ID</b>
</div>

