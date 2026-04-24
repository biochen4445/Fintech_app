[README.md](https://github.com/user-attachments/files/27042917/README.md)
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/Yahoo_Finance-API-7B1FA2" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
</p>

<h1 align="center">📊 FinAnalyzer — AI Stock Investment Analyzer</h1>

<p align="center">
  <strong>Multi-agent stock analysis with Bloomberg-terminal-style dark UI</strong><br/>
  Rule-based AI investor agents provide investment commentary on US &amp; Taiwan stocks
</p>

---

## Overview

**FinAnalyzer** is a full-stack stock analysis web application inspired by [FinceptTerminal](https://github.com/Fincept-Corporation/FinceptTerminal). Enter any US or Taiwan (TWSE) stock ticker and receive instant, multi-dimensional investment analysis with commentary from **5 AI investor personas**.

### Key Features

| Feature | Description |
|---------|-------------|
| **6-Dimension Scoring** | Valuation, Growth, Profitability, Financial Health, Technicals, Dividends |
| **5 Investor Agents** | Warren Buffett, Benjamin Graham, Peter Lynch, Cathie Wood, Risk Analyst |
| **Real-Time Data** | Live stock data via Yahoo Finance (prices, ratios, financials, technicals) |
| **Interactive Dashboard** | Score gauge, metric cards, bull/bear panels, 6-month price chart |
| **US & TW Markets** | Supports any Yahoo Finance ticker — `AAPL`, `TSLA`, `2330.TW`, `2317.TW`, etc. |

---

## Quick Start

### Prerequisites

- **Python 3.11+** — [Download](https://www.python.org/downloads/)

### Installation

```bash
# Clone or navigate to the project
cd Fintech

# Install dependencies
pip install -r requirements.txt

# Start the server
python server.py
```

Open **http://localhost:5000** in your browser.

### Usage

1. Enter a stock ticker in the search bar (e.g. `AAPL`, `2330.TW`)
2. Click **Analyze** or press Enter
3. View the comprehensive investment analysis:
   - Overall score (0–100) with animated gauge
   - Dimension breakdown (Valuation, Growth, Profitability, Health, Technicals, Dividends)
   - Bull vs. Bear factor summary
   - 6-month historical price chart
   - Commentary from 5 AI investor agents

---

## AI Investor Agents

Each agent evaluates the stock through a distinct investment philosophy:

| Agent | Style | Focus |
|-------|-------|-------|
| 🏛️ **Warren Buffett** | Value Investing | Competitive moats, ROE, long-term compounding |
| 📊 **Benjamin Graham** | Defensive Value | Margin of safety, P/E < 15, book value, liquidity |
| 🚀 **Peter Lynch** | Growth at Reasonable Price | PEG ratio, revenue growth, "know what you own" |
| ⚡ **Cathie Wood** | Disruptive Innovation | Revenue acceleration, sector disruption, 5-year thesis |
| 🛡️ **Risk Analyst** | Risk Management | Beta, leverage, RSI, downside scenarios |

Each agent outputs a **verdict** (BUY / HOLD / AVOID), a **summary**, and specific **pros/cons** backed by the stock's actual financial data.

---

## Scoring Engine

The overall score (0–100) is a weighted composite:

| Dimension | Weight | Metrics Used |
|-----------|--------|--------------|
| Valuation | 20% | P/E, Forward P/E, P/B, PEG |
| Growth | 20% | Revenue growth, Earnings growth |
| Profitability | 20% | ROE, ROA, Profit margin, Operating margin |
| Financial Health | 15% | Debt-to-equity, Current ratio, Quick ratio |
| Technicals | 15% | SMA 50/200, RSI, 52-week position |
| Dividends | 10% | Dividend yield, Payout ratio |

| Score Range | Rating |
|-------------|--------|
| 70–100 | 🟢 Bullish |
| 45–69 | 🟡 Neutral |
| 0–44 | 🔴 Bearish |

---

## Project Structure

```
Fintech/
├── server.py          # Flask API + scoring engine + 5 investor agents
├── index.html         # Dashboard HTML layout
├── style.css          # Bloomberg-terminal dark theme (JetBrains Mono + DM Sans)
├── app.js             # Frontend logic, Chart.js, dynamic rendering
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, Flask, yfinance, pandas, numpy |
| **Frontend** | Vanilla HTML/CSS/JS, Chart.js 4.x |
| **Data Source** | Yahoo Finance API (via yfinance) |
| **Design** | Bloomberg-terminal dark theme, glassmorphism, JetBrains Mono |

---

## API Reference

### `GET /api/analyze/<ticker>`

Analyze a stock and return full scoring + agent commentary.

**Example:**

```bash
curl http://localhost:5000/api/analyze/AAPL
```

**Response:**

```json
{
  "success": true,
  "stock": {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "price": 273.43,
    "pe": 33.2,
    "roe": 152.0,
    ...
  },
  "scores": {
    "overall": 58,
    "valuation": 37,
    "growth": 68,
    "profitability": 82,
    "health": 40,
    "technicals": 58,
    "dividends": 62
  },
  "agents": [ ... ],
  "bulls": [ ... ],
  "bears": [ ... ]
}
```

---

## Supported Markets

| Market | Ticker Format | Examples |
|--------|--------------|----------|
| US (NYSE/NASDAQ) | `SYMBOL` | `AAPL`, `TSLA`, `MSFT`, `NVDA` |
| Taiwan (TWSE) | `NUMBER.TW` | `2330.TW`, `2317.TW`, `2454.TW` |

Any ticker supported by Yahoo Finance will work.

---

## Disclaimer

> **This tool is for educational and informational purposes only.** It does not constitute financial advice. The AI agents use rule-based analysis on publicly available data — they are not real financial advisors. Always do your own research and consult a qualified financial professional before making investment decisions.

---

## Acknowledgements

- Inspired by [FinceptTerminal](https://github.com/Fincept-Corporation/FinceptTerminal) — an open-source financial intelligence platform with 37 AI agents and CFA-level analytics
- Stock data provided by [Yahoo Finance](https://finance.yahoo.com/) via [yfinance](https://github.com/ranaroussi/yfinance)
- Charts rendered with [Chart.js](https://www.chartjs.org/)

---

## License

MIT License — free for personal and educational use.
