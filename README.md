# 📈 TradingAgents-Dashboard (Personal Trading Room)

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/github/license/jiwoomap/TradingAgents-Dashboard)
[![Python CI](https://github.com/jiwoomap/TradingAgents-Dashboard/actions/workflows/python-app.yml/badge.svg)](https://github.com/jiwoomap/TradingAgents-Dashboard/actions/workflows/python-app.yml)

> 🚀 **Your Personal AI Analyst with Long-term Memory.**  
> A Dockerized dashboard that turns [TradingAgents](https://github.com/TauricResearch/TradingAgents) into a personalized trading assistant. It not only analyzes the market but also **remembers your insights via Markdown files (RAG).**

<p align="center">
  <img src="assets/demo.gif" alt="Demo Animation" width="100%">
</p>

<details>
<summary>📸 <strong>Click to view Dashboard Screenshot</strong></summary>
<p align="center">
  <img src="assets/dashboard_sample.png" alt="Dashboard Screenshot" width="100%">
  <br>
  <em>Real-time analysis and logging in the web dashboard</em>
</p>
</details>

## 🎯 Project Goal: "Data Persistence & Growth"
Most AI trading tools are "stateless"—they analyze and forget.  
**TradingAgents-Dashboard** is designed for individual traders who want to **accumulate knowledge**.

1.  **Visualize:** No more terminal logs. Watch agents debate in a clean Web UI.
2.  **Persist:** External news links rot, and data disappears. This tool auto-saves the full analysis context to your local storage, ensuring your knowledge base remains intact forever.
3.  **Grow:** Agents retrieve your past notes (RAG) to learn from previous successes and mistakes.
> *Your trading data belongs to you, forever.*

## ✨ Key Features
- **Dockerized Setup:** One-command deployment (`docker-compose up`).
- **Web Dashboard:** Interactive UI built with Streamlit.
- **🧠 Persistent Memory (RAG):** Syncs analysis reports with your local Markdown files (compatible with [Obsidian](https://obsidian.md), VS Code, etc.) for long-term retention.
- **✅ Fact Checker:** Physically validates news URLs to prevent hallucinations.
- **Debate Transcript:** Extracts key arguments into readable markdown.
- **Auto-Summary:** Generates structured AI summary reports (`_summary.md`).

## 🐳 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key
- A directory for storing Markdown notes (e.g., Obsidian Vault, or any folder)

### Installation & Run
1. **Clone the repository:**
   ```bash
   git clone https://github.com/jiwoomap/TradingAgents-Dashboard.git
   cd TradingAgents-Dashboard
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

   **Required Configuration:**
   - `LLM_PROVIDER=openai` - Currently only OpenAI is supported
   - `OPENAI_API_KEY` - Get your key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

   **Recommended (Optional):**
   - `ALPHA_VANTAGE_API_KEY` - **Highly recommended for better analysis quality!**
     - Provides more comprehensive stock data and significantly improves news data quality
     - Get a FREE API key at [alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)
     - Free tier has rate limits but is sufficient for most use cases
   - `OBSIDIAN_VAULT_PATH` - Path to your Markdown notes folder for persistent memory/RAG
     - Example: `/Users/yourname/Documents/MyTradingNotes`
     - Docker users: Use `/app/obsidian_vault` (mapped in docker-compose.yml)
     - Any folder with `.md` files works (Obsidian recommended for viewing)

3. **Run with Docker:**
   ```bash
   docker-compose up --build -d
   ```

4. **Access Dashboard:**
   Open [http://localhost:8501](http://localhost:8501) in your browser.

## 🛠️ Advanced Features

### ⏰ Scheduled Analysis (Background Scheduler)
Run automated analysis jobs continuously in the background, independent of the Streamlit web UI.

When running with Docker, the scheduler starts automatically! Just access the web UI and add your schedules.

**Key Features:**
- ✅ **Auto-start in Docker** - No manual setup needed
- 🔄 Runs independently of Streamlit app (won't stop when you close the browser)
- 💾 Persistent job storage (survives restarts)
- 🌍 Automatic timezone conversion (schedule in your local time, executes in UTC)
- 📝 Auto-saves reports to Obsidian vault
- 📊 Real-time progress tracking via status files

**How to use:**
1. Open the web UI at http://localhost:8501
2. Go to sidebar → "Schedule New Job"
3. Set your ticker, time, and parameters
4. Click "Add Schedule"
5. Jobs will run automatically at the scheduled time!
6. View results in "Scheduled Results" tab

### 🧠 Persistent Memory (RAG) & Knowledge Accumulation
Give your agents "Long-term Memory". This ensures that even if original news links rot or data is lost online, your personal knowledge base remains preserved and reusable.

**Any Markdown (`.md`) file works!** You don't strictly need Obsidian.
You can manage your trading simulation logs, strategy notes, and market insights in **any editor** (VS Code, Notepad, Obsidian). As you accumulate more notes, the agent becomes a **smarter simulation partner** tailored to your trading style.

1.  **Sync (Memorize):** Click `Sync Memories` to load `.md` notes from your mounted folder into the vector DB. The AI indexes your notes as "Situations" (Title/Context) and "Knowledge" (Content).
2.  **Retrieve (Recall):** During analysis, agents automatically search your local files for past market situations similar to the current one.
    *   *Example:* "Last time inflation rose while tech stocks fell, I noted that defensive sectors outperformed." -> Agents will recall this note and apply it to today's decision.
3.  **Auto-Save (Record):** Analysis reports (`_summary.md`, `_debate.md`) are automatically saved to your folder (`TradingAgents/Reports/`) for future reference.

### ✅ Fact Checker (URL Verification)
The enhanced Fact Checker agent now **physically pings** URLs cited in news reports.
- **Validates Sources:** Checks if the link returns 200 OK.
- **Anti-Bot Handling:** Treats 403 Forbidden as `VALID (Protected)` to avoid false positives.
- **Prevents Hallucinations:** Flags claims based on dead or non-existent links.

---

## 🗺️ Roadmap

- [ ] **Backtesting Module:** Validate agent strategies against historical data.
- [ ] **Multi-Model Support:** Integration with other AI APIs (Claude, Gemini, DeepSeek) and Local LLMs (Ollama).

## 🏗️ Architecture (Original)
This project wraps the **TradingAgents** framework, a multi-agent system that simulates a real-world trading firm.

- **Analyst Team:** Fundamentals, Sentiment, News, Technical Analysts.
- **Researcher Team:** Bull/Bear debate and consensus.
- **Trader & Risk Manager:** Final decision making.

## 🤝 Reference & Credit
This project is a UI enhancement and functional extension (Persistent Memory, RAG) based on the original **[TradingAgents](https://github.com/TauricResearch/TradingAgents)** framework.

Please cite the original work if you use this for research:
```bibtex
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework}, 
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138}, 
}
```

## 📜 License
Apache License 2.0
