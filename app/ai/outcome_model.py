from pathlib import Path
import joblib
import pandas as pd
from app.models import OutcomeSimulation


FEATURES = [
    "eds_score",
    "semantic_similarity",
    "channel_fit",
    "trust_score",
    "business_value",
    "compliance_sensitivity",
    "fatigue_score",
]


class OutcomeSimulationModel:
    def __init__(self):
        self.conversion_model = joblib.load("models/outcome_conversion_model.joblib") if Path("models/outcome_conversion_model.joblib").exists() else None
        self.revenue_model = joblib.load("models/outcome_revenue_model.joblib") if Path("models/outcome_revenue_model.joblib").exists() else None

    @staticmethod
    def _heuristic_conversion(
        eds_score,
        semantic_similarity: float,
        channel_fit: float,
        tapl,
        candidate,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                eds_score.final_eds_score * 0.40
                + semantic_similarity * 0.20
                + channel_fit * 0.15
                + tapl.trust_score * 0.15
                + candidate.business_value * 0.10
                - tapl.fatigue_score * 0.08
                - candidate.compliance_sensitivity * 0.04,
            ),
        )

    @staticmethod
    def _apply_calibration(
        conversion_probability: float,
        revenue_impact: float,
        calibration: dict[str, float] | None,
    ) -> tuple[float, float]:
        if not calibration:
            return conversion_probability, revenue_impact

        historical_cvr = calibration.get("historical_cvr", 0.0)
        avg_revenue = calibration.get("avg_revenue_per_impression", 0.0)
        if historical_cvr > 0:
            blend = min(0.35, historical_cvr)
            conversion_probability = max(
                0.0,
                min(1.0, conversion_probability * (1 - blend) + historical_cvr * blend),
            )
        if avg_revenue > 0:
            revenue_impact = max(revenue_impact, avg_revenue * 100.0)
        return conversion_probability, revenue_impact

    def simulate(self, eds_score, semantic_similarity, channel_fit, tapl, candidate, calibration=None):
        feature_frame = pd.DataFrame([{
            "eds_score": eds_score.final_eds_score,
            "semantic_similarity": semantic_similarity,
            "channel_fit": channel_fit,
            "trust_score": tapl.trust_score,
            "business_value": candidate.business_value,
            "compliance_sensitivity": candidate.compliance_sensitivity,
            "fatigue_score": tapl.fatigue_score,
        }])

        heuristic_conversion = self._heuristic_conversion(
            eds_score,
            semantic_similarity,
            channel_fit,
            tapl,
            candidate,
        )

        if self.conversion_model and hasattr(self.conversion_model, "predict_proba"):
            ml_conversion = float(self.conversion_model.predict_proba(feature_frame)[0][1])
            if ml_conversion >= 0.98 or ml_conversion <= 0.02:
                conversion_probability = heuristic_conversion
            else:
                conversion_probability = round(
                    0.30 * ml_conversion + 0.70 * heuristic_conversion,
                    4,
                )
        else:
            conversion_probability = round(heuristic_conversion, 4)

        if self.revenue_model:
            revenue_impact = float(max(0.0, self.revenue_model.predict(feature_frame)[0]))
        else:
            revenue_impact = 100.0 * conversion_probability * candidate.business_value

        if revenue_impact <= 0.0:
            revenue_impact = 100.0 * conversion_probability * candidate.business_value

        conversion_probability, revenue_impact = self._apply_calibration(
            conversion_probability,
            revenue_impact,
            calibration,
        )

        trust_impact = max(0.0, min(1.0, tapl.trust_score - tapl.fatigue_score * 0.12))
        journey_impact = eds_score.journey_momentum_score
        compliance_risk = candidate.compliance_sensitivity
        fatigue_risk = max(0.0, min(1.0, tapl.fatigue_score + candidate.compliance_sensitivity * 0.15))

        expected_outcome_score = max(
            0.0,
            min(
                1.0,
                conversion_probability * 0.35
                + min(revenue_impact / 100.0, 1.0) * 0.20
                + trust_impact * 0.20
                + journey_impact * 0.15
                - compliance_risk * 0.05
                - fatigue_risk * 0.05,
            ),
        )

        return OutcomeSimulation(
            conversion_probability=round(conversion_probability, 4),
            revenue_impact=round(revenue_impact, 2),
            trust_impact=round(trust_impact, 4),
            journey_impact=round(journey_impact, 4),
            compliance_risk=round(compliance_risk, 4),
            fatigue_risk=round(fatigue_risk, 4),
            expected_outcome_score=round(expected_outcome_score, 4),
        )
