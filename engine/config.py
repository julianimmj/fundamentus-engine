"""
config.py — Configurações centrais do Fundamentus Engine
Contém: lista de ~200 tickers, classificação setorial, constantes de scoring.
"""
import os

# ─────────────────────────────────────────────────────────────
# API Keys (via env vars para segurança no Streamlit Cloud)
# ─────────────────────────────────────────────────────────────
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# ─────────────────────────────────────────────────────────────
# Scoring Weights
# ─────────────────────────────────────────────────────────────
SCORE_WEIGHTS = {
    "macro": 0.30,
    "quality": 0.25,
    "valuation": 0.25,
    "momentum": 0.15,
    "governance": 0.05,
}

# ─────────────────────────────────────────────────────────────
# Classification Thresholds
# ─────────────────────────────────────────────────────────────
THRESHOLDS = {
    "promissor_score": 65,
    "promissor_upside": 0.10,
    "neutro_min": 40,
    "neutro_max": 64,
    "ruim_score": 40,
    "ruim_upside": -0.20,
}

# ─────────────────────────────────────────────────────────────
# Valuation Constants
# ─────────────────────────────────────────────────────────────
ERP_DEFAULT = 0.055          # Equity Risk Premium
TERMINAL_GROWTH_BR = 0.035   # Terminal growth Brasil (nominal)
TERMINAL_GROWTH_US = 0.025   # Terminal growth US (BDRs)
TAX_RATE_BR = 0.34           # Alíquota efetiva IR+CSLL Brasil
PROJECTION_YEARS = 5

# ─────────────────────────────────────────────────────────────
# Bank-specific Constants
# ─────────────────────────────────────────────────────────────
BANK_PEERS = ["ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "SANB11.SA", "BPAC11.SA"]
BANK_SECTORS = {"bancos", "seguros"}  # Sectors treated as financial institutions
# Tickers in 'bancos' sector that are NOT banks (exchanges, fintechs, etc.)
BANK_EXCLUSIONS = {"B3SA3.SA", "CIEL3.SA"}

# ─────────────────────────────────────────────────────────────
# Setores e Classificação
# ─────────────────────────────────────────────────────────────
SECTORS = {
    "bancos": {
        "name": "Bancos & Financeiro",
        "sensitivity": {"juros": 0.8, "commodities": 0.1, "cambio": 0.3},
    },
    "mineracao": {
        "name": "Mineração & Siderurgia",
        "sensitivity": {"juros": 0.2, "commodities": 0.9, "cambio": 0.7},
    },
    "petroleo": {
        "name": "Petróleo & Gás",
        "sensitivity": {"juros": 0.2, "commodities": 0.9, "cambio": 0.8},
    },
    "utilities": {
        "name": "Utilities (Energia)",
        "sensitivity": {"juros": 0.7, "commodities": 0.2, "cambio": 0.3},
    },
    "varejo": {
        "name": "Varejo & Consumo",
        "sensitivity": {"juros": 0.9, "commodities": 0.2, "cambio": 0.4},
    },
    "saude": {
        "name": "Saúde",
        "sensitivity": {"juros": 0.5, "commodities": 0.1, "cambio": 0.3},
    },
    "tech": {
        "name": "Tecnologia & Software",
        "sensitivity": {"juros": 0.8, "commodities": 0.05, "cambio": 0.3},
    },
    "imobiliario": {
        "name": "Imobiliário & Construção",
        "sensitivity": {"juros": 0.9, "commodities": 0.3, "cambio": 0.2},
    },
    "alimentos": {
        "name": "Alimentos & Bebidas",
        "sensitivity": {"juros": 0.3, "commodities": 0.7, "cambio": 0.6},
    },
    "papel_celulose": {
        "name": "Papel & Celulose",
        "sensitivity": {"juros": 0.3, "commodities": 0.6, "cambio": 0.8},
    },
    "seguros": {
        "name": "Seguros & Previdência",
        "sensitivity": {"juros": 0.7, "commodities": 0.05, "cambio": 0.2},
    },
    "transporte": {
        "name": "Transporte & Logística",
        "sensitivity": {"juros": 0.5, "commodities": 0.4, "cambio": 0.5},
    },
    "telecom": {
        "name": "Telecomunicações",
        "sensitivity": {"juros": 0.4, "commodities": 0.05, "cambio": 0.3},
    },
    "saneamento": {
        "name": "Saneamento",
        "sensitivity": {"juros": 0.6, "commodities": 0.1, "cambio": 0.1},
    },
    "agro": {
        "name": "Agronegócio",
        "sensitivity": {"juros": 0.3, "commodities": 0.8, "cambio": 0.7},
    },
    "industrial": {
        "name": "Bens Industriais",
        "sensitivity": {"juros": 0.5, "commodities": 0.4, "cambio": 0.5},
    },
    "fii": {
        "name": "Fundos Imobiliários",
        "sensitivity": {"juros": 0.9, "commodities": 0.05, "cambio": 0.1},
    },
    "bdr_tech": {
        "name": "BDR Tech (EUA)",
        "sensitivity": {"juros": 0.7, "commodities": 0.1, "cambio": 0.9},
    },
    "bdr_saude": {
        "name": "BDR Saúde (EUA)",
        "sensitivity": {"juros": 0.5, "commodities": 0.1, "cambio": 0.8},
    },
    "bdr_finance": {
        "name": "BDR Financeiro (EUA)",
        "sensitivity": {"juros": 0.7, "commodities": 0.1, "cambio": 0.8},
    },
    "bdr_consumo": {
        "name": "BDR Consumo (EUA)",
        "sensitivity": {"juros": 0.5, "commodities": 0.2, "cambio": 0.8},
    },
    "bdr_industrial": {
        "name": "BDR Industrial (EUA)",
        "sensitivity": {"juros": 0.5, "commodities": 0.3, "cambio": 0.8},
    },
    "bdr_energia": {
        "name": "BDR Energia (EUA)",
        "sensitivity": {"juros": 0.3, "commodities": 0.8, "cambio": 0.8},
    },
}

# ─────────────────────────────────────────────────────────────
# Ticker → Setor mapping
# ─────────────────────────────────────────────────────────────
TICKER_SECTOR = {
    # ── Bancos & Financeiro ──
    "ITUB4.SA": "bancos", "BBDC4.SA": "bancos", "BBAS3.SA": "bancos",
    "SANB11.SA": "bancos", "BPAC11.SA": "bancos", "ITSA4.SA": "bancos",
    "BBDC3.SA": "bancos",
    # ── Mercado de Capitais (não é banco) ──
    "B3SA3.SA": "industrial",
    "ITUB3.SA": "bancos", "ABCB4.SA": "bancos", "BRSR6.SA": "bancos",
    "BMGB4.SA": "bancos",
    # ── Mineração & Siderurgia ──
    "VALE3.SA": "mineracao", "CSNA3.SA": "mineracao", "USIM5.SA": "mineracao",
    "GGBR4.SA": "mineracao", "GOAU4.SA": "mineracao", "CMIN3.SA": "mineracao",
    "GGBR3.SA": "mineracao", "FESA4.SA": "mineracao",
    # ── Petróleo & Gás ──
    "PETR4.SA": "petroleo", "PETR3.SA": "petroleo", "PRIO3.SA": "petroleo",
    "RECV3.SA": "petroleo", "CSAN3.SA": "petroleo",
    "VBBR3.SA": "petroleo", "UGPA3.SA": "petroleo", "RAIZ4.SA": "petroleo",
    "BRKM5.SA": "petroleo",
    # ── Utilities (Energia) ──
    "EQTL3.SA": "utilities",
    "ENGI11.SA": "utilities", "CPFE3.SA": "utilities",
    "CMIG4.SA": "utilities", "TAEE11.SA": "utilities", "EGIE3.SA": "utilities",
    "AURE3.SA": "utilities",
    "ENEV3.SA": "utilities", "CPLE3.SA": "utilities", "CMIG3.SA": "utilities",
    "NEOE3.SA": "utilities", "ALUP11.SA": "utilities",
    # ── Varejo & Consumo ──
    "MGLU3.SA": "varejo", "LREN3.SA": "varejo",
    "AZZA3.SA": "varejo", "BHIA3.SA": "varejo",
    "ASAI3.SA": "varejo", "PCAR3.SA": "varejo",
    "ALPA4.SA": "varejo", "GRND3.SA": "varejo",
    "VULC3.SA": "varejo", "VIVA3.SA": "varejo", "ARML3.SA": "varejo",
    # ── Saúde ──
    "RDOR3.SA": "saude", "HAPV3.SA": "saude", "FLRY3.SA": "saude",
    "HYPE3.SA": "saude", "RADL3.SA": "saude", "ONCO3.SA": "saude",
    "DASA3.SA": "saude", "MATD3.SA": "saude",
    # ── Tecnologia ──
    "TOTS3.SA": "tech", "LWSA3.SA": "tech", "CASH3.SA": "tech",
    "MLAS3.SA": "tech", "INTB3.SA": "tech",
    # ── Imobiliário & Construção ──
    "CYRE3.SA": "imobiliario", "MRVE3.SA": "imobiliario", "EZTC3.SA": "imobiliario",
    "MULT3.SA": "imobiliario", "IGTI11.SA": "imobiliario", "EVEN3.SA": "imobiliario",
    "TEND3.SA": "imobiliario", "TRIS3.SA": "imobiliario", "DIRR3.SA": "imobiliario",
    "LAVV3.SA": "imobiliario",
    # ── Alimentos & Bebidas ──
    "ABEV3.SA": "alimentos",
    "MDIA3.SA": "alimentos", "BEEF3.SA": "alimentos", "SMTO3.SA": "alimentos",
    # ── Papel & Celulose ──
    "SUZB3.SA": "papel_celulose", "KLBN11.SA": "papel_celulose",
    "DXCO3.SA": "papel_celulose", "KLBN4.SA": "papel_celulose",
    # ── Seguros & Previdência ──
    "BBSE3.SA": "seguros", "PSSA3.SA": "seguros", "IRBR3.SA": "seguros",
    # ── Transporte & Logística ──
    "RAIL3.SA": "transporte", "ECOR3.SA": "transporte",
    "RENT3.SA": "transporte", "MOVI3.SA": "transporte",
    "VAMO3.SA": "transporte", "SIMH3.SA": "transporte",
    # ── Telecomunicações ──
    "VIVT3.SA": "telecom", "TIMS3.SA": "telecom",
    # ── Saneamento ──
    "SBSP3.SA": "saneamento", "SAPR11.SA": "saneamento", "CSMG3.SA": "saneamento",
    # ── Agronegócio ──
    "SLCE3.SA": "agro", "AGRO3.SA": "agro", "SMTO3.SA": "agro",
    # ── Bens Industriais ──
    "WEGE3.SA": "industrial", "PRNR3.SA": "industrial",
    "PTBL3.SA": "industrial", "TUPY3.SA": "industrial", "ROMI3.SA": "industrial",
    # ── Educação ──
    "YDUQ3.SA": "varejo", "COGN3.SA": "varejo", "ANIM3.SA": "varejo",
    # ── FIIs (30 mais líquidos) ──
    "HGLG11.SA": "fii", "XPML11.SA": "fii", "KNRI11.SA": "fii",
    "MXRF11.SA": "fii", "VISC11.SA": "fii", "HGBS11.SA": "fii",
    "XPLG11.SA": "fii", "BTLG11.SA": "fii", "VILG11.SA": "fii",
    "PVBI11.SA": "fii", "RBRR11.SA": "fii", "CPTS11.SA": "fii",
    "HGRE11.SA": "fii", "HSML11.SA": "fii", "IRDM11.SA": "fii",
    "RECR11.SA": "fii", "KNIP11.SA": "fii", "KNCR11.SA": "fii",
    "HFOF11.SA": "fii", "TGAR11.SA": "fii",
    "JSRE11.SA": "fii", "BRCR11.SA": "fii", "LVBI11.SA": "fii",
    "RBRF11.SA": "fii", "VGIR11.SA": "fii", "SNFF11.SA": "fii",
    "RZTR11.SA": "fii", "TRXF11.SA": "fii", "RBRP11.SA": "fii",
    # ── BDRs Tech ──
    "AAPL34.SA": "bdr_tech", "MSFT34.SA": "bdr_tech", "GOGL34.SA": "bdr_tech",
    "AMZO34.SA": "bdr_tech", "TSLA34.SA": "bdr_tech", "M1TA34.SA": "bdr_tech",
    "NVDC34.SA": "bdr_tech", "NFLX34.SA": "bdr_tech", "AVGO34.SA": "bdr_tech",
    "ORCL34.SA": "bdr_tech", "ADBE34.SA": "bdr_tech",
    "QCOM34.SA": "bdr_tech",
    # ── BDRs Saúde ──
    "JNJB34.SA": "bdr_saude", "PFIZ34.SA": "bdr_saude", "ABBV34.SA": "bdr_saude",
    "MRCK34.SA": "bdr_saude",
    # ── BDRs Financeiro ──
    "JPMC34.SA": "bdr_finance", "BERK34.SA": "bdr_finance", "VISA34.SA": "bdr_finance",
    "MSCD34.SA": "bdr_finance", "GSGI34.SA": "bdr_finance",
    # ── BDRs Consumo ──
    "COCA34.SA": "bdr_consumo", "PEPB34.SA": "bdr_consumo", "PGCO34.SA": "bdr_consumo",
    "NIKE34.SA": "bdr_consumo",
    "WALM34.SA": "bdr_consumo", "DISB34.SA": "bdr_consumo",
    # ── BDRs Industrial ──
    "CATP34.SA": "bdr_industrial", "HONB34.SA": "bdr_industrial",
    "DEEC34.SA": "bdr_industrial", "GEOO34.SA": "bdr_industrial",
    # ── BDRs Energia ──
    "EXXO34.SA": "bdr_energia", "CHVX34.SA": "bdr_energia",
}

# ─────────────────────────────────────────────────────────────
# Governance: Segmentos de listagem (proxy ESG)
# ─────────────────────────────────────────────────────────────
GOVERNANCE_SEGMENTS = {
    # Novo Mercado = 100, Nível 2 = 75, Nível 1 = 50, Tradicional = 25
    # BDRs e FIIs recebem 60 (governança estrangeira / regulação CVM)
    "novo_mercado": 100,
    "nivel_2": 75,
    "nivel_1": 50,
    "tradicional": 25,
    "bdr": 60,
    "fii": 60,
}

# Simplified governance mapping (most liquid stocks)
TICKER_GOVERNANCE = {}
# Default: FIIs and BDRs
for t in TICKER_SECTOR:
    sector = TICKER_SECTOR[t]
    if sector == "fii":
        TICKER_GOVERNANCE[t] = "fii"
    elif sector.startswith("bdr_"):
        TICKER_GOVERNANCE[t] = "bdr"
    else:
        # Default to novo_mercado for most liquid stocks (simplified)
        TICKER_GOVERNANCE[t] = "novo_mercado"

# Override known Nível 1/2/Tradicional stocks
for t in ["ITUB4.SA", "BBDC4.SA", "USIM5.SA", "GGBR4.SA", "GOAU4.SA",
           "CMIG4.SA", "ELET6.SA", "CPLE6.SA", "BBDC3.SA", "ITUB3.SA",
           "SANB11.SA", "KLBN4.SA", "ALPA4.SA", "TAEE11.SA"]:
    TICKER_GOVERNANCE[t] = "nivel_1"

for t in ["PETR4.SA", "PETR3.SA", "ELET3.SA"]:
    TICKER_GOVERNANCE[t] = "nivel_2"

# ─────────────────────────────────────────────────────────────
# FII Type Classification
# ─────────────────────────────────────────────────────────────
FII_TYPES = {
    "HGLG11.SA": "logistica", "XPML11.SA": "shopping", "KNRI11.SA": "hibrido",
    "MXRF11.SA": "papel", "VISC11.SA": "shopping", "HGBS11.SA": "shopping",
    "XPLG11.SA": "logistica", "BTLG11.SA": "logistica", "VILG11.SA": "logistica",
    "PVBI11.SA": "lajes", "RBRR11.SA": "papel", "CPTS11.SA": "papel",
    "HGRE11.SA": "lajes", "HSML11.SA": "shopping", "IRDM11.SA": "papel",
    "RECR11.SA": "papel", "KNIP11.SA": "papel", "KNCR11.SA": "papel",
    "BCFF11.SA": "fof", "HFOF11.SA": "fof", "TGAR11.SA": "hibrido",
    "JSRE11.SA": "lajes", "BRCR11.SA": "lajes", "LVBI11.SA": "logistica",
    "RBRF11.SA": "fof", "VGIR11.SA": "papel", "SNFF11.SA": "fof",
    "RZTR11.SA": "agro", "TRXF11.SA": "renda_urbana", "RBRP11.SA": "hibrido",
}

# ─────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────
def get_all_tickers():
    """Return list of all tickers."""
    return list(TICKER_SECTOR.keys())

def get_tickers_by_type():
    """Return tickers grouped by type (acao, bdr, fii)."""
    acoes, bdrs, fiis = [], [], []
    for t, s in TICKER_SECTOR.items():
        if s == "fii":
            fiis.append(t)
        elif s.startswith("bdr_"):
            bdrs.append(t)
        else:
            acoes.append(t)
    return {"acoes": acoes, "bdrs": bdrs, "fiis": fiis}

def get_tickers_by_sector(sector_key):
    """Return tickers in a specific sector."""
    return [t for t, s in TICKER_SECTOR.items() if s == sector_key]

def get_sector_name(sector_key):
    """Return human-readable sector name."""
    return SECTORS.get(sector_key, {}).get("name", sector_key)

def get_ticker_type(ticker):
    """Return 'FII', 'BDR', 'Banco', or 'Ação' for a ticker."""
    s = TICKER_SECTOR.get(ticker, "")
    if s == "fii":
        return "FII"
    if s.startswith("bdr_"):
        return "BDR"
    if is_financial_institution(ticker):
        return "Banco"
    return "Ação"

def is_financial_institution(ticker):
    """Detect if ticker is a bank/financial institution.
    
    Auto-detects based on sector classification, with exclusions
    for non-bank entities in the financial sector (e.g. B3, Cielo).
    """
    if ticker in BANK_EXCLUSIONS:
        return False
    sector = TICKER_SECTOR.get(ticker, "")
    return sector in BANK_SECTORS
