from pathlib import Path
import json
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dengue_research.app_exports import save_strict_json
from dengue_research.climate import build_master_features, classify_enso_phase
from dengue_research.epidemiology import causal_epidemiological_channel
from dengue_research.master import MasterConfig
from dengue_research.pipeline import load_weekly_data


def config() -> MasterConfig:
    return MasterConfig(
        data_path=PROJECT_ROOT / "data/dataset/processado/base_modelagem_dengue_dataset.xlsx"
    )


class MasterProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = config()
        cls.data = load_weekly_data(cls.cfg)
        cls.channel = causal_epidemiological_channel(cls.data, cls.cfg)
        cls.features, cls.groups = build_master_features(cls.data, cls.channel, cls.cfg)

    def test_local_climate_uses_at_least_one_week_delay(self):
        expected = self.data["media_temperatura_semana"].shift(1)
        pd.testing.assert_series_equal(
            self.features["media_temperatura_semana"], expected, check_names=False
        )

    def test_oni_uses_four_week_availability_delay(self):
        expected = self.data["ONI"].shift(4)
        pd.testing.assert_series_equal(self.features["ONI"], expected, check_names=False)

    def test_future_climate_mutation_does_not_change_past_features(self):
        cutoff = pd.Timestamp("2021-12-26")
        mutated = self.data.copy()
        mutated.loc[mutated.index > cutoff, "chuva_total_mm"] *= 1000
        changed, _ = build_master_features(mutated, self.channel, self.cfg)
        pd.testing.assert_series_equal(
            self.features.loc[:cutoff, "chuva_total_mm"],
            changed.loc[:cutoff, "chuva_total_mm"],
        )

    def test_feature_sets_separate_enso(self):
        self.assertIn("ONI", self.groups["full"])
        self.assertNotIn("ONI", self.groups["full_without_enso"])
        self.assertNotIn("ONI", self.groups["epidemiology_only"])
        self.assertIn("log_incidence_lag_1", self.groups["epidemiology_only"])

    def test_enso_operational_categories(self):
        values = pd.Series([-0.8, -0.2, 0.6, np.nan])
        self.assertEqual(
            classify_enso_phase(values).tolist(),
            ["la_nina", "neutro", "el_nino", "indisponivel"],
        )

    def test_strict_json_replaces_non_finite_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            save_strict_json(path, {"nan": np.nan, "inf": np.inf, "ok": np.float64(1.5)})
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("NaN", text)
            self.assertNotIn("Infinity", text)
            self.assertEqual(json.loads(text), {"nan": None, "inf": None, "ok": 1.5})


if __name__ == "__main__":
    unittest.main()
