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
    "A1MD34.SA": "bdr_tech",
    "AALL34.SA": "bdr_tech",
    "AAPL34.SA": "bdr_tech",
    "ABCB4.SA": "bancos",
    "ABEV3.SA": "alimentos",
    "AGRO3.SA": "agro",
    "AIRB34.SA": "bdr_tech",
    "ALOS3.SA": "outros",
    "ALPA4.SA": "varejo",
    "ALUP11.SA": "utilities",
    "ALZR11.SA": "fii",
    "AMBP3.SA": "outros",
    "AMER3.SA": "outros",
    "AMZO34.SA": "bdr_tech",
    "ANIM3.SA": "varejo",
    "ARML3.SA": "varejo",
    "ASAI3.SA": "varejo",
    "ASML34.SA": "bdr_tech",
    "AURE3.SA": "utilities",
    "AVGO34.SA": "bdr_tech",
    "AXIA3.SA": "outros",
    "AXIA6.SA": "outros",
    "AZZA3.SA": "varejo",
    "B3SA3.SA": "industrial",
    "BABA34.SA": "bdr_tech",
    "BBAS3.SA": "bancos",
    "BBDC3.SA": "bancos",
    "BBDC4.SA": "bancos",
    "BBOV11.SA": "bdr_tech",
    "BBSE3.SA": "seguros",
    "BEEF3.SA": "alimentos",
    "BERK34.SA": "bdr_finance",
    "BHIA3.SA": "varejo",
    "BIDU34.SA": "bdr_tech",
    "BLAK34.SA": "bdr_tech",
    "BLAU3.SA": "outros",
    "BMGB4.SA": "bancos",
    "BMOB3.SA": "outros",
    "BOEI34.SA": "bdr_tech",
    "BPAC11.SA": "bancos",
    "BRAP4.SA": "outros",
    "BRAV3.SA": "outros",
    "BRBI11.SA": "bancos",
    "BRCO11.SA": "fii",
    "BRCR11.SA": "fii",
    "BRKM5.SA": "petroleo",
    "BRSR6.SA": "bancos",
    "BTLG11.SA": "fii",
    "C2OI34.SA": "bdr_tech",
    "CAML3.SA": "outros",
    "CASH3.SA": "tech",
    "CBAV3.SA": "outros",
    "CEAB3.SA": "outros",
    "CHVX34.SA": "bdr_energia",
    "CLSC4.SA": "outros",
    "CMCS34.SA": "bdr_tech",
    "CMIG3.SA": "utilities",
    "CMIG4.SA": "utilities",
    "CMIN3.SA": "mineracao",
    "COCA34.SA": "bdr_consumo",
    "COGN3.SA": "varejo",
    "COWC34.SA": "bdr_tech",
    "CPFE3.SA": "utilities",
    "CPLE3.SA": "utilities",
    "CPTS11.SA": "fii",
    "CSAN3.SA": "petroleo",
    "CSCO34.SA": "bdr_tech",
    "CSED3.SA": "outros",
    "CSMG3.SA": "saneamento",
    "CSNA3.SA": "mineracao",
    "CURY3.SA": "outros",
    "CVCB3.SA": "outros",
    "CXSE3.SA": "outros",
    "CYRE3.SA": "imobiliario",
    "DIRR3.SA": "imobiliario",
    "DISB34.SA": "bdr_consumo",
    "DXCO3.SA": "papel_celulose",
    "ECOR3.SA": "transporte",
    "EGIE3.SA": "utilities",
    "ENEV3.SA": "utilities",
    "ENGI11.SA": "utilities",
    "ENJU3.SA": "outros",
    "EQTL3.SA": "utilities",
    "ESPA3.SA": "outros",
    "EVEN3.SA": "imobiliario",
    "EXXO34.SA": "bdr_energia",
    "EZTC3.SA": "imobiliario",
    "FESA4.SA": "mineracao",
    "FIQE3.SA": "outros",
    "FLRY3.SA": "saude",
    "FRAS3.SA": "outros",
    "GFSA3.SA": "outros",
    "GGBR4.SA": "mineracao",
    "GGPS3.SA": "outros",
    "GGRC11.SA": "fii",
    "GMAT3.SA": "outros",
    "GOAU4.SA": "mineracao",
    "GOGL34.SA": "bdr_tech",
    "GOGL35.SA": "bdr_tech",
    "GRND3.SA": "varejo",
    "GTWR11.SA": "fii",
    "HAPV3.SA": "saude",
    "HBOR3.SA": "outros",
    "HBSA3.SA": "outros",
    "HGBS11.SA": "fii",
    "HGCR11.SA": "fii",
    "HGLG11.SA": "fii",
    "HGRU11.SA": "fii",
    "HOME34.SA": "bdr_tech",
    "HSML11.SA": "fii",
    "HYPE3.SA": "saude",
    "IGTI11.SA": "imobiliario",
    "INBR32.SA": "bdr_tech",
    "INTB3.SA": "tech",
    "IRBR3.SA": "seguros",
    "ISAE4.SA": "outros",
    "ITLC34.SA": "bdr_tech",
    "ITSA4.SA": "bancos",
    "ITUB4.SA": "bancos",
    "JALL3.SA": "outros",
    "JBSS32.SA": "bdr_tech",
    "JHSF3.SA": "outros",
    "JNJB34.SA": "bdr_saude",
    "JPMC34.SA": "bdr_finance",
    "JSLG3.SA": "outros",
    "JSRE11.SA": "fii",
    "KEPL3.SA": "outros",
    "KLBN11.SA": "papel_celulose",
    "KNCR11.SA": "fii",
    "KNRI11.SA": "fii",
    "KNSC11.SA": "fii",
    "LAVV3.SA": "imobiliario",
    "LEVE3.SA": "outros",
    "LILY34.SA": "bdr_tech",
    "LOGG3.SA": "outros",
    "LREN3.SA": "varejo",
    "LVBI11.SA": "fii",
    "LWSA3.SA": "tech",
    "M1TA34.SA": "bdr_tech",
    "M2ST34.SA": "bdr_tech",
    "MATD3.SA": "saude",
    "MBRF3.SA": "outros",
    "MCDC34.SA": "bdr_tech",
    "MDIA3.SA": "alimentos",
    "MDNE3.SA": "outros",
    "MELI34.SA": "bdr_tech",
    "MGLU3.SA": "varejo",
    "MMMC34.SA": "bdr_tech",
    "MOSC34.SA": "bdr_tech",
    "MOTV3.SA": "outros",
    "MOVI3.SA": "transporte",
    "MRCK34.SA": "bdr_saude",
    "MRVE3.SA": "imobiliario",
    "MSBR34.SA": "bdr_tech",
    "MSCD34.SA": "bdr_finance",
    "MSFT34.SA": "bdr_tech",
    "MTRE3.SA": "outros",
    "MULT3.SA": "imobiliario",
    "MXRF11.SA": "fii",
    "MYPK3.SA": "outros",
    "NEOE3.SA": "utilities",
    "NFLX34.SA": "bdr_tech",
    "NGRD3.SA": "outros",
    "NIKE34.SA": "bdr_consumo",
    "NVDC34.SA": "bdr_tech",
    "ODPV3.SA": "outros",
    "ONCO3.SA": "saude",
    "OPCT3.SA": "outros",
    "ORCL34.SA": "bdr_tech",
    "PCAR3.SA": "varejo",
    "PEPB34.SA": "bdr_consumo",
    "PETR3.SA": "petroleo",
    "PETR4.SA": "petroleo",
    "PFIZ34.SA": "bdr_saude",
    "PFRM3.SA": "outros",
    "PGCO34.SA": "bdr_consumo",
    "PGMN3.SA": "outros",
    "PINE4.SA": "bancos",
    "PLPL3.SA": "outros",
    "PNVL3.SA": "outros",
    "POMO4.SA": "outros",
    "POSI3.SA": "outros",
    "PRIO3.SA": "petroleo",
    "PSSA3.SA": "seguros",
    "PTBL3.SA": "industrial",
    "PVBI11.SA": "fii",
    "PYPL34.SA": "bdr_tech",
    "QCOM34.SA": "bdr_tech",
    "QUAL3.SA": "outros",
    "RADL3.SA": "saude",
    "RAIL3.SA": "transporte",
    "RAIZ4.SA": "petroleo",
    "RANI3.SA": "outros",
    "RAPT4.SA": "outros",
    "RBRR11.SA": "fii",
    "RDOR3.SA": "saude",
    "RECR11.SA": "fii",
    "RECV3.SA": "petroleo",
    "RENT3.SA": "transporte",
    "ROMI3.SA": "industrial",
    "ROXO34.SA": "bdr_tech",
    "S2EA34.SA": "bdr_tech",
    "SANB11.SA": "bancos",
    "SAPR11.SA": "saneamento",
    "SBFG3.SA": "outros",
    "SBSP3.SA": "saneamento",
    "SEER3.SA": "outros",
    "SEQL3.SA": "outros",
    "SIMH3.SA": "transporte",
    "SLCE3.SA": "agro",
    "SMFT3.SA": "outros",
    "SMTO3.SA": "agro",
    "SOJA3.SA": "outros",
    "SSFO34.SA": "bdr_tech",
    "STOC34.SA": "bdr_tech",
    "SUZB3.SA": "papel_celulose",
    "SYNE3.SA": "outros",
    "TAEE11.SA": "utilities",
    "TASA4.SA": "outros",
    "TCSA3.SA": "outros",
    "TEND3.SA": "imobiliario",
    "TGAR11.SA": "fii",
    "TGMA3.SA": "outros",
    "TIMS3.SA": "telecom",
    "TMOS34.SA": "bdr_tech",
    "TOTS3.SA": "tech",
    "TRIS3.SA": "imobiliario",
    "TRXF11.SA": "fii",
    "TSLA34.SA": "bdr_tech",
    "TSMC34.SA": "bdr_tech",
    "TTEN3.SA": "outros",
    "TUPY3.SA": "industrial",
    "UGPA3.SA": "petroleo",
    "ULEV34.SA": "bdr_tech",
    "UNHH34.SA": "bdr_tech",
    "UNIP6.SA": "outros",
    "USIM5.SA": "mineracao",
    "VALE3.SA": "mineracao",
    "VAMO3.SA": "transporte",
    "VBBR3.SA": "petroleo",
    "VGHF11.SA": "fii",
    "VILG11.SA": "fii",
    "VINO11.SA": "fii",
    "VISA34.SA": "bdr_finance",
    "VISC11.SA": "fii",
    "VITT3.SA": "outros",
    "VIVA3.SA": "varejo",
    "VIVT3.SA": "telecom",
    "VLID3.SA": "outros",
    "VRTA11.SA": "fii",
    "VULC3.SA": "varejo",
    "WALM34.SA": "bdr_consumo",
    "WEGE3.SA": "industrial",
    "WIZC3.SA": "outros",
    "XPBR31.SA": "bdr_tech",
    "XPLG11.SA": "fii",
    "XPML11.SA": "fii",
    "YDUQ3.SA": "varejo",
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
