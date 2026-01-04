# 📈 TradingAgents-Dashboard

> 🚀 **A Dockerized web dashboard for [TradingAgents](https://github.com/TauricResearch/TradingAgents).**  
> Features improved UI/UX, real-time logging, and easy deployment with Docker.

<details>
<summary>📸 <strong>Click to view Dashboard Screenshot</strong></summary>
<p align="center">
  <img src="assets/dashboard_sample.png" alt="Dashboard Screenshot" width="100%">
  <br>
  <em>Real-time analysis and logging in the web dashboard</em>
</p>
</details>

## ✨ Key Features
- **Dockerized Setup:** One-command deployment using Docker Compose.
- **Web Dashboard:** Interactive UI built with Streamlit for easy ticker/date selection.
- **Real-time Logging:** View internal agent thoughts and debates directly in the browser.
- **Persistent Logs:** Analysis logs are automatically saved to `logs/YYYY-MM-DD/TICKER/`.
- **Debate Transcript:** Extracts specific analyst discussions into a readable `_debate.md` file.
- **Auto-Summary:** Generates and saves a structured AI summary report (`_summary.md`) alongside the logs.
- **✅ Fact Checker with URL Verification:** Automatically verifies if cited news URLs are physically accessible and valid (prevents hallucinations).
- **🧠 Obsidian Memory Integration:** Syncs your analysis reports with an Obsidian Vault for long-term memory and knowledge retrieval.

## 🐳 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key
- Alpha Vantage API Key (Optional, but recommended for detailed data)

### Installation & Run
1. **Clone the repository:**
   ```bash
   git clone https://github.com/jiwoomap/TradingAgents-Dashboard.git
   cd TradingAgents-Dashboard
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys:
   # OPENAI_API_KEY=sk-... (Required)
   # ALPHA_VANTAGE_API_KEY=... (Optional - Defaults to yfinance/Google if missing)
   ```

3. **(Optional) Mount Obsidian Vault:**
   To use the **Memory Integration** feature, you can either manually mount the volume in `docker-compose.yml` or simply add your local path to the `.env` file.

   **Method A: Using .env (Recommended)**
   Add your local Obsidian Vault absolute path to `.env`:
   ```bash
   OBSIDIAN_VAULT_PATH="/Users/yourname/Documents/ObsidianVault"
   ```

   **Method B: Manual Docker Volume**
   Edit `docker-compose.yml`:
   ```yaml
   services:
     trading-agents:
       volumes:
         # ... existing volumes ...
         - /Users/yourname/Documents/ObsidianVault:/app/obsidian_vault
   ```

4. **Run with Docker:**
   ```bash
   docker-compose up --build -d
   ```

5. **Access Dashboard:**
   Open [http://localhost:8501](http://localhost:8501) in your browser.

## 🚀 Roadmap
You can easily run this yourself using Docker. I plan to update the UI whenever I have free time.

The **next milestone** is to build a **"Watchlist Dashboard"** where you can set up your favorite stocks and view them all at a glance.

---

## 🛠️ Advanced Features

### ✅ Fact Checker (URL Verification)
The enhanced Fact Checker agent now **physically pings** URLs cited in news reports.
- **Validates Sources:** Checks if the link returns 200 OK.
- **Anti-Bot Handling:** Treats 403 Forbidden as `VALID (Protected)` to avoid false positives on sites like Bloomberg or WSJ.
- **Prevents Hallucinations:** Flags claims based on dead or non-existent links.

### 🧠 Obsidian Integration (Long-term Memory)
Connect your Obsidian Vault to give the agents "Long-term Memory". This allows the AI to learn from your past notes and trading journals.

1. **Sync (Memorize):** Click `Sync Memories` in the dashboard to load `.md` notes from your vault into the vector DB. The AI indexes your notes as "Situations" (Title/Context) and "Knowledge" (Content).
2. **Retrieve (Recall):** During analysis, the agents automatically search your vault for past market situations similar to the current one.
   - *Example:* "Last time inflation rose while tech stocks fell, I noted that defensive sectors outperformed." -> Agents will see this note and apply it to today's decision.
3. **Auto-Save (Record):** Analysis reports (`_summary.md`, `_debate.md`) are automatically saved to `YourVault/TradingAgents/Reports/` for future reference.


---

## 🏗️ Architecture (Original)
This project wraps the **TradingAgents** framework, a multi-agent system that simulates a real-world trading firm.

<details>
<summary>Click to see architecture diagram</summary>
<p align="center">
  <img src="assets/schema.png" style="width: 100%; height: auto;">
</p>
</details>

- **Analyst Team:** Fundamentals, Sentiment, News, Technical Analysts.
- **Researcher Team:** Bull/Bear debate and consensus.
- **Trader & Risk Manager:** Final decision making.

## 🤝 Reference & Credit
This project is a fork and UI enhancement of **[TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)**.

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
