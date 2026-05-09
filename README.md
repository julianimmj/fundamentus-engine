# 🏦 Fundamentus Engine — Análise Top-Down B3

Motor de análise fundamentalista automatizado para ~200 ativos da B3 (Ações, BDRs, FIIs).

## 🏗️ Arquitetura

Pipeline Top-Down com 5 camadas:

1. **Macro Global** — VIX, DXY, Commodities, Treasury yields (Yahoo Finance + World Bank)
2. **Macro Brasil** — Selic, IPCA, Câmbio, Dívida/PIB, Focus (API BCB)
3. **Análise Setorial** — 17 setores com sensibilidades a juros/commodities/câmbio
4. **Bottom-Up** — Indicadores + Projeções 5 anos + DCF + Múltiplos (yfinance)
5. **Scoring** — Score composto 0-100 → Classificação (Promissor/Neutro/Viés Ruim)

## 🚀 Como usar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📊 Classificação

| Rating | Critério |
|--------|----------|
| 🟢 Promissor | Score ≥ 75, Upside > 20%, Macro favorável |
| 🟡 Neutro | Score 45-74 |
| 🔴 Viés Ruim | Score < 45 ou Upside < -15% |

## ⚠️ Disclaimer

Modelo quantitativo automatizado para fins educacionais. Não constitui recomendação de investimento.
