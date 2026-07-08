from pathlib import Path
import joblib
import pandas as pd


FEATURES = [
    "eds_score",
    "semantic_similarity",
    "channel_fit",
    "trust_score",
    "outcome_score",
    "business_value",
    "compliance_sensitivity",
]


class FinalRankerModel:
    def __init__(self):
        self.model = joblib.load("models/final_ranker_model.joblib") if Path("models/final_ranker_model.joblib").exists() else None

    def score(self, eds_score, semantic_similarity, channel_fit, tapl, outcome, candidate):
        feature_frame = pd.DataFrame([{
            "eds_score": eds_score.final_eds_score,
            "semantic_similarity": semantic_similarity,
            "channel_fit": channel_fit,
            "trust_score": tapl.trust_score,
            "outcome_score": outcome.expected_outcome_score,
            "business_value": candidate.business_value,
            "compliance_sensitivity": candidate.compliance_sensitivity,
        }])

        if self.model and hasattr(self.model, "predict_proba"):
            return round(float(self.model.predict_proba(feature_frame)[0][1]), 4)

        return round(max(0.0, min(1.0, (
            eds_score.final_eds_score * 0.25
            + semantic_similarity * 0.15
            + channel_fit * 0.10
            + tapl.trust_score * 0.15
            + outcome.expected_outcome_score * 0.25
            + candidate.business_value * 0.10
            - candidate.compliance_sensitivity * 0.05
        ))), 4)
