from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dengue_research.epidemiology import (
    EpidemiologicalConfig,
    causal_epidemiological_channel,
    create_epidemiological_targets,
    engineer_incidence_features,
)
from dengue_research.pipeline import assemble_samples, load_weekly_data, temporal_split


def study_config() -> EpidemiologicalConfig:
    return EpidemiologicalConfig(
        data_path=PROJECT_ROOT / "data/dataset/processado/base_modelagem_dengue_dataset.xlsx"
    )


class EpidemiologyTests(unittest.TestCase):
    def test_channel_is_causal_against_future_case_mutation(self):
        cfg = study_config()
        original = load_weekly_data(cfg)
        cutoff = pd.Timestamp("2021-12-26")
        mutated = original.copy()
        mutated.loc[mutated.index > cutoff, cfg.case_column] *= 100
        before = causal_epidemiological_channel(original, cfg).loc[:cutoff, "channel_upper"]
        after = causal_epidemiological_channel(mutated, cfg).loc[:cutoff, "channel_upper"]
        np.testing.assert_allclose(before, after, equal_nan=True)

    def test_exact_and_onset_window_targets_have_correct_timing(self):
        index = pd.date_range("2020-01-05", periods=12, freq="W-SUN")
        state = pd.Series([0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0], index=index, dtype="Float64")
        onset = pd.Series([0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0], index=index, dtype="Float64")
        targets = create_epidemiological_targets(state, onset, (4,))
        self.assertEqual(targets.loc[index[0], "target_exact_4"], state.iloc[4])
        self.assertEqual(targets.loc[index[0], "target_window_4"], 1)
        self.assertEqual(targets.loc[index[4], "target_window_4"], 1)

    def test_case_information_has_at_least_one_week_delay(self):
        cfg = study_config()
        data = load_weekly_data(cfg)
        channel = causal_epidemiological_channel(data, cfg)
        features = engineer_incidence_features(data, channel, cfg)
        expected = channel["incidence_per_100k"].shift(1)
        pd.testing.assert_series_equal(
            features["incidence_lag_1"], expected, check_names=False
        )

    def test_target_date_partitions_do_not_overlap(self):
        cfg = study_config()
        data = load_weekly_data(cfg)
        channel = causal_epidemiological_channel(data, cfg)
        targets = create_epidemiological_targets(
            channel["alert_state"], channel["alert_onset"], cfg.horizons
        )
        features = engineer_incidence_features(data, channel, cfg)
        sample = assemble_samples(features, targets, channel["alert_state"], 16, "exact")
        splits = temporal_split(sample, cfg)
        self.assertLessEqual(pd.to_datetime(splits["train"]["target_date"]).max(), pd.Timestamp(cfg.train_end))
        self.assertGreaterEqual(pd.to_datetime(splits["validation"]["target_date"]).min(), pd.Timestamp(cfg.validation_start))
        self.assertLessEqual(pd.to_datetime(splits["validation"]["target_date"]).max(), pd.Timestamp(cfg.validation_end))
        self.assertGreaterEqual(pd.to_datetime(splits["test"]["target_date"]).min(), pd.Timestamp(cfg.test_start))


if __name__ == "__main__":
    unittest.main()
