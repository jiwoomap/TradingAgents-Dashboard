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
- **Auto-Summary:** Generates and saves a structured AI summary report (`_summary.md`) alongside the logs.

## 🐳 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key & Alpha Vantage API Key

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
   # OPENAI_API_KEY=sk-...
   # ALPHA_VANTAGE_API_KEY=...
   ```

3. **Run with Docker:**
   ```bash
   docker-compose up -d
   ```

4. **Access Dashboard:**
   Open [http://localhost:8501](http://localhost:8501) in your browser.

## 🚀 Roadmap
You can easily run this yourself using Docker. I plan to update the UI whenever I have free time.

The **next milestone** is to build a **"Watchlist Dashboard"** where you can set up your favorite stocks and view them all at a glance.

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
