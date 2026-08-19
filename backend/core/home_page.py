"""
home_page.py — Pre-dashboard home page for Startup Blueprint Generator.
Sections:
  1. Welcome hero + quick actions
  2. Start Blueprint (navigates to dashboard)
  3. Startup School (beginner resources)
  4. Doubt Solver Agent (basic Q&A)
  5. Startup Calculators (Burn Rate, CAC/LTV, Valuation, Break-even, Runway)
"""

from __future__ import annotations
import streamlit as st
import json


# ══════════════════════════════════════════════════════════════════════════════
# STYLES
# ══════════════════════════════════════════════════════════════════════════════

HOME_CSS = """
<style>
/* ── Home Hero ── */
.home-hero {
    background: linear-gradient(135deg,rgba(15,98,254,0.08) 0%,rgba(105,41,196,0.06) 50%,rgba(16,185,129,0.04) 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 24px;
    padding: 3rem 2.5rem 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.home-hero::before {
    content:'';
    position:absolute;top:-40%;right:-10%;
    width:55%;height:140%;
    background:radial-gradient(ellipse,rgba(105,41,196,0.08) 0%,transparent 65%);
    pointer-events:none;
}
.home-hero-title {
    font-size: 2.6rem;
    font-weight: 900;
    letter-spacing: -0.04em;
    line-height: 1.1;
    background: linear-gradient(135deg,#ffffff 0%,#93c5fd 40%,#a78bfa 70%,#34d399 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.6rem;
}
.home-hero-sub {
    font-size: 0.95rem;
    color: #64748b;
    line-height: 1.65;
    max-width: 560px;
    margin-bottom: 1.4rem;
}

/* ── Feature Cards ── */
.feat-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    padding: 1.4rem 1.5rem;
    height: 100%;
    transition: border-color 0.25s, background 0.25s, transform 0.2s;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}
.feat-card:hover {
    border-color: rgba(96,165,250,0.3);
    background: rgba(96,165,250,0.03);
    transform: translateY(-2px);
}
.feat-card-icon {
    font-size: 2rem;
    margin-bottom: 0.7rem;
    display: block;
}
.feat-card-title {
    font-size: 1rem;
    font-weight: 800;
    color: #f1f5f9;
    margin-bottom: 0.35rem;
    letter-spacing: -0.015em;
}
.feat-card-desc {
    font-size: 0.78rem;
    color: #64748b;
    line-height: 1.6;
}
.feat-card-tag {
    display: inline-block;
    margin-top: 0.75rem;
    font-size: 0.67rem;
    font-weight: 700;
    padding: 2px 10px;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── Resource Cards ── */
.resource-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.065);
    border-radius: 14px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    transition: background 0.2s, border-color 0.2s;
    text-decoration: none;
}
.resource-card:hover {
    background: rgba(15,98,254,0.05);
    border-color: rgba(15,98,254,0.2);
}
.resource-icon {
    font-size: 1.3rem;
    flex-shrink: 0;
    margin-top: 0.1rem;
}
.resource-title {
    font-size: 0.86rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 0.2rem;
    line-height: 1.4;
}
.resource-desc {
    font-size: 0.74rem;
    color: #64748b;
    line-height: 1.5;
}
.resource-tag {
    font-size: 0.65rem;
    font-weight: 700;
    padding: 1px 8px;
    border-radius: 8px;
    margin-top: 0.3rem;
    display: inline-block;
}

/* ── Calc Cards ── */
.calc-result {
    background: linear-gradient(135deg,rgba(15,98,254,0.08),rgba(105,41,196,0.06));
    border: 1px solid rgba(15,98,254,0.2);
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    margin-top: 1rem;
    text-align: center;
}
.calc-result-val {
    font-size: 1.9rem;
    font-weight: 900;
    background: linear-gradient(135deg,#60a5fa,#a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.03em;
}
.calc-result-label {
    font-size: 0.72rem;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-top: 0.2rem;
}
.calc-insight {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-top: 0.5rem;
    line-height: 1.6;
}

/* ── Chat Bubbles ── */
.chat-user {
    background: rgba(15,98,254,0.12);
    border: 1px solid rgba(15,98,254,0.2);
    border-radius: 16px 16px 4px 16px;
    padding: 0.65rem 1rem;
    margin: 0.4rem 0 0.4rem 3rem;
    font-size: 0.85rem;
    color: #e2e8f0;
    line-height: 1.6;
}
.chat-bot {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px 16px 16px 4px;
    padding: 0.65rem 1rem;
    margin: 0.4rem 3rem 0.4rem 0;
    font-size: 0.85rem;
    color: #cbd5e1;
    line-height: 1.7;
}
.chat-bot-header {
    font-size: 0.68rem;
    font-weight: 700;
    color: #a78bfa;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.35rem;
}
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
# DOUBT SOLVER AGENT
# ══════════════════════════════════════════════════════════════════════════════

DOUBT_SYSTEM = """You are a friendly startup mentor helping beginners understand startup concepts.
Keep answers concise (3-5 sentences), use simple language, and always include a real-world example from India where possible.
Format: Brief direct answer, then one example, then one actionable tip.
Never use jargon without explaining it."""

QUICK_QUESTIONS = [
    "What is a startup incubator?",
    "What does GTM strategy mean?",
    "What is CAC and LTV?",
    "Explain burn rate simply",
    "What is a term sheet?",
    "What is product-market fit?",
    "What does bootstrapping mean?",
    "What is a pivot in startups?",
]

def _ask_doubt(question: str, groq_client) -> str:
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": DOUBT_SYSTEM},
                {"role": "user", "content": question},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Sorry, couldn't get an answer right now. Error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# CALCULATORS
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_inr(val: float) -> str:
    if val >= 1_00_00_000:
        return f"₹{val/1_00_00_000:.2f} Cr"
    elif val >= 1_00_000:
        return f"₹{val/1_00_000:.2f} L"
    elif val >= 1_000:
        return f"₹{val/1_000:.1f}K"
    return f"₹{val:.0f}"

def _fmt_months(m: float) -> str:
    if m >= 12:
        return f"{m/12:.1f} years"
    return f"{m:.1f} months"


def _calc_burn_rate():
    st.markdown("#### 🔥 Burn Rate & Runway Calculator")
    st.markdown('<div style="font-size:0.8rem;color:#64748b;margin-bottom:1rem">How long will your money last?</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        cash = st.number_input("Cash in Bank (₹)", min_value=0, value=5000000, step=100000, key="br_cash", format="%d")
        monthly_revenue = st.number_input("Monthly Revenue (₹)", min_value=0, value=0, step=10000, key="br_rev", format="%d")
    with c2:
        monthly_expenses = st.number_input("Monthly Expenses (₹)", min_value=1, value=500000, step=10000, key="br_exp", format="%d")
        target_month = st.number_input("Target Runway (months)", min_value=1, value=18, key="br_target")

    net_burn = monthly_expenses - monthly_revenue
    runway = cash / net_burn if net_burn > 0 else float('inf')
    cash_needed = (target_month * net_burn) - cash if net_burn > 0 else 0

    st.markdown(
        f'<div class="calc-result">'
        f'<div class="calc-result-val">{_fmt_months(runway) if runway != float("inf") else "♾️ Profitable"}</div>'
        f'<div class="calc-result-label">Current Runway</div>'
        f'<div style="display:flex;gap:1.5rem;justify-content:center;margin-top:0.75rem">'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:#f87171">{_fmt_inr(net_burn)}/mo</div><div style="font-size:0.68rem;color:#64748b">Net Burn</div></div>'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:{"#34d399" if cash_needed<=0 else "#f59e0b"}">{_fmt_inr(max(0,cash_needed))}</div><div style="font-size:0.68rem;color:#64748b">Extra needed for {target_month}mo runway</div></div>'
        f'</div>'
        f'<div class="calc-insight">{"⚠️ Your runway is critical — start fundraising immediately!" if runway < 6 else "✅ Good runway. Use this time to hit key milestones before next raise." if runway < 18 else "💪 Strong runway. Focus on growth and metrics."}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def _calc_cac_ltv():
    st.markdown("#### 📊 CAC / LTV Calculator")
    st.markdown('<div style="font-size:0.8rem;color:#64748b;margin-bottom:1rem">Are your unit economics healthy?</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        marketing_spend = st.number_input("Monthly Marketing Spend (₹)", min_value=0, value=100000, step=5000, key="cac_spend", format="%d")
        new_customers = st.number_input("New Customers/Month", min_value=1, value=50, key="cac_cust")
        avg_revenue = st.number_input("Avg Monthly Revenue per Customer (₹)", min_value=1, value=2000, key="cac_rev", format="%d")
    with c2:
        gross_margin = st.slider("Gross Margin %", 0, 100, 70, key="cac_margin")
        avg_lifespan = st.number_input("Avg Customer Lifespan (months)", min_value=1, value=24, key="cac_life")
        churn = st.slider("Monthly Churn Rate %", 0, 100, 5, key="cac_churn")

    cac = marketing_spend / new_customers if new_customers > 0 else 0
    ltv = (avg_revenue * (gross_margin/100)) / (churn/100) if churn > 0 else avg_revenue * avg_lifespan * (gross_margin/100)
    ratio = ltv / cac if cac > 0 else 0
    payback = cac / (avg_revenue * (gross_margin/100)) if avg_revenue > 0 else 0

    ratio_color = "#34d399" if ratio >= 3 else "#f59e0b" if ratio >= 1 else "#f87171"
    st.markdown(
        f'<div class="calc-result">'
        f'<div class="calc-result-val">LTV:CAC = {ratio:.1f}x</div>'
        f'<div class="calc-result-label">Unit Economics Ratio</div>'
        f'<div style="display:flex;gap:1.5rem;justify-content:center;margin-top:0.75rem">'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:#f87171">{_fmt_inr(cac)}</div><div style="font-size:0.68rem;color:#64748b">CAC</div></div>'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:#34d399">{_fmt_inr(ltv)}</div><div style="font-size:0.68rem;color:#64748b">LTV</div></div>'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:#60a5fa">{payback:.1f} mo</div><div style="font-size:0.68rem;color:#64748b">Payback Period</div></div>'
        f'</div>'
        f'<div class="calc-insight">{"🚨 LTV:CAC below 1 — you lose money on every customer. Fix pricing or reduce CAC." if ratio < 1 else "⚠️ LTV:CAC between 1-3 — marginal. Aim for 3x+ before scaling." if ratio < 3 else "✅ Healthy unit economics! LTV:CAC ≥ 3x means you can scale profitably."}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def _calc_valuation():
    st.markdown("#### 💎 Startup Valuation Estimator")
    st.markdown('<div style="font-size:0.8rem;color:#64748b;margin-bottom:1rem">Rough pre-money valuation across 3 methods</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        arr = st.number_input("Annual Recurring Revenue - ARR (₹)", min_value=0, value=1000000, step=100000, key="val_arr", format="%d")
        sector = st.selectbox("Sector", ["SaaS","Fintech","Edtech","Healthtech","E-commerce","Agritech","Other"], key="val_sector")
        stage = st.selectbox("Stage", ["Idea","Pre-seed","Seed","Series A"], key="val_stage")
    with c2:
        growth_rate = st.slider("YoY Growth Rate %", 0, 500, 100, key="val_growth")
        tam = st.number_input("TAM - Total Addressable Market (₹)", min_value=0, value=100_00_00_000, step=10_00_00_000, key="val_tam", format="%d")

    # Revenue multiple by sector
    multiples = {"SaaS": 8, "Fintech": 6, "Edtech": 5, "Healthtech": 7, "E-commerce": 3, "Agritech": 4, "Other": 5}
    base_multiple = multiples.get(sector, 5)
    growth_bonus = min(growth_rate / 100, 3)
    adjusted_multiple = base_multiple + growth_bonus

    # Stage premium
    stage_premium = {"Idea": 0.3, "Pre-seed": 0.5, "Seed": 1.0, "Series A": 1.5}.get(stage, 1.0)

    rev_val = arr * adjusted_multiple * stage_premium if arr > 0 else 0
    tam_val = tam * 0.01 * stage_premium  # 1% TAM capture
    scorecard_val = (rev_val + tam_val) / 2

    st.markdown(
        f'<div class="calc-result">'
        f'<div class="calc-result-val">{_fmt_inr(scorecard_val)}</div>'
        f'<div class="calc-result-label">Estimated Pre-Money Valuation</div>'
        f'<div style="display:flex;gap:1.5rem;justify-content:center;margin-top:0.75rem">'
        f'<div><div style="font-size:0.82rem;font-weight:700;color:#60a5fa">{_fmt_inr(rev_val)}</div><div style="font-size:0.65rem;color:#64748b">Revenue Multiple ({adjusted_multiple:.1f}x ARR)</div></div>'
        f'<div><div style="font-size:0.82rem;font-weight:700;color:#a78bfa">{_fmt_inr(tam_val)}</div><div style="font-size:0.65rem;color:#64748b">TAM-based (1% capture)</div></div>'
        f'</div>'
        f'<div class="calc-insight">⚠️ These are rough estimates. Actual valuation depends on team, traction, and market conditions. Use for internal planning only.</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def _calc_breakeven():
    st.markdown("#### ⚖️ Break-Even Calculator")
    st.markdown('<div style="font-size:0.8rem;color:#64748b;margin-bottom:1rem">When does your startup become profitable?</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fixed_costs = st.number_input("Monthly Fixed Costs (₹)", min_value=0, value=300000, step=10000, key="be_fixed", format="%d")
        price_per_unit = st.number_input("Revenue per Customer/Unit (₹)", min_value=1, value=5000, step=100, key="be_price", format="%d")
    with c2:
        variable_cost = st.number_input("Variable Cost per Customer/Unit (₹)", min_value=0, value=1000, step=100, key="be_var", format="%d")
        current_customers = st.number_input("Current Monthly Customers", min_value=0, value=20, key="be_curr")

    contribution_margin = price_per_unit - variable_cost
    breakeven_units = fixed_costs / contribution_margin if contribution_margin > 0 else float('inf')
    current_profit = (contribution_margin * current_customers) - fixed_costs
    gap = breakeven_units - current_customers

    st.markdown(
        f'<div class="calc-result">'
        f'<div class="calc-result-val">{breakeven_units:.0f} customers</div>'
        f'<div class="calc-result-label">Break-Even Point</div>'
        f'<div style="display:flex;gap:1.5rem;justify-content:center;margin-top:0.75rem">'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:#{"34d399" if current_profit>=0 else "f87171"}">{_fmt_inr(abs(current_profit))}</div><div style="font-size:0.68rem;color:#64748b">{"Monthly Profit" if current_profit>=0 else "Monthly Loss"}</div></div>'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:#f59e0b">{_fmt_inr(contribution_margin)}</div><div style="font-size:0.68rem;color:#64748b">Contribution Margin/unit</div></div>'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:#60a5fa">{max(0, gap):.0f}</div><div style="font-size:0.68rem;color:#64748b">More customers needed</div></div>'
        f'</div>'
        f'<div class="calc-insight">{"🎉 You are already profitable! Focus on scaling." if current_profit >= 0 else f"You need {max(0,gap):.0f} more customers to break even. At current growth, focus on reducing fixed costs or increasing price."}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def _calc_fundraise():
    st.markdown("#### 🎯 Fundraising Need Calculator")
    st.markdown('<div style="font-size:0.8rem;color:#64748b;margin-bottom:1rem">How much should you raise in your next round?</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        monthly_burn = st.number_input("Monthly Burn Rate (₹)", min_value=1, value=500000, step=50000, key="fr_burn", format="%d")
        runway_needed = st.slider("Runway Needed (months)", 12, 36, 18, key="fr_runway")
        milestones_cost = st.number_input("Cost to Hit Key Milestones (₹)", min_value=0, value=2000000, step=100000, key="fr_mile", format="%d")
    with c2:
        current_cash = st.number_input("Current Cash (₹)", min_value=0, value=500000, step=100000, key="fr_cash", format="%d")
        buffer_pct = st.slider("Safety Buffer %", 10, 50, 20, key="fr_buf")
        dilution = st.slider("Acceptable Dilution %", 5, 40, 20, key="fr_dil")

    base_needed = (monthly_burn * runway_needed) + milestones_cost - current_cash
    with_buffer = base_needed * (1 + buffer_pct/100)
    raise_amount = max(0, with_buffer)
    post_money = raise_amount / (dilution/100) if dilution > 0 else 0
    pre_money = post_money - raise_amount

    st.markdown(
        f'<div class="calc-result">'
        f'<div class="calc-result-val">{_fmt_inr(raise_amount)}</div>'
        f'<div class="calc-result-label">Recommended Raise Amount</div>'
        f'<div style="display:flex;gap:1.5rem;justify-content:center;margin-top:0.75rem">'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:#60a5fa">{_fmt_inr(pre_money)}</div><div style="font-size:0.68rem;color:#64748b">Implied Pre-Money Valuation</div></div>'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:#a78bfa">{dilution}%</div><div style="font-size:0.68rem;color:#64748b">Equity Given Away</div></div>'
        f'<div><div style="font-size:0.9rem;font-weight:700;color:#34d399">{runway_needed} mo</div><div style="font-size:0.68rem;color:#64748b">Runway Achieved</div></div>'
        f'</div>'
        f'<div class="calc-insight">Raise {_fmt_inr(raise_amount)} to give yourself {runway_needed} months of runway with a {buffer_pct}% safety buffer. This implies a pre-money valuation of {_fmt_inr(pre_money)}.</div>'
        f'</div>',
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# RESOURCES DATA
# ══════════════════════════════════════════════════════════════════════════════

RESOURCES = {
    "📖 Core Concepts": [
        {"icon": "🏗️", "title": "What is a Startup?", "desc": "Difference between a startup, SME, and business. Why startups aim for scale.", "tag": "Beginner", "tag_color": "#34d399", "url": "https://youtu.be/0lJKucu6HJc"},
        {"icon": "🗺️", "title": "Business Model Canvas (BMC)", "desc": "The 9 building blocks every startup needs. With Indian examples.", "tag": "Beginner", "tag_color": "#34d399", "url": "https://youtu.be/IP0cUBWTgpY"},
        {"icon": "💡", "title": "Product-Market Fit (PMF)", "desc": "How to know when your product is actually solving a real problem.", "tag": "Core", "tag_color": "#60a5fa", "url": "https://youtu.be/0LNQxT9LvM0"},
        {"icon": "🎯", "title": "Go-To-Market Strategy", "desc": "How to launch your product and acquire your first 100 customers.", "tag": "Core", "tag_color": "#60a5fa", "url": "https://youtu.be/zL9w2compbc"},
    ],
    "💰 Funding & Finance": [
        {"icon": "🌱", "title": "How Startup Funding Works", "desc": "From bootstrapping to Series A — what each stage means and what investors expect.", "tag": "Finance", "tag_color": "#f59e0b", "url": "https://youtu.be/677ZtSMr4-4"},
        {"icon": "🏛️", "title": "Startup India & Govt Schemes", "desc": "DPIIT registration, Seed Fund Scheme, SIDBI, AIM — the complete guide for Indian founders.", "tag": "India-specific", "tag_color": "#a78bfa", "url": "https://www.startupindia.gov.in/"},
        {"icon": "📊", "title": "Burn Rate & Runway Explained", "desc": "What burn rate means, how to calculate runway, and when to fundraise.", "tag": "Finance", "tag_color": "#f59e0b", "url": "https://youtu.be/qnvCq-8XDZE"},
        {"icon": "🤝", "title": "What is a Term Sheet?", "desc": "Every clause explained in simple language. Know what you're signing.", "tag": "Advanced", "tag_color": "#f87171", "url": "https://youtu.be/Zr-zrMtRfYo"},
    ],
    "🏢 Ecosystem": [
        {"icon": "🐣", "title": "Incubators vs Accelerators", "desc": "What's the difference? Which one is right for your startup stage?", "tag": "Ecosystem", "tag_color": "#34d399", "url": "https://youtu.be/Jx5FJdl2H9E"},
        {"icon": "👼", "title": "Angel Investors vs VCs", "desc": "Who invests at what stage, how they think, and what they look for.", "tag": "Ecosystem", "tag_color": "#34d399", "url": "https://youtu.be/9ZPqWRaDCFk"},
        {"icon": "🦄", "title": "India's Unicorn Ecosystem", "desc": "How Flipkart, Zepto, Razorpay built billion-dollar companies from India.", "tag": "Inspiration", "tag_color": "#60a5fa", "url": "https://inc42.com/unicorn-tracker/"},
        {"icon": "📋", "title": "Cap Table Basics", "desc": "What a capitalization table is and why it matters from Day 1.", "tag": "Advanced", "tag_color": "#f87171", "url": "https://youtu.be/pPJLkjR3Nqo"},
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ══════════════════════════════════════════════════════════════════════════════

def render_home_page(user: dict, groq_client) -> None:
    st.markdown(HOME_CSS, unsafe_allow_html=True)
    # Compute display name first
    raw_name = user.get("name", "") or user.get("email", "Founder")
    if "@" in raw_name:
        raw_name = raw_name.split("@")[0]
    name = raw_name.split()[0].capitalize()

    # ── Topbar ────────────────────────────────────────────────────────────────
    t1, t2, t3, t4 = st.columns([4, 3, 2, 1])
    with t1:
        st.markdown(
            '<div class="nav-logo"><span class="nav-logo-icon">🚀</span>Startup Blueprint Generator</div>',
            unsafe_allow_html=True,
        )
    with t2:
        st.markdown(
            '<div style="padding-top:0.35rem">'
            '<span class="badge badge-ibm">IBM Granite 4.0</span>'
            '<span class="badge badge-groq">Groq Llama 3.3</span>'
            '<span class="badge badge-gemini">✨ Gemini</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with t3:
        st.markdown(
            f'<div style="text-align:right;padding-top:0.4rem">'
            f'<span class="user-chip">👤 {name}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with t4:
        if st.button("Sign Out", key="home_signout", type="secondary"):
            for k in ["logged_in", "user", "page", "blueprints", "current_blueprint"]:
                st.session_state[k] = {
                    "logged_in": False, "user": None, "page": "login",
                    "blueprints": [], "current_blueprint": None,
                }[k]
            st.session_state.mentor_session = None
            st.session_state.mentor_messages_ui = []
            st.rerun()
    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Hero ──────────────────────────────────────────────────────────────────
    raw_name = user.get("name", "") or user.get("email", "Founder")
    # If name looks like an email, use the part before @
    if "@" in raw_name:
        raw_name = raw_name.split("@")[0]
    name = raw_name.split()[0].capitalize()
    st.markdown(
        f'<div class="home-hero">'
        f'<div class="home-hero-title">Welcome back, {name} 👋</div>'
        f'<div class="home-hero-sub">Your AI-powered startup command centre. Generate blueprints, '
        f'learn the fundamentals, solve doubts, and run financial calculations — all in one place.</div>'
        f'<div>'
        f'<span class="badge badge-ibm">IBM Granite 4.0</span>'
        f'<span class="badge badge-groq">Groq Llama 3.3</span>'
        f'<span class="badge badge-gemini">✨ Gemini Flash</span>'
        f'<span class="badge badge-rag">CRAG Self-Correcting RAG</span>'
        f'<span class="badge badge-live">🔴 Tavily Live Search</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 4 Feature Cards ───────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns(4)
    cards = [
        ("🚀", "Generate Blueprint", "Describe your startup idea and get a full AI-powered blueprint in minutes.", "#3b82f6", "Most Popular", "dashboard"),
        ("📚", "Startup School", "New to startups? Learn key terms, watch curated videos, and read essential guides.", "#10b981", "For Beginners", "school"),
        ("🤖", "Doubt Solver", "Ask anything — GTM, CAC, incubators, term sheets. Get instant plain-English answers.", "#a78bfa", "AI-Powered", "doubts"),
        ("🧮", "Calculators", "Burn rate, CAC/LTV, valuation, break-even — all the startup math you need.", "#f59e0b", "5 Calculators", "calculators"),
    ]
    for col, (icon, title, desc, color, tag, page_key) in zip([fc1, fc2, fc3, fc4], cards):
        with col:
            st.markdown(
                f'<div class="feat-card" style="border-color:rgba(255,255,255,0.07)">'
                f'<span class="feat-card-icon">{icon}</span>'
                f'<div class="feat-card-title">{title}</div>'
                f'<div class="feat-card-desc">{desc}</div>'
                f'<span class="feat-card-tag" style="background:{color}18;color:{color};border:1px solid {color}33">{tag}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Open →", key=f"feat_{page_key}", use_container_width=True, type="primary" if page_key == "dashboard" else "secondary"):
                st.session_state.home_section = page_key
                if page_key == "dashboard":
                    st.session_state.page = "dashboard"
                st.rerun()

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── Section Router ────────────────────────────────────────────────────────
    section = st.session_state.get("home_section", "dashboard")

    if section == "school":
        _render_school()
    elif section == "doubts":
        _render_doubts(groq_client)
    elif section == "calculators":
        _render_calculators()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: STARTUP SCHOOL
# ══════════════════════════════════════════════════════════════════════════════

def _render_school():
    st.markdown("---")
    st.markdown(
        '<div style="font-size:1.3rem;font-weight:800;color:#f1f5f9;margin-bottom:0.3rem">📚 Startup School</div>'
        '<div style="font-size:0.83rem;color:#64748b;margin-bottom:1.5rem">Curated resources to help you understand the startup world — videos, articles, and official guides.</div>',
        unsafe_allow_html=True,
    )

    for category, resources in RESOURCES.items():
        st.markdown(f'<div style="font-size:0.85rem;font-weight:700;color:#94a3b8;margin:1.2rem 0 0.7rem;text-transform:uppercase;letter-spacing:0.06em">{category}</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, r in enumerate(resources):
            with cols[i % 2]:
                st.markdown(
                    f'<a href="{r["url"]}" target="_blank" style="text-decoration:none">'
                    f'<div class="resource-card">'
                    f'<span class="resource-icon">{r["icon"]}</span>'
                    f'<div>'
                    f'<div class="resource-title">{r["title"]}</div>'
                    f'<div class="resource-desc">{r["desc"]}</div>'
                    f'<span class="resource-tag" style="background:{r["tag_color"]}18;color:{r["tag_color"]};border:1px solid {r["tag_color"]}33">{r["tag"]}</span>'
                    f'</div></div></a>',
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="background:rgba(15,98,254,0.06);border:1px solid rgba(15,98,254,0.15);border-radius:14px;padding:1rem 1.3rem;font-size:0.83rem;color:#94a3b8;line-height:1.7">'
        '💡 <strong style="color:#60a5fa">Ready to apply what you learned?</strong> '
        'Once you understand the basics, go to <strong>Generate Blueprint</strong> and describe your startup idea — '
        'our AI will create a full Business Model Canvas, budget, GTM strategy, and more.'
        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: DOUBT SOLVER
# ══════════════════════════════════════════════════════════════════════════════

def _render_doubts(groq_client):
    st.markdown("---")
    st.markdown(
        '<div style="font-size:1.3rem;font-weight:800;color:#f1f5f9;margin-bottom:0.3rem">🤖 Doubt Solver</div>'
        '<div style="font-size:0.83rem;color:#64748b;margin-bottom:1.2rem">Ask anything about startups. Get clear, jargon-free answers with Indian examples.</div>',
        unsafe_allow_html=True,
    )

    # Chat history
    if "doubt_history" not in st.session_state:
        st.session_state.doubt_history = []

    # Quick question chips
    st.markdown('<div style="font-size:0.75rem;color:#64748b;margin-bottom:0.5rem;font-weight:600">⚡ Quick questions:</div>', unsafe_allow_html=True)
    chip_cols = st.columns(4)
    for i, q in enumerate(QUICK_QUESTIONS):
        with chip_cols[i % 4]:
            if st.button(q, key=f"quick_{i}", use_container_width=True):
                with st.spinner("Thinking..."):
                    answer = _ask_doubt(q, groq_client)
                st.session_state.doubt_history.append({"q": q, "a": answer})
                st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # Custom question input
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        user_q = st.text_input(
            "", placeholder="e.g. What is the difference between equity and debt funding?",
            key="doubt_input", label_visibility="collapsed"
        )
    with col_btn:
        ask_btn = st.button("Ask →", key="doubt_ask", type="primary", use_container_width=True)

    if ask_btn and user_q.strip():
        with st.spinner("Thinking..."):
            answer = _ask_doubt(user_q.strip(), groq_client)
        st.session_state.doubt_history.append({"q": user_q.strip(), "a": answer})
        st.rerun()

    # Render chat history
    if st.session_state.doubt_history:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        for item in reversed(st.session_state.doubt_history[-6:]):
            st.markdown(f'<div class="chat-user">{item["q"]}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="chat-bot">'
                f'<div class="chat-bot-header">🤖 Startup Mentor</div>'
                f'{item["a"]}'
                f'</div>',
                unsafe_allow_html=True,
            )

        if st.button("🗑 Clear conversation", key="clear_doubts"):
            st.session_state.doubt_history = []
            st.rerun()
    else:
        st.markdown(
            '<div style="text-align:center;padding:2rem;color:#475569">'
            '<div style="font-size:2rem;margin-bottom:0.5rem">🤔</div>'
            '<div style="font-size:0.85rem">Ask your first question above or tap a quick question chip!</div>'
            '</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: CALCULATORS
# ══════════════════════════════════════════════════════════════════════════════

def _render_calculators():
    st.markdown("---")
    st.markdown(
        '<div style="font-size:1.3rem;font-weight:800;color:#f1f5f9;margin-bottom:0.3rem">🧮 Startup Calculators</div>'
        '<div style="font-size:0.83rem;color:#64748b;margin-bottom:1.5rem">Essential financial models for founders. All amounts in Indian Rupees (₹).</div>',
        unsafe_allow_html=True,
    )

    calc_tabs = st.tabs([
        "🔥 Burn Rate & Runway",
        "📊 CAC / LTV",
        "💎 Valuation",
        "⚖️ Break-Even",
        "🎯 Fundraising Need",
    ])

    with calc_tabs[0]:
        _calc_burn_rate()
    with calc_tabs[1]:
        _calc_cac_ltv()
    with calc_tabs[2]:
        _calc_valuation()
    with calc_tabs[3]:
        _calc_breakeven()
    with calc_tabs[4]:
        _calc_fundraise()