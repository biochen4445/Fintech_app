"""
Fintech Stock Analysis Agent Server
Inspired by FinceptTerminal's 37 AI agents and CFA-level analytics.
Supports US and Taiwan (TWSE) markets via Yahoo Finance.
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf
import numpy as np
import json
import os
import traceback

app = Flask(__name__, static_folder=".")
CORS(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_get(info: dict, key: str, default=None):
    v = info.get(key, default)
    if v is None:
        return default
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return default
    return v


def pct(val):
    if val is None:
        return None
    return round(val * 100, 2)


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

def fetch_stock_data(ticker_str: str) -> dict:
    tk = yf.Ticker(ticker_str)
    info = tk.info or {}

    hist = tk.history(period="6mo")
    prices = []
    if not hist.empty:
        for dt, row in hist.iterrows():
            prices.append({
                "date": dt.strftime("%Y-%m-%d"),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

    current = safe_get(info, "currentPrice") or safe_get(info, "regularMarketPrice", 0)
    prev_close = safe_get(info, "previousClose") or safe_get(info, "regularMarketPreviousClose", 0)
    change = round(current - prev_close, 2) if current and prev_close else 0
    change_pct = round(change / prev_close * 100, 2) if prev_close else 0

    # Compute simple moving averages from history
    closes = [p["close"] for p in prices]
    sma50 = round(np.mean(closes[-50:]), 2) if len(closes) >= 50 else None
    sma200 = round(np.mean(closes[-200:]), 2) if len(closes) >= 200 else None

    # RSI (14-day)
    rsi = None
    if len(closes) >= 15:
        deltas = np.diff(closes[-15:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss != 0:
            rs = avg_gain / avg_loss
            rsi = round(100 - 100 / (1 + rs), 1)

    return {
        "ticker": ticker_str.upper(),
        "name": safe_get(info, "longName") or safe_get(info, "shortName", ticker_str),
        "sector": safe_get(info, "sector", "N/A"),
        "industry": safe_get(info, "industry", "N/A"),
        "currency": safe_get(info, "currency", "USD"),
        "exchange": safe_get(info, "exchange", ""),
        "price": current,
        "previousClose": prev_close,
        "change": change,
        "changePct": change_pct,
        "marketCap": safe_get(info, "marketCap"),
        "volume": safe_get(info, "volume"),
        "avgVolume": safe_get(info, "averageVolume"),
        "fiftyTwoWeekHigh": safe_get(info, "fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": safe_get(info, "fiftyTwoWeekLow"),
        "pe": safe_get(info, "trailingPE"),
        "forwardPe": safe_get(info, "forwardPE"),
        "peg": safe_get(info, "pegRatio"),
        "pb": safe_get(info, "priceToBook"),
        "ps": safe_get(info, "priceToSalesTrailing12Months"),
        "eps": safe_get(info, "trailingEps"),
        "forwardEps": safe_get(info, "forwardEps"),
        "roe": pct(safe_get(info, "returnOnEquity")),
        "roa": pct(safe_get(info, "returnOnAssets")),
        "profitMargin": pct(safe_get(info, "profitMargins")),
        "operatingMargin": pct(safe_get(info, "operatingMargins")),
        "grossMargin": pct(safe_get(info, "grossMargins")),
        "revenueGrowth": pct(safe_get(info, "revenueGrowth")),
        "earningsGrowth": pct(safe_get(info, "earningsGrowth")),
        "debtToEquity": safe_get(info, "debtToEquity"),
        "currentRatio": safe_get(info, "currentRatio"),
        "quickRatio": safe_get(info, "quickRatio"),
        "dividendYield": pct(safe_get(info, "dividendYield")),
        "payoutRatio": pct(safe_get(info, "payoutRatio")),
        "beta": safe_get(info, "beta"),
        "sma50": sma50,
        "sma200": sma200,
        "rsi": rsi,
        "analystRating": safe_get(info, "recommendationKey", "N/A"),
        "targetPrice": safe_get(info, "targetMeanPrice"),
        "history": prices,
    }


# ---------------------------------------------------------------------------
# Scoring Engine
# ---------------------------------------------------------------------------

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def score_valuation(d: dict) -> dict:
    score = 50
    reasons = []
    pe = d.get("pe")
    fpe = d.get("forwardPe")
    pb = d.get("pb")
    peg = d.get("peg")

    if pe is not None:
        if pe < 10:
            score += 20; reasons.append(f"Very low P/E ({pe:.1f}) — deep value territory")
        elif pe < 15:
            score += 12; reasons.append(f"Low P/E ({pe:.1f}) — attractive valuation")
        elif pe < 25:
            score += 0; reasons.append(f"Moderate P/E ({pe:.1f}) — fairly valued")
        elif pe < 40:
            score -= 10; reasons.append(f"High P/E ({pe:.1f}) — growth expectations priced in")
        else:
            score -= 20; reasons.append(f"Very high P/E ({pe:.1f}) — expensive by earnings")
    if fpe is not None and pe is not None and fpe < pe:
        score += 5; reasons.append(f"Forward P/E ({fpe:.1f}) lower than trailing — earnings improving")
    if pb is not None:
        if pb < 1:
            score += 10; reasons.append(f"P/B below 1 ({pb:.1f}) — trading below book value")
        elif pb < 3:
            score += 3
        elif pb > 10:
            score -= 8; reasons.append(f"High P/B ({pb:.1f})")
    if peg is not None:
        if peg < 1:
            score += 10; reasons.append(f"PEG < 1 ({peg:.1f}) — undervalued relative to growth")
        elif peg < 2:
            score += 3
        elif peg > 3:
            score -= 8; reasons.append(f"PEG > 3 ({peg:.1f}) — overpriced vs growth")
    return {"score": clamp(score), "reasons": reasons}


def score_growth(d: dict) -> dict:
    score = 50
    reasons = []
    rg = d.get("revenueGrowth")
    eg = d.get("earningsGrowth")
    if rg is not None:
        if rg > 30:
            score += 20; reasons.append(f"Strong revenue growth ({rg:.1f}%)")
        elif rg > 10:
            score += 10; reasons.append(f"Healthy revenue growth ({rg:.1f}%)")
        elif rg > 0:
            score += 3; reasons.append(f"Modest revenue growth ({rg:.1f}%)")
        else:
            score -= 15; reasons.append(f"Revenue declining ({rg:.1f}%)")
    if eg is not None:
        if eg > 30:
            score += 15; reasons.append(f"Excellent earnings growth ({eg:.1f}%)")
        elif eg > 10:
            score += 8; reasons.append(f"Solid earnings growth ({eg:.1f}%)")
        elif eg < 0:
            score -= 15; reasons.append(f"Earnings declining ({eg:.1f}%)")
    return {"score": clamp(score), "reasons": reasons}


def score_profitability(d: dict) -> dict:
    score = 50
    reasons = []
    roe = d.get("roe")
    pm = d.get("profitMargin")
    om = d.get("operatingMargin")
    if roe is not None:
        if roe > 20:
            score += 15; reasons.append(f"Excellent ROE ({roe:.1f}%) — superior capital efficiency")
        elif roe > 10:
            score += 7; reasons.append(f"Good ROE ({roe:.1f}%)")
        elif roe < 5:
            score -= 10; reasons.append(f"Low ROE ({roe:.1f}%)")
    if pm is not None:
        if pm > 20:
            score += 12; reasons.append(f"High profit margin ({pm:.1f}%)")
        elif pm > 10:
            score += 5
        elif pm < 0:
            score -= 15; reasons.append(f"Net loss (margin {pm:.1f}%)")
    if om is not None and om > 25:
        score += 5; reasons.append(f"Strong operating margin ({om:.1f}%)")
    return {"score": clamp(score), "reasons": reasons}


def score_health(d: dict) -> dict:
    score = 50
    reasons = []
    dte = d.get("debtToEquity")
    cr = d.get("currentRatio")
    if dte is not None:
        if dte < 30:
            score += 15; reasons.append(f"Very low debt-to-equity ({dte:.0f}) — strong balance sheet")
        elif dte < 80:
            score += 5; reasons.append(f"Manageable debt-to-equity ({dte:.0f})")
        elif dte > 200:
            score -= 15; reasons.append(f"High leverage (D/E {dte:.0f}) — financial risk")
    if cr is not None:
        if cr > 2:
            score += 10; reasons.append(f"Strong current ratio ({cr:.1f}) — excellent liquidity")
        elif cr > 1:
            score += 3
        else:
            score -= 10; reasons.append(f"Current ratio below 1 ({cr:.1f}) — liquidity concern")
    return {"score": clamp(score), "reasons": reasons}


def score_technicals(d: dict) -> dict:
    score = 50
    reasons = []
    price = d.get("price")
    sma50 = d.get("sma50")
    sma200 = d.get("sma200")
    rsi = d.get("rsi")
    hi = d.get("fiftyTwoWeekHigh")
    lo = d.get("fiftyTwoWeekLow")

    if price and sma50:
        if price > sma50:
            score += 8; reasons.append("Price above 50-day MA — short-term uptrend")
        else:
            score -= 8; reasons.append("Price below 50-day MA — short-term weakness")
    if price and sma200:
        if price > sma200:
            score += 8; reasons.append("Price above 200-day MA — long-term uptrend")
        else:
            score -= 8; reasons.append("Price below 200-day MA — long-term downtrend")
    if sma50 and sma200:
        if sma50 > sma200:
            score += 5; reasons.append("Golden cross (50-day > 200-day) — bullish signal")
        else:
            score -= 5; reasons.append("Death cross (50-day < 200-day) — bearish signal")
    if rsi is not None:
        if rsi > 70:
            score -= 10; reasons.append(f"RSI {rsi} — overbought territory")
        elif rsi < 30:
            score += 10; reasons.append(f"RSI {rsi} — oversold, potential bounce")
        else:
            reasons.append(f"RSI {rsi} — neutral range")
    if price and hi and lo and hi != lo:
        pos = (price - lo) / (hi - lo) * 100
        if pos > 90:
            reasons.append(f"Near 52-week high ({pos:.0f}% of range)")
        elif pos < 20:
            reasons.append(f"Near 52-week low ({pos:.0f}% of range)")
    return {"score": clamp(score), "reasons": reasons}


def score_dividends(d: dict) -> dict:
    score = 50
    reasons = []
    dy = d.get("dividendYield")
    pr = d.get("payoutRatio")
    if dy is not None:
        if dy > 5:
            score += 12; reasons.append(f"High dividend yield ({dy:.1f}%) — income opportunity")
        elif dy > 2:
            score += 8; reasons.append(f"Decent dividend yield ({dy:.1f}%)")
        elif dy > 0:
            score += 3; reasons.append(f"Small dividend yield ({dy:.1f}%)")
        else:
            reasons.append("No dividend")
    else:
        reasons.append("No dividend paid")
    if pr is not None:
        if 20 < pr < 60:
            score += 5; reasons.append(f"Healthy payout ratio ({pr:.0f}%) — sustainable")
        elif pr > 90:
            score -= 8; reasons.append(f"Very high payout ratio ({pr:.0f}%) — sustainability risk")
    return {"score": clamp(score), "reasons": reasons}


# ---------------------------------------------------------------------------
# Investor Agent Commentaries
# ---------------------------------------------------------------------------

def agent_buffett(d: dict, scores: dict) -> dict:
    pros, cons = [], []
    pe = d.get("pe")
    roe = d.get("roe")
    pm = d.get("profitMargin")
    dte = d.get("debtToEquity")
    dy = d.get("dividendYield")

    if roe and roe > 15:
        pros.append(f"Excellent ROE of {roe:.1f}% — a sign of a durable competitive advantage (economic moat).")
    elif roe and roe < 8:
        cons.append(f"ROE of {roe:.1f}% is below my threshold — limited pricing power or capital efficiency.")
    if pm and pm > 15:
        pros.append(f"Profit margin of {pm:.1f}% suggests the company has pricing power in its industry.")
    if pe and pe < 20:
        pros.append(f"P/E of {pe:.1f} is reasonable — I prefer buying wonderful companies at fair prices.")
    elif pe and pe > 35:
        cons.append(f"P/E of {pe:.1f} is rich. Even great businesses can be bad investments at the wrong price.")
    if dte and dte < 50:
        pros.append("Conservative balance sheet — manageable debt levels are essential for weathering downturns.")
    elif dte and dte > 150:
        cons.append(f"Debt-to-equity of {dte:.0f} concerns me. Leverage amplifies both gains and pain.")
    if dy and dy > 1:
        pros.append(f"Dividend yield of {dy:.1f}% rewards patient shareholders.")

    verdict = "BUY" if scores["overall"] >= 65 else "HOLD" if scores["overall"] >= 45 else "AVOID"
    summary = f"As a long-term value investor, I see this stock scoring {scores['overall']}/100. "
    if verdict == "BUY":
        summary += "The fundamentals suggest a quality business at a reasonable price — the kind I love to hold for decades."
    elif verdict == "HOLD":
        summary += "Decent business, but I'd want a better price or clearer moat before committing capital."
    else:
        summary += "The numbers don't excite me. I'll wait for a better opportunity — there's no penalty for patience."

    return {"name": "Warren Buffett", "style": "Value Investing", "emoji": "🏛️",
            "verdict": verdict, "summary": summary, "pros": pros, "cons": cons}


def agent_graham(d: dict, scores: dict) -> dict:
    pros, cons = [], []
    pe = d.get("pe")
    pb = d.get("pb")
    cr = d.get("currentRatio")
    dy = d.get("dividendYield")
    dte = d.get("debtToEquity")

    if pe and pe < 15:
        pros.append(f"P/E of {pe:.1f} meets my criterion of buying below 15x earnings.")
    elif pe and pe > 20:
        cons.append(f"P/E of {pe:.1f} exceeds my conservative threshold. The margin of safety is thin.")
    if pb and pb < 1.5:
        pros.append(f"Price-to-book of {pb:.1f} — trading near tangible asset value, a margin-of-safety characteristic.")
    elif pb and pb > 5:
        cons.append(f"P/B of {pb:.1f} is far above book value. Risk of permanent capital loss if earnings disappoint.")
    if cr and cr > 2:
        pros.append(f"Current ratio of {cr:.1f} — strong working capital position, the hallmark of a defensive investment.")
    elif cr and cr < 1:
        cons.append(f"Current ratio of {cr:.1f} — insufficient working capital buffer.")
    if dy and dy > 2:
        pros.append(f"Dividend yield of {dy:.1f}% provides a tangible return while you wait.")
    if dte and dte > 100:
        cons.append(f"Excessive debt (D/E: {dte:.0f}). I insist on financial conservatism.")

    verdict = "BUY" if scores["overall"] >= 60 and (pe and pe < 18) else "HOLD" if scores["overall"] >= 40 else "AVOID"
    summary = f"Applying my defensive investor criteria, this stock scores {scores['overall']}/100. "
    if verdict == "BUY":
        summary += "It meets several of my tests for a sound investment with adequate margin of safety."
    elif verdict == "HOLD":
        summary += "Some merits exist, but it doesn't fully satisfy my requirements for a defensive investment."
    else:
        summary += "Fails too many of my criteria. The intelligent investor must insist on adequate protection."

    return {"name": "Benjamin Graham", "style": "Defensive Value", "emoji": "📊",
            "verdict": verdict, "summary": summary, "pros": pros, "cons": cons}


def agent_lynch(d: dict, scores: dict) -> dict:
    pros, cons = [], []
    peg = d.get("peg")
    rg = d.get("revenueGrowth")
    eg = d.get("earningsGrowth")
    pe = d.get("pe")

    if peg and peg < 1:
        pros.append(f"PEG ratio of {peg:.1f} — growth at a reasonable price, exactly what I look for!")
    elif peg and peg > 2:
        cons.append(f"PEG of {peg:.1f} — you're overpaying for the growth rate.")
    if rg and rg > 20:
        pros.append(f"Revenue growing at {rg:.1f}% — this company is expanding its market presence.")
    elif rg and rg < 0:
        cons.append(f"Revenue shrinking ({rg:.1f}%) — the story may be deteriorating.")
    if eg and eg > 25:
        pros.append(f"Earnings surging {eg:.1f}% — the business is firing on all cylinders.")
    if pe and pe < 20 and rg and rg > 15:
        pros.append("Classic GARP opportunity — reasonable P/E with strong growth.")

    verdict = "BUY" if scores["overall"] >= 60 else "HOLD" if scores["overall"] >= 42 else "AVOID"
    summary = f"I always look for 'the story' behind a stock. This one scores {scores['overall']}/100. "
    if verdict == "BUY":
        summary += "The growth-at-a-reasonable-price math works here. Know what you own and why you own it!"
    elif verdict == "HOLD":
        summary += "Interesting story, but I'd want to see better growth numbers or a lower entry price."
    else:
        summary += "The story doesn't add up at this price. Never invest in a company before you've done your homework."

    return {"name": "Peter Lynch", "style": "Growth at Reasonable Price", "emoji": "🚀",
            "verdict": verdict, "summary": summary, "pros": pros, "cons": cons}


def agent_wood(d: dict, scores: dict) -> dict:
    pros, cons = [], []
    rg = d.get("revenueGrowth")
    eg = d.get("earningsGrowth")
    pe = d.get("pe")
    sector = d.get("sector", "")

    innovation_sectors = ["Technology", "Communication Services", "Healthcare"]
    if sector in innovation_sectors:
        pros.append(f"Operating in {sector} — a sector ripe for disruptive innovation and exponential growth.")
    if rg and rg > 25:
        pros.append(f"Revenue growth of {rg:.1f}% aligns with our 5-year compounding thesis.")
    elif rg and rg < 5:
        cons.append(f"Revenue growth of only {rg:.1f}% — not the disruptive trajectory we seek.")
    if eg and eg > 30:
        pros.append(f"Earnings growth of {eg:.1f}% — the flywheel is accelerating.")
    if pe and pe > 50:
        pros.append(f"High P/E ({pe:.1f}) is expected for disruptors — we invest on a 5-year horizon, not trailing earnings.")
    if pe and pe < 15:
        cons.append(f"Low P/E ({pe:.1f}) may signal a mature business, not the innovation curve we target.")

    verdict = "BUY" if rg and rg > 20 else "HOLD" if rg and rg > 5 else "AVOID"
    summary = f"Through the lens of disruptive innovation, this stock scores {scores['overall']}/100. "
    if verdict == "BUY":
        summary += "This fits our innovation-driven portfolio thesis. We're investing for a 5-year transformation."
    elif verdict == "HOLD":
        summary += "Some innovation potential, but the growth rate needs to accelerate for our conviction threshold."
    else:
        summary += "This looks more like an incumbent than a disruptor. We focus capital on paradigm-shifting companies."

    return {"name": "Cathie Wood", "style": "Disruptive Innovation", "emoji": "⚡",
            "verdict": verdict, "summary": summary, "pros": pros, "cons": cons}


def agent_risk(d: dict, scores: dict) -> dict:
    risks, mitigants = [], []
    beta = d.get("beta")
    dte = d.get("debtToEquity")
    cr = d.get("currentRatio")
    pe = d.get("pe")
    rsi = d.get("rsi")
    hi = d.get("fiftyTwoWeekHigh")
    price = d.get("price")

    if beta and beta > 1.5:
        risks.append(f"High beta ({beta:.2f}) — expect 50%+ more volatility than the broad market.")
    elif beta and beta < 0.7:
        mitigants.append(f"Low beta ({beta:.2f}) — defensive characteristics, less market sensitivity.")
    if dte and dte > 150:
        risks.append(f"Elevated leverage (D/E: {dte:.0f}) — vulnerable in credit tightening or downturn scenarios.")
    elif dte and dte < 50:
        mitigants.append(f"Conservative debt (D/E: {dte:.0f}) — financial resilience in stress scenarios.")
    if cr and cr < 1:
        risks.append(f"Current ratio {cr:.1f} — potential liquidity crunch if revenues decline.")
    if pe and pe > 50:
        risks.append(f"P/E of {pe:.1f} — significant multiple compression risk if growth disappoints.")
    if rsi and rsi > 75:
        risks.append(f"RSI at {rsi} — technically overbought, short-term pullback probable.")
    if price and hi and hi > 0:
        nearness = (price / hi) * 100
        if nearness > 95:
            risks.append(f"Trading within 5% of 52-week high — limited upside buffer.")
    if not risks:
        mitigants.append("No major red flags detected in current risk screening.")

    severity = "HIGH" if len(risks) >= 3 else "MODERATE" if len(risks) >= 1 else "LOW"
    summary = f"Risk assessment score: {scores['overall']}/100. "
    if severity == "HIGH":
        summary += "Multiple risk factors present. Position sizing should be conservative; consider hedging strategies."
    elif severity == "MODERATE":
        summary += "Some risk factors to monitor. Standard position sizing appropriate with stop-loss discipline."
    else:
        summary += "Risk profile is manageable. Fundamentals provide a reasonable safety cushion."

    return {"name": "Risk Analyst", "style": "Risk Management", "emoji": "🛡️",
            "verdict": severity, "summary": summary, "pros": mitigants, "cons": risks}


# ---------------------------------------------------------------------------
# Main Analysis Orchestrator
# ---------------------------------------------------------------------------

def analyze(ticker_str: str) -> dict:
    data = fetch_stock_data(ticker_str)

    val = score_valuation(data)
    gro = score_growth(data)
    pro = score_profitability(data)
    hlt = score_health(data)
    tec = score_technicals(data)
    div = score_dividends(data)

    overall = round(
        val["score"] * 0.20 +
        gro["score"] * 0.20 +
        pro["score"] * 0.20 +
        hlt["score"] * 0.15 +
        tec["score"] * 0.15 +
        div["score"] * 0.10
    )

    scores_map = {
        "overall": overall,
        "valuation": val["score"],
        "growth": gro["score"],
        "profitability": pro["score"],
        "health": hlt["score"],
        "technicals": tec["score"],
        "dividends": div["score"],
    }

    # Collect all bull / bear reasons
    all_reasons = []
    for cat_name, cat in [("Valuation", val), ("Growth", gro), ("Profitability", pro),
                           ("Health", hlt), ("Technicals", tec), ("Dividends", div)]:
        for r in cat["reasons"]:
            all_reasons.append({"category": cat_name, "text": r})

    bulls = [r for r in all_reasons if any(kw in r["text"].lower() for kw in
             ["excellent", "strong", "high", "good", "above", "golden", "low p/e", "low debt",
              "below book", "peg < 1", "healthy", "oversold", "decent", "attractive", "very low",
              "improving", "undervalued", "growth"])]
    bears = [r for r in all_reasons if any(kw in r["text"].lower() for kw in
             ["decline", "risk", "high p/e", "expensive", "below", "death", "overbought",
              "concern", "high leverage", "loss", "excessive", "thin", "overpriced",
              "shrinking", "insufficient", "very high p/e"])]

    agents = [
        agent_buffett(data, scores_map),
        agent_graham(data, scores_map),
        agent_lynch(data, scores_map),
        agent_wood(data, scores_map),
        agent_risk(data, scores_map),
    ]

    return {
        "success": True,
        "stock": data,
        "scores": scores_map,
        "scoreDetails": {
            "valuation": val,
            "growth": gro,
            "profitability": pro,
            "health": hlt,
            "technicals": tec,
            "dividends": div,
        },
        "bulls": bulls[:6],
        "bears": bears[:6],
        "agents": agents,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


@app.route("/api/analyze/<ticker>")
def api_analyze(ticker):
    try:
        result = analyze(ticker.strip())
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("[*] Fintech Stock Analysis Server starting...")
    print("    Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
