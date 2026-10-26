---
title: AI Travel Booking System
emoji: ✈️
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.41.0"
app_file: frontend.py
pinned: false
---

# ✈️ AI Travel Booking System — Multi-Agent

A **multi-agent AI travel planner** built with **LangGraph**, **Groq (LLaMA 3.3 70B)**, and **PostgreSQL**. Four specialized agents collaborate in a pipeline to search flights, find hotels, generate a day-by-day itinerary, and deliver a complete travel plan — all from a single natural language query.

---

## 🖥️ Demo

| Terminal Mode | Browser UI (Streamlit) |
|---|---|
| `python main.py` | `streamlit run frontend.py` |
| Type your query, get a full plan | Interactive dark-themed web app |

---

## 🧠 How It Works — Agent Pipeline

```
User Query
    │
    ▼
① Flight Agent  ──→  Fetches live flight data (AviationStack API)
    │
    ▼
② Hotel Agent   ──→  Searches hotel & travel info (Tavily Search API)
    │
    ▼
③ Itinerary Agent ──→  Builds day-by-day itinerary (Groq LLaMA 3.3 70B)
    │
    ▼
④ Final Agent   ──→  Compiles full travel response (Groq LLaMA 3.3 70B)
    │
    ▼
  Output (terminal or Streamlit UI)
```

Each agent is a **LangGraph node** connected in a directed state graph. The shared `TravelState` passes data between agents. Conversation memory is persisted in **PostgreSQL** via `PostgresSaver`, so your session history is remembered across runs.

---

## 📁 Project Structure

```
multiagent project/
│
├── main.py               # Core agent graph (LangGraph)
├── frontend.py           # Streamlit web UI
│
├── tools/
│   ├── flight_tool.py    # AviationStack API integration
│   └── tavily_tool.py    # Tavily web search integration
│
├── travel_plans/         # Auto-saved travel plans (markdown, gitignored)
├── requirement.txt       # All dependencies
├── .env                  # API keys & DB URL (gitignored)
└── .gitignore
```

---

## ⚙️ Setup & Installation

### 1. Clone the repo
```bash
git clone https://github.com/Nikhil-sinhaa/Multi_agent.git
cd Multi_agent
```

### 2. Create and activate a virtual environment
```bash
python -m venv myvenv

# Windows
.\myvenv\Scripts\Activate.ps1

# macOS / Linux
source myvenv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirement.txt
```

### 4. Set up environment variables

Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
AVIATION_STACK_API_KEY=your_aviationstack_api_key
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/langraph_memory
```

| Key | Where to get it |
|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) |
| `AVIATION_STACK_API_KEY` | [aviationstack.com](https://aviationstack.com) |
| `DATABASE_URL` | Your local PostgreSQL instance |

### 5. Create the PostgreSQL database

Make sure PostgreSQL is running, then:
```bash
# Windows (PowerShell)
$env:PGPASSWORD="your_password"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE langraph_memory;"

# macOS / Linux
psql -U postgres -c "CREATE DATABASE langraph_memory;"
```

> The `checkpointer.setup()` call in `main.py` will automatically create the required checkpoint tables on first run.

---

## 🚀 Running the App

### Option A — Terminal (CLI)
```bash
python main.py
# Enter travel request: Paris trip in 3 days budget 50000
```

### Option B — Streamlit Web UI
```bash
streamlit run frontend.py
```
Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Agent Framework** | [LangGraph](https://github.com/langchain-ai/langgraph) |
| **LLM** | Groq — LLaMA 3.3 70B Versatile |
| **Flight Data** | AviationStack API |
| **Hotel / Web Search** | Tavily Search API |
| **Memory / Checkpointing** | PostgreSQL + `langgraph-checkpoint-postgres` |
| **Web UI** | Streamlit |
| **Environment** | Python 3.10, python-dotenv |

---

## 💾 Conversation Memory

This project uses **PostgreSQL** to persist the LangGraph checkpoint state. Each user session is identified by a `thread_id`. This means:

- ✅ Your travel history is **remembered** across multiple runs
- ✅ You can continue a previous session by reusing the same `thread_id`
- 🔄 To start fresh, change the `thread_id` in `main.py` (line 121) or in the Streamlit sidebar

To reset all memory:
```sql
-- Connect to the DB and run:
DELETE FROM checkpoints;
```

---

## 📦 Key Dependencies

```
langgraph
langgraph-checkpoint-postgres
langchain-groq
langchain-tavily
psycopg[binary]
streamlit
python-dotenv
requests
```

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

---

## 📄 License

MIT License — feel free to use and modify.
