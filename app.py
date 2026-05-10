"""
app.py — Fundamentus Engine: Dashboard Streamlit Premium
Motor de Análise Fundamentalista Top-Down para ~200 ativos da B3.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import json
import os
from pathlib import Path
from datetime import datetime, timezone

# ─────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Fundamentus Engine · Análise Top-Down B3",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# Data paths
# ─────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
RESULTS_CSV = DATA_DIR / "analysis_results.csv"
MACRO_JSON = DATA_DIR / "macro_snapshot.json"

# ─────────────────────────────────────────
# Premium CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .hero {
        background: linear-gradient(135deg, #0a1628 0%, #1a2744 40%, #0d2137 70%, #0a1628 100%);
        padding: 2.5rem 3rem; border-radius: 20px; color: #ffffff;
        margin-bottom: 2rem; position: relative; overflow: hidden;
        border: 1px solid rgba(0, 200, 255, 0.1);
    }
    .hero::before {
        content: ''; position: absolute; top: -50%; right: -20%;
        width: 400px; height: 400px;
        background: radial-gradient(circle, rgba(0,200,255,0.08) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero h1 {
        margin: 0; font-size: 2.4rem; font-weight: 800; letter-spacing: -1px;
        background: linear-gradient(90deg, #fff 40%, #00c8ff 70%, #00ff88);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .hero .subtitle { margin: 0.6rem 0 0; font-size: 1rem; opacity: 0.7; font-weight: 300; }

    .kpi-card {
        background: linear-gradient(145deg, #111b2e, #0d1926);
        border: 1px solid rgba(0,200,255,0.15); border-radius: 16px;
        padding: 1.2rem 1rem; text-align: center; min-height: 110px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4); transition: all 0.3s ease;
    }
    .kpi-card:hover { border-color: rgba(0,200,255,0.4); transform: translateY(-2px); }
    .kpi-card .value { font-weight: 800; font-size: 2.4rem; margin: 0; line-height: 1.1; }
    .kpi-card .label {
        font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px;
        opacity: 0.7; margin-top: 0.5rem; color: #aac;
    }

    .section-title {
        font-size: 1.3rem; font-weight: 700; margin: 1.5rem 0 1rem;
        padding-bottom: 0.5rem; border-bottom: 2px solid rgba(0,200,255,0.2); color: #fafafa;
    }

    .macro-card {
        background: linear-gradient(145deg, #111b2e, #0d1926);
        border: 1px solid rgba(0,200,255,0.12); border-radius: 14px;
        padding: 1.2rem; margin-bottom: 0.8rem;
    }
    .macro-card .outlook { font-size: 1.1rem; font-weight: 700; margin-bottom: 0.5rem; }
    .macro-card .detail { font-size: 0.85rem; color: #8899bb; margin: 0.2rem 0; }

    .rating-promissor { color: #00e676; font-weight: 700; }
    .rating-neutro { color: #ffab00; font-weight: 700; }
    .rating-ruim { color: #ff1744; font-weight: 700; }

    .top-card {
        background: linear-gradient(145deg, #0d2137, #111b2e);
        border: 1px solid rgba(0,255,136,0.15); border-radius: 14px;
        padding: 1rem 1.2rem; margin-bottom: 0.6rem;
        transition: all 0.3s ease;
    }
    .top-card:hover { border-color: rgba(0,255,136,0.4); box-shadow: 0 4px 15px rgba(0,255,136,0.1); }
    .top-card .ticker { font-weight: 800; font-size: 1.1rem; color: #00ff88; }
    .top-card .name { font-size: 0.8rem; color: #8899bb; }
    .top-card .metrics { font-size: 0.85rem; color: #ccd; margin-top: 0.4rem; }

    .freshness {
        background: rgba(0,200,255,0.08); border: 1px solid rgba(0,200,255,0.2);
        border-radius: 12px; padding: 8px 16px; font-size: 0.85rem;
        color: #8899bb; display: inline-block; margin-bottom: 1rem;
    }
    .freshness b { color: #00c8ff; }

    section[data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #0a1628 0%, #111b2e 100%);
    }
    div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

    @media (max-width: 768px) {
        .hero { padding: 1.2rem 1rem !important; border-radius: 12px !important; }
        .hero h1 { font-size: 1.4rem !important; }
        .kpi-card .value { font-size: 1.8rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Hero Header
# ─────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🏦 Fundamentus Engine — Análise Top-Down B3</h1>
    <p class="subtitle">
        Motor quantitativo de análise fundamentalista para <b>~200 ativos</b> da B3
        (Ações, BDRs, FIIs).<br>
        Pipeline completo: <b>Macro Global → Macro Brasil → Setorial → Bottom-Up → Valuation → Scoring</b>.<br>
        <span style="opacity: 0.7; font-size: 0.9em;">
            ⚠️ Modelo quantitativo automatizado — não constitui recomendação de investimento.
        </span>
    </p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# Load data
# ─────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_results(csv_path, mtime=0.0):
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_macro(json_path, mtime=0.0):
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


# ─────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏦 Fundamentus Engine")
    st.caption("Análise Top-Down Automatizada")
    st.markdown("---")

    st.subheader("🔄 Executar Análise")
    run_btn = st.button("▶️ Rodar Análise Completa", use_container_width=True, type="primary")
    st.caption("Processa ~200 ativos (pode levar 10-20 min)")

    st.markdown("---")
    st.subheader("🎯 Filtros")

    filter_rating = st.multiselect(
        "Rating",
        ["Promissor", "Neutro", "Viés Ruim"],
        default=["Promissor", "Neutro", "Viés Ruim"],
    )
    filter_type = st.multiselect(
        "Tipo de Ativo",
        ["Ação", "BDR", "FII"],
        default=["Ação", "BDR", "FII"],
    )

    st.markdown("---")
    with st.expander("📐 Metodologia"):
        st.markdown("""
**Score Composto (0-100):**
| Componente | Peso |
|------------|------|
| Macro Alignment | 30% |
| Qualidade Fundamental | 25% |
| Valuation Attractiveness | 25% |
| Momentum & Liquidez | 15% |
| Governança (proxy) | 5% |

**Classificação:**
- 🟢 **Promissor**: Score ≥ 65, Upside > 10%, Macro +
- 🟡 **Neutro**: Score 40-64
- 🔴 **Viés Ruim**: Score < 40 ou Upside < -20%

**Valuation:** DCF (35%) + Múltiplos (45%) + DDM (20%)
        """)


# ─────────────────────────────────────────
# Run Analysis
# ─────────────────────────────────────────
if run_btn:
    st.cache_data.clear()
    from engine.runner import run_full_analysis
    from engine.config import get_all_tickers

    tickers = get_all_tickers()
    progress_bar = st.progress(0, text="⏳ Iniciando análise top-down...")
    status = st.empty()

    def update_progress(current, total, msg=""):
        pct = min(current / total, 1.0) if total > 0 else 0
        progress_bar.progress(pct, text=f"⏳ {msg} ({current}/{total})")

    status.info(f"🔄 Analisando {len(tickers)} ativos...")
    output = run_full_analysis(
        tickers=tickers, max_workers=8,
        use_cache=True, progress_callback=update_progress
    )

    df = output.get("results", pd.DataFrame())
    if not df.empty:
        os.makedirs(str(DATA_DIR), exist_ok=True)
        df.to_csv(str(RESULTS_CSV), index=False)

        macro_snapshot = {
            "macro_global": {
                "score": output["macro_global"].get("score"),
                "summary": output["macro_global"].get("summary"),
                "timestamp": output["macro_global"].get("timestamp"),
            },
            "macro_brazil": {
                "score": output["macro_brazil"].get("score"),
                "summary": output["macro_brazil"].get("summary"),
                "timestamp": output["macro_brazil"].get("timestamp"),
            },
            "sector_scores": output.get("sector_scores", {}),
            "timestamp": output.get("timestamp"),
        }
        with open(str(MACRO_JSON), "w", encoding="utf-8") as f:
            json.dump(macro_snapshot, f, ensure_ascii=False, indent=2, default=str)

        progress_bar.empty()
        n_p = len(output["promissores"])
        n_n = len(output["neutros"])
        n_r = len(output["vies_ruim"])
        status.success(
            f"✅ Análise concluída! {len(df)} ativos processados: "
            f"{n_p} Promissores, {n_n} Neutros, {n_r} Viés Ruim"
        )
    else:
        progress_bar.empty()
        status.error("❌ Erro na análise. Verifique os logs.")
        st.stop()


# ─────────────────────────────────────────
# Load saved data
# ─────────────────────────────────────────
csv_path = str(RESULTS_CSV)
json_path = str(MACRO_JSON)

mtime_csv = os.path.getmtime(csv_path) if os.path.exists(csv_path) else 0
mtime_json = os.path.getmtime(json_path) if os.path.exists(json_path) else 0

df = load_results(csv_path, mtime_csv)
macro = load_macro(json_path, mtime_json)

if df.empty:
    st.info(
        "📊 **Nenhuma análise disponível.**\n\n"
        "Clique em **▶️ Rodar Análise Completa** na barra lateral para iniciar."
    )
    st.stop()

# ─────────────────────────────────────────
# Freshness badge
# ─────────────────────────────────────────
ts = macro.get("timestamp", "")
if ts:
    try:
        dt = datetime.fromisoformat(str(ts))
        ts_display = dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        ts_display = str(ts)[:19]
else:
    ts_display = "Desconhecido"

n_total = len(df)
n_prom = len(df[df["Rating"] == "Promissor"]) if "Rating" in df.columns else 0
n_neut = len(df[df["Rating"] == "Neutro"]) if "Rating" in df.columns else 0
n_ruim = len(df[df["Rating"] == "Viés Ruim"]) if "Rating" in df.columns else 0

st.markdown(
    f'<div class="freshness">📅 Última análise: <b>{ts_display}</b> · '
    f'<b>{n_total}</b> ativos analisados</div>',
    unsafe_allow_html=True
)

# ─────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
for col, val, label, color in [
    (k1, n_total, "Ativos Analisados", "#00c8ff"),
    (k2, n_prom, "🟢 Promissores", "#00e676"),
    (k3, n_neut, "🟡 Neutros", "#ffab00"),
    (k4, n_ruim, "🔴 Viés Ruim", "#ff1744"),
]:
    col.markdown(f"""
    <div class="kpi-card">
        <p class="value" style="color: {color}">{val}</p>
        <p class="label">{label}</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────
tab_macro, tab_sectors, tab_top15, tab_full = st.tabs([
    "🌍 Sumário Macro", "🏭 Mapa Setorial", "⭐ Top 15 Promissores", "📋 Tabela Completa"
])

# ── Tab 1: Macro Summary ──
with tab_macro:
    st.markdown('<div class="section-title">Panorama Macroeconômico</div>', unsafe_allow_html=True)

    col_g, col_b = st.columns(2)

    # Global Macro
    mg = macro.get("macro_global", {})
    with col_g:
        summary_g = mg.get("summary", {})
        outlook_g = summary_g.get("outlook", "Dados não disponíveis")
        score_g = mg.get("score", "N/A")
        st.markdown(f"""
        <div class="macro-card">
            <div class="outlook">🌍 Macro Global — Score: {score_g}/100</div>
            <div class="detail">{outlook_g}</div>
        </div>
        """, unsafe_allow_html=True)
        for detail in summary_g.get("details", []):
            st.markdown(f"<div class='macro-card'><div class='detail'>• {detail}</div></div>", unsafe_allow_html=True)

    # Brazil Macro
    mb = macro.get("macro_brazil", {})
    with col_b:
        summary_b = mb.get("summary", {})
        outlook_b = summary_b.get("outlook", "Dados não disponíveis")
        score_b = mb.get("score", "N/A")
        st.markdown(f"""
        <div class="macro-card">
            <div class="outlook">🇧🇷 Macro Brasil — Score: {score_b}/100</div>
            <div class="detail">{outlook_b}</div>
        </div>
        """, unsafe_allow_html=True)
        for detail in summary_b.get("details", []):
            st.markdown(f"<div class='macro-card'><div class='detail'>• {detail}</div></div>", unsafe_allow_html=True)

    # Score gauges
    st.markdown("<br>", unsafe_allow_html=True)
    gc1, gc2 = st.columns(2)
    for col, score, title in [(gc1, score_g, "Global"), (gc2, score_b, "Brasil")]:
        if isinstance(score, (int, float)):
            color = "#00e676" if score >= 65 else "#ffab00" if score >= 45 else "#ff1744"
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=score,
                title={"text": f"Score Macro {title}"},
                number={"font": {"size": 48, "color": color}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1, "dtick": 20},
                    "bar": {"color": color, "thickness": 0.3},
                    "bgcolor": "rgba(0,0,0,0)",
                    "steps": [
                        {"range": [0, 45], "color": "rgba(255,23,68,0.1)"},
                        {"range": [45, 65], "color": "rgba(255,171,0,0.1)"},
                        {"range": [65, 100], "color": "rgba(0,230,118,0.1)"},
                    ],
                }
            ))
            fig.update_layout(
                height=280, margin=dict(l=30, r=30, t=60, b=20),
                paper_bgcolor="rgba(0,0,0,0)", font={"color": "#fff"}
            )
            col.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Sector Map ──
with tab_sectors:
    st.markdown('<div class="section-title">Mapa Setorial — Alinhamento Macro</div>', unsafe_allow_html=True)

    sector_scores = macro.get("sector_scores", {})
    if sector_scores:
        rows = []
        for sk, sv in sector_scores.items():
            if isinstance(sv, dict):
                rows.append({
                    "Setor": sv.get("name", sk),
                    "Score": sv.get("score", 50),
                    "Rating": sv.get("rating", "Neutral"),
                })
        if rows:
            df_sec = pd.DataFrame(rows).sort_values("Score", ascending=False)
            colors = df_sec["Rating"].map({
                "Overweight": "#00e676", "Neutral": "#ffab00", "Underweight": "#ff1744"
            }).fillna("#888")
            fig = go.Figure(go.Bar(
                x=df_sec["Score"], y=df_sec["Setor"],
                orientation="h", marker_color=colors.tolist(),
                text=df_sec["Rating"], textposition="auto",
            ))
            fig.update_layout(
                height=max(400, len(rows) * 32),
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#ccc"}, xaxis={"range": [0, 100], "title": "Score"},
                yaxis={"autorange": "reversed"},
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dados setoriais não disponíveis. Execute a análise completa.")

# ── Tab 3: Top 15 Promissores ──
with tab_top15:
    st.markdown('<div class="section-title">⭐ Top 15 Promissores</div>', unsafe_allow_html=True)

    promissores = df[df["Rating"] == "Promissor"].head(15) if "Rating" in df.columns else pd.DataFrame()

    if promissores.empty:
        st.info("Nenhum ativo classificado como Promissor na última análise.")
    else:
        for _, row in promissores.iterrows():
            upside = row.get("Upside")
            upside_str = f"{upside*100:+.1f}%" if pd.notna(upside) else "N/A"
            score = row.get("Score", 0)
            tp = row.get("Target Price")
            tp_str = f"R$ {tp:,.2f}" if pd.notna(tp) else "N/A"
            price = row.get("Preço")
            price_str = f"R$ {price:,.2f}" if pd.notna(price) else "N/A"
            roe = row.get("ROE")
            roe_str = f"{roe*100:.1f}%" if pd.notna(roe) else "N/A"

            justification = []
            if pd.notna(upside) and upside > 0.3:
                justification.append("upside significativo")
            if pd.notna(roe) and roe > 0.15:
                justification.append("alta rentabilidade")
            margin = row.get("Margem EBITDA")
            if pd.notna(margin) and margin > 0.25:
                justification.append("margens sólidas")
            growth = row.get("Cresc. Receita")
            if pd.notna(growth) and growth > 0.10:
                justification.append("crescimento acelerado")
            just_str = " · ".join(justification) if justification else "fundamentos sólidos"

            st.markdown(f"""
            <div class="top-card">
                <span class="ticker">{row.get('Ticker', '')}</span>
                <span class="name" style="margin-left: 12px;">{row.get('Nome', '')}</span>
                <span style="float: right; color: #00e676; font-weight: 700;">
                    Score {score:.0f} · Upside {upside_str}
                </span>
                <div class="metrics">
                    Preço: {price_str} → Target: {tp_str} · ROE: {roe_str} · {row.get('Setor', '')}
                    <br><span style="color: #6688aa;">💡 {just_str}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ── Tab 4: Full Table ──
with tab_full:
    st.markdown('<div class="section-title">Tabela Completa — Todos os Ativos</div>', unsafe_allow_html=True)

    # Apply filters
    filtered = df.copy()
    if "Rating" in filtered.columns and filter_rating:
        filtered = filtered[filtered["Rating"].isin(filter_rating)]
    if "Tipo" in filtered.columns and filter_type:
        filtered = filtered[filtered["Tipo"].isin(filter_type)]

    if filtered.empty:
        st.info("Nenhum ativo encontrado com os filtros selecionados.")
    else:
        # Format display
        display_cols = [
            "Ticker", "Nome", "Tipo", "Setor", "Rating", "Score",
            "Preço", "Target Price", "Upside", "ROE", "ROIC",
            "Margem EBITDA", "P/L", "EV/EBITDA", "Div. Yield",
            "Dív. Líq./EBITDA", "Vol. Médio",
        ]
        available = [c for c in display_cols if c in filtered.columns]
        display = filtered[available].copy()

        # Format numbers
        for col in ["Preço", "Target Price"]:
            if col in display.columns:
                display[col] = display[col].apply(
                    lambda v: f"R$ {v:,.2f}" if pd.notna(v) else "–"
                )
        for col in ["Upside", "ROE", "ROIC", "Margem EBITDA", "Div. Yield", "Cresc. Receita"]:
            if col in display.columns:
                display[col] = display[col].apply(
                    lambda v: f"{v*100:.1f}%" if pd.notna(v) else "–"
                )
        for col in ["P/L", "EV/EBITDA", "Dív. Líq./EBITDA"]:
            if col in display.columns:
                display[col] = display[col].apply(
                    lambda v: f"{v:.1f}x" if pd.notna(v) else "–"
                )
        if "Score" in display.columns:
            display["Score"] = display["Score"].apply(
                lambda v: f"{v:.0f}" if pd.notna(v) else "–"
            )
        if "Vol. Médio" in display.columns:
            display["Vol. Médio"] = display["Vol. Médio"].apply(
                lambda v: f"{v:,.0f}" if pd.notna(v) and v > 0 else "–"
            )

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=min(800, 35 * len(display) + 38),
        )

        st.caption(f"Exibindo {len(display)} de {n_total} ativos · Última análise: {ts_display}")

        # Download button
        csv_export = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exportar CSV",
            csv_export,
            "fundamentus_engine_results.csv",
            "text/csv",
            use_container_width=True,
        )
