#!/usr/bin/env python3
"""Executa o Projeto Mestre completo ou uma verificação rápida."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dengue_research.master import MasterConfig, run_master_study
from dengue_research.master_reporting import generate_master_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Executa apenas quatro semanas com poucas épocas para teste técnico.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    common = {
        "data_path": PROJECT_ROOT / "data/dataset/processado/base_modelagem_dengue_dataset.xlsx",
        "output_dir": PROJECT_ROOT / (
            "outputs/projeto_mestre_quick" if args.quick else "outputs/projeto_mestre"
        ),
        "app_output_dir": PROJECT_ROOT / (
            "outputs/horizontes_quick" if args.quick else "outputs/horizontes"
        ),
    }
    if args.quick:
        config = MasterConfig(
            **common,
            horizons=(4,),
            target_kinds=("exact",),
            numpy_epochs=2,
            pytorch_epochs=2,
            early_stopping_patience=2,
            association_bootstrap=20,
            stability_seeds=(42,),
            model_version="master-quick-check",
        )
    else:
        config = MasterConfig(**common)
    results, _ = run_master_study(config)
    report = None
    if not args.quick:
        report = generate_master_report(PROJECT_ROOT)
    print(
        json.dumps(
            {
                "status": "concluido",
                "output_dir": str(config.output_dir),
                "app_output_dir": str(config.app_output_dir),
                "horizons": list(config.horizons),
                "experiments": list(results["experiments"]),
                "report": str(report) if report else None,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
