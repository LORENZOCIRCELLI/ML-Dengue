#!/usr/bin/env python3
"""Executa o estudo revisado e gera explicações Captum do desfecho principal."""

from __future__ import annotations

from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dengue_research.explainability import explain_torch_lstm
from dengue_research.pipeline import StudyConfig, run_study, save_json
from dengue_research.reporting import generate_all_reports


def main() -> None:
    config = StudyConfig(
        data_path=PROJECT_ROOT / "data/dataset/processado/base_modelagem_dengue_dataset.xlsx",
        output_dir=PROJECT_ROOT / "outputs/revisao_metodologica",
    )
    results, artifacts = run_study(config)

    explanations = {}
    for horizon in config.horizons:
        experiment = artifacts["exact"][horizon]
        sequence = experiment["sequence"]
        X_test, y_test, dates = sequence["arrays"]["test"]
        output_dir = config.output_dir / "exact" / f"{horizon:02d}_semanas" / "captum"
        probabilities = experiment["predictions"]["lstm_pytorch"]["test"]
        threshold = results["experiments"]["exact"][str(horizon)]["selection"]["lstm_pytorch"]["threshold"]
        explanations[str(horizon)] = explain_torch_lstm(
            experiment["models"]["lstm_pytorch"],
            X_test,
            y_test,
            dates,
            sequence["columns"],
            output_dir,
            sequence["device"],
            probabilities=probabilities,
            threshold=threshold,
        )
    save_json(config.output_dir / "captum_resumo.json", explanations)
    generate_all_reports(PROJECT_ROOT)
    print(json.dumps({"status": "concluido", "output_dir": str(config.output_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
