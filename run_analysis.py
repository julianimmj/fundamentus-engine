"""
run_analysis.py — Script standalone para GitHub Actions
Executa a análise completa e salva resultados em data/
"""
import json
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    os.makedirs("data", exist_ok=True)

    from engine.runner import run_full_analysis

    logger.info("Starting full analysis...")
    output = run_full_analysis(max_workers=6, use_cache=False)

    df = output.get("results")
    if df is None or df.empty:
        logger.error("No results generated!")
        sys.exit(1)

    # Save results CSV
    df.to_csv("data/analysis_results.csv", index=False)
    logger.info(f"Saved {len(df)} rows to data/analysis_results.csv")

    # Save macro snapshot JSON
    macro = {
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
    with open("data/macro_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(macro, f, ensure_ascii=False, indent=2, default=str)

    n_p = len(output.get("promissores", []))
    n_n = len(output.get("neutros", []))
    n_r = len(output.get("vies_ruim", []))
    logger.info(f"Analysis complete: {n_p} Promissores, {n_n} Neutros, {n_r} Vies Ruim")

if __name__ == "__main__":
    main()
