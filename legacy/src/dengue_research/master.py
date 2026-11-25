"""Projeto Mestre: clima, ENSO, previsão, Captum e exportação para o app."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from .app_exports import export_horizon_app_payloads, save_strict_json
from .climate import (
    build_master_features,
    climate_lag_associations,
    enso_outcome_summary,
)
from .epidemiology import (
    EpidemiologicalConfig,
    causal_epidemiological_channel,
    create_epidemiological_targets,
    episode_table,
    episode_warning_metrics,
    population_audit,
    sensitivity_analysis,
)
from .explainability import explain_torch_lstm
from .pipeline import (
    NumpyLSTM,
    assemble_samples,
    audit_data,
    choose_operating_threshold,
    evaluate_predictions,
    fit_tabular_models,
    fit_torch_lstm,
    load_weekly_data,
    prepare_sequences,
    run_single_experiment,
    save_experiment_artifacts,
    save_json,
    set_reproducible_seed,
    temporal_split,
    torch_probabilities,
)


@dataclass(frozen=True)
class MasterConfig(EpidemiologicalConfig):
    """Protocolo congelado da especificação mestre."""

    output_dir: Path = Path("outputs/projeto_mestre")
    app_output_dir: Path = Path("outputs/horizontes")
    model_version: str = "master-1.0.0"
    source_notebook: str = "notebooks/Notebook_Mestre_Clima_Dengue.ipynb"
    association_bootstrap: int = 300
    stability_seeds: tuple[int, ...] = (42, 123, 2025)

    def to_json(self) -> dict:
        result = super().to_json()
        result["app_output_dir"] = str(self.app_output_dir)
        result["model_version"] = self.model_version
        result["source_notebook"] = self.source_notebook
        result["association_bootstrap"] = self.association_bootstrap
        result["stability_seeds"] = list(self.stability_seeds)
        return result


def _subset_splits(
    splits: dict[str, pd.DataFrame],
    feature_columns: list[str],
) -> dict[str, pd.DataFrame]:
    metadata = ["target", "current_outbreak", "issue_date", "target_date"]
    columns = feature_columns + metadata
    return {name: part.loc[:, columns].copy() for name, part in splits.items()}


def _tabular_ablation(
    base_artifacts: dict,
    groups: dict[str, list[str]],
    config: MasterConfig,
    horizon: int,
) -> tuple[dict, list[dict]]:
    """Compara grupos no mesmo conjunto de semanas para evitar comparação injusta."""
    results: dict = {}
    flat_rows: list[dict] = []
    for group_name in (
        "seasonal_only",
        "epidemiology_only",
        "climate_only",
        "full_without_enso",
    ):
        splits = _subset_splits(base_artifacts["splits"], groups[group_name])
        _, predictions, selection = fit_tabular_models(splits, config)
        metrics = evaluate_predictions(
            predictions,
            selection,
            config,
            seed_offset=2000 + horizon + len(results) * 100,
        )
        # Baselines sazonais e de persistência já aparecem no experimento completo.
        keep = {name: metrics[name] for name in ("logistic_regression", "random_forest")}
        results[group_name] = {"metrics": keep, "selection": selection}
        for model_name, model_values in keep.items():
            row = {
                "horizon_weeks": horizon,
                "feature_set": group_name,
                "model": model_name,
            }
            row.update(model_values["test"])
            row.pop("confidence_intervals", None)
            flat_rows.append(row)
    return results, flat_rows


def _sequence_variant_columns(
    full_columns: list[str],
    groups: dict[str, list[str]],
    feature_set: str,
) -> list[str]:
    allowed = set(groups[feature_set])
    columns = [column for column in full_columns if column in allowed]
    if not columns:
        raise ValueError(f"Nenhuma feature sequencial para {feature_set}.")
    return columns


def _torch_variant(
    *,
    name: str,
    features: pd.DataFrame,
    sample: pd.DataFrame,
    splits: dict[str, pd.DataFrame],
    columns: list[str],
    config: MasterConfig,
    horizon: int,
) -> tuple[dict, dict]:
    scaler, arrays = prepare_sequences(
        features, sample, splits, columns, config.sequence_length
    )
    model, history, device = fit_torch_lstm(arrays, len(columns), config)
    validation_probability = torch_probabilities(model, arrays["validation"][0], device)
    test_probability = torch_probabilities(model, arrays["test"][0], device)
    threshold, selection = choose_operating_threshold(
        arrays["validation"][1].astype(int),
        validation_probability,
        config.target_recall,
    )
    predictions = {
        name: {
            "validation": validation_probability,
            "test": test_probability,
            "y_validation": arrays["validation"][1].astype(int),
            "y_test": arrays["test"][1].astype(int),
        }
    }
    selected = {name: {"threshold": threshold, **selection}}
    metrics = evaluate_predictions(predictions, selected, config, 3000 + horizon)
    return (
        {"selection": selected[name], "metrics": metrics[name]},
        {
            "model": model,
            "history": history,
            "device": device,
            "scaler": scaler,
            "arrays": arrays,
            "columns": columns,
        },
    )


def _seed_stability(
    *,
    arrays: dict,
    input_size: int,
    config: MasterConfig,
    horizon: int,
    seed_42_metrics: dict,
) -> tuple[dict, list[dict]]:
    rows: list[dict] = []
    by_seed: dict = {}
    for seed in config.stability_seeds:
        if seed == config.seed:
            metrics = seed_42_metrics
        else:
            seeded = replace(config, seed=int(seed))
            model, _, device = fit_torch_lstm(arrays, input_size, seeded)
            validation_probability = torch_probabilities(model, arrays["validation"][0], device)
            test_probability = torch_probabilities(model, arrays["test"][0], device)
            threshold, selection = choose_operating_threshold(
                arrays["validation"][1].astype(int),
                validation_probability,
                config.target_recall,
            )
            predictions = {
                "lstm_pytorch": {
                    "validation": validation_probability,
                    "test": test_probability,
                    "y_validation": arrays["validation"][1].astype(int),
                    "y_test": arrays["test"][1].astype(int),
                }
            }
            metrics = evaluate_predictions(
                predictions,
                {"lstm_pytorch": {"threshold": threshold, **selection}},
                seeded,
                4000 + horizon + int(seed),
            )["lstm_pytorch"]
        by_seed[str(seed)] = metrics
        test = metrics["test"]
        rows.append(
            {
                "horizon_weeks": horizon,
                "seed": int(seed),
                "pr_auc": test["pr_auc"],
                "roc_auc": test["roc_auc"],
                "precision": test["precision"],
                "recall": test["recall_sensitivity"],
                "brier": test["brier"],
                "false_alarms_per_year": test["false_alarms_per_year"],
            }
        )
    frame = pd.DataFrame(rows)
    summary = {
        "by_seed": by_seed,
        "n_seeds": int(len(frame)),
        "pr_auc_mean": float(frame["pr_auc"].mean()),
        "pr_auc_sd": float(frame["pr_auc"].std(ddof=1)) if len(frame) > 1 else 0.0,
        "pr_auc_min": float(frame["pr_auc"].min()),
        "pr_auc_max": float(frame["pr_auc"].max()),
    }
    return summary, rows


def run_master_study(config: MasterConfig) -> tuple[dict, dict]:
    """Executa a análise final sem alterar os dois projetos anteriores."""
    set_reproducible_seed(config.seed)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    data = load_weekly_data(config)
    audit = audit_data(data, config)
    pop_audit = population_audit(data, config)
    channel = causal_epidemiological_channel(data, config)
    targets = create_epidemiological_targets(
        channel["alert_state"], channel["alert_onset"], config.horizons
    )
    features, groups = build_master_features(data, channel, config)
    episodes = episode_table(channel)
    sensitivity = sensitivity_analysis(data, channel, config)
    associations = climate_lag_associations(
        features,
        channel,
        config.horizons,
        seed=config.seed,
        n_bootstrap=config.association_bootstrap,
    )
    enso_summary = enso_outcome_summary(data, channel, config.horizons)

    save_strict_json(config.output_dir / "configuracao.json", config.to_json())
    save_strict_json(config.output_dir / "auditoria_dados.json", audit)
    save_strict_json(config.output_dir / "auditoria_denominador.json", pop_audit)
    save_strict_json(config.output_dir / "grupos_atributos.json", groups)
    channel.to_csv(config.output_dir / "canal_endemico.csv", index_label="data")
    features.to_csv(config.output_dir / "atributos_mestres.csv", index_label="data")
    episodes.to_csv(config.output_dir / "episodios_alerta.csv", index=False)
    sensitivity.to_csv(config.output_dir / "sensibilidade_definicao.csv", index=False)
    associations.to_csv(config.output_dir / "associacoes_climaticas.csv", index=False)
    enso_summary.to_csv(config.output_dir / "resumo_enso.csv", index=False)

    results: dict = {
        "config": config.to_json(),
        "scope": {
            "primary_question": (
                "variáveis climáticas e ENSO acrescentam capacidade de antecipar alertas de dengue?"
            ),
            "primary_outcome": "estado de alerta epidemiológico exatamente em t+h",
            "secondary_outcome": "início de episódio entre t+1 e t+h",
            "primary_definition": "canal endêmico causal em incidência",
            "sensitivity_definition": "P75 causal do projeto 1",
            "geographic_scope": "Ribeirão Preto",
            "claim_boundary": "associação e contribuição preditiva; não causalidade",
        },
        "data_audit": audit,
        "population_audit": pop_audit,
        "episodes": {
            "n": int(len(episodes)),
            "records": episodes.assign(
                start=episodes["start"].astype(str), end=episodes["end"].astype(str)
            ).to_dict(orient="records"),
        },
        "climate_association": {
            "method": "Spearman com bootstrap móvel de oito semanas",
            "warning": "associação descritiva; não causal",
            "n_rows": int(len(associations)),
        },
        "experiments": {},
        "ablation": {},
        "sequence_ablation": {},
        "seed_stability": {},
        "captum": {},
        "app_exports": {},
    }
    artifacts: dict = {}
    ablation_rows: list[dict] = []
    stability_rows: list[dict] = []

    for target_kind in config.target_kinds:
        results["experiments"][target_kind] = {}
        artifacts[target_kind] = {}
        baseline_state = channel["alert_state"] if target_kind == "exact" else channel["alert_onset"]
        for horizon in config.horizons:
            print(
                f"[mestre] alvo={target_kind}, horizonte={horizon}: modelos completos",
                flush=True,
            )
            experiment, experiment_artifacts = run_single_experiment(
                data,
                features[groups["full"]],
                targets,
                baseline_state,
                horizon,
                target_kind,
                config,
            )
            if target_kind == "window":
                episode_metrics = {}
                for model_name, prediction_values in experiment_artifacts["predictions"].items():
                    dates = (
                        experiment_artifacts["sequence"]["arrays"]["test"][2]
                        if model_name.startswith("lstm_")
                        else experiment_artifacts["splits"]["test"].index
                    )
                    episode_metrics[model_name] = episode_warning_metrics(
                        dates,
                        prediction_values["test"],
                        experiment["selection"][model_name]["threshold"],
                        channel["alert_onset"],
                        horizon,
                        config,
                    )
                experiment["episode_metrics"] = episode_metrics
            results["experiments"][target_kind][str(horizon)] = experiment
            artifacts[target_kind][horizon] = experiment_artifacts
            experiment_dir = config.output_dir / target_kind / f"{horizon:02d}_semanas"
            save_strict_json(experiment_dir / "resultados.json", experiment)
            save_experiment_artifacts(experiment_dir, experiment, experiment_artifacts)

            if target_kind != "exact":
                continue

            print(f"[mestre] horizonte={horizon}: análise com e sem clima", flush=True)
            ablation, rows = _tabular_ablation(
                experiment_artifacts, groups, config, horizon
            )
            # Inclui o conjunto completo já treinado, sem repetir o ajuste.
            ablation["full"] = {
                "metrics": {
                    name: experiment["metrics"][name]
                    for name in ("logistic_regression", "random_forest")
                },
                "selection": {
                    name: experiment["selection"][name]
                    for name in ("logistic_regression", "random_forest")
                },
            }
            for model_name in ("logistic_regression", "random_forest"):
                row = {
                    "horizon_weeks": horizon,
                    "feature_set": "full",
                    "model": model_name,
                }
                row.update(experiment["metrics"][model_name]["test"])
                row.pop("confidence_intervals", None)
                rows.append(row)
            results["ablation"][str(horizon)] = ablation
            ablation_rows.extend(rows)

            full_columns = experiment_artifacts["sequence"]["columns"]
            sequence_results = {}
            for feature_set in ("epidemiology_only", "full_without_enso"):
                columns = _sequence_variant_columns(full_columns, groups, feature_set)
                variant_result, variant_artifacts = _torch_variant(
                    name=f"lstm_pytorch_{feature_set}",
                    features=features,
                    sample=experiment_artifacts["sample"],
                    splits=experiment_artifacts["splits"],
                    columns=columns,
                    config=config,
                    horizon=horizon,
                )
                sequence_results[feature_set] = variant_result
                variant_dir = experiment_dir / "variantes_lstm" / feature_set
                variant_dir.mkdir(parents=True, exist_ok=True)
                variant_artifacts["history"].to_csv(
                    variant_dir / "historico.csv", index=False
                )
                save_strict_json(variant_dir / "resultados.json", variant_result)
            sequence_results["full"] = {
                "selection": experiment["selection"]["lstm_pytorch"],
                "metrics": experiment["metrics"]["lstm_pytorch"],
            }
            results["sequence_ablation"][str(horizon)] = sequence_results

            print(f"[mestre] horizonte={horizon}: estabilidade da LSTM", flush=True)
            stability, rows = _seed_stability(
                arrays=experiment_artifacts["sequence"]["arrays"],
                input_size=len(full_columns),
                config=config,
                horizon=horizon,
                seed_42_metrics=experiment["metrics"]["lstm_pytorch"],
            )
            results["seed_stability"][str(horizon)] = stability
            stability_rows.extend(rows)

            print(f"[mestre] horizonte={horizon}: Captum e JSONs", flush=True)
            X_test, y_test, dates = experiment_artifacts["sequence"]["arrays"]["test"]
            captum_dir = experiment_dir / "captum"
            captum_summary = explain_torch_lstm(
                experiment_artifacts["models"]["lstm_pytorch"],
                X_test,
                y_test,
                dates,
                full_columns,
                captum_dir,
                experiment_artifacts["sequence"]["device"],
                probabilities=experiment_artifacts["predictions"]["lstm_pytorch"]["test"],
                threshold=experiment["selection"]["lstm_pytorch"]["threshold"],
            )
            results["captum"][str(horizon)] = captum_summary
            exported = export_horizon_app_payloads(
                app_root=config.app_output_dir,
                horizon=horizon,
                features=features,
                raw_data=data,
                channel=channel,
                experiment=experiment,
                artifacts=experiment_artifacts,
                global_explanation_dir=captum_dir,
                model_version=config.model_version,
                source_notebook=config.source_notebook,
            )
            results["app_exports"][str(horizon)] = {
                name: str(path) for name, path in exported.items()
            }

    pd.DataFrame(ablation_rows).to_csv(
        config.output_dir / "comparacao_com_sem_clima.csv", index=False
    )
    pd.DataFrame(stability_rows).to_csv(
        config.output_dir / "estabilidade_lstm_sementes.csv", index=False
    )
    save_strict_json(config.output_dir / "resultados_completos.json", results)
    return results, artifacts
