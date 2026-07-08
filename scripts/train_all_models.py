from pathlib import Path
import pandas as pd
import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import GradientBoostingClassifier

Path("models").mkdir(exist_ok=True)

MASTER_SCENARIO_PATH = Path("data/scenario_training_master.csv")
GENERATED_DIR = Path("data/generated")

CANDIDATE_PROFILES = {
    "vehicle_upgrade_suv": {"business_value": 0.90, "compliance_sensitivity": 0.10, "base_revenue": 160},
    "early_booking_discount": {"business_value": 0.70, "compliance_sensitivity": 0.05, "base_revenue": 85},
    "hotel_reservation_assist": {"business_value": 0.84, "compliance_sensitivity": 0.05, "base_revenue": 130},
    "hotel_room_offer": {"business_value": 0.80, "compliance_sensitivity": 0.05, "base_revenue": 115},
    "restaurant_reservation_assist": {"business_value": 0.76, "compliance_sensitivity": 0.05, "base_revenue": 55},
    "restaurant_menu_recommendation": {"business_value": 0.68, "compliance_sensitivity": 0.03, "base_revenue": 42},
    "mobile_restaurant_qr_menu": {"business_value": 0.72, "compliance_sensitivity": 0.03, "base_revenue": 38},
    "mobile_restaurant_dish_promo": {"business_value": 0.84, "compliance_sensitivity": 0.03, "base_revenue": 48},
    "obesity_product_hcp_education": {"business_value": 0.82, "compliance_sensitivity": 0.85, "base_revenue": 0},
    "hcp_education_content": {"business_value": 0.65, "compliance_sensitivity": 0.80, "base_revenue": 0},
    "chatbot_booking_assist": {"business_value": 0.78, "compliance_sensitivity": 0.15, "base_revenue": 75},
    "connected_car_location_assist": {"business_value": 0.72, "compliance_sensitivity": 0.30, "base_revenue": 35},
    "wearable_health_nudge": {"business_value": 0.55, "compliance_sensitivity": 0.75, "base_revenue": 0},
}

INTENT_STRENGTH = {
    "purchase": 0.96,
    "upgrade": 0.90,
    "research": 0.74,
    "support": 0.62,
    "retention": 0.58,
    "unknown": 0.35,
}

JOURNEY_STRENGTH = {
    "purchase": 0.96,
    "consideration": 0.82,
    "research": 0.66,
    "awareness": 0.52,
    "service": 0.60,
    "retention": 0.56,
}

CHANNEL_FIT = {
    "web": 0.90,
    "mobile": 0.86,
    "chatbot": 0.82,
    "connected_car": 0.72,
    "email": 0.74,
    "wearable": 0.52,
}

TAPL_FACTORS = {
    "show": {"trust": 0.94, "fatigue": 0.08, "outcome": 1.00, "selected": 1},
    "soften": {"trust": 0.82, "fatigue": 0.24, "outcome": 0.78, "selected": 1},
    "delay": {"trust": 0.66, "fatigue": 0.74, "outcome": 0.44, "selected": 0},
    "suppress": {"trust": 0.36, "fatigue": 0.54, "outcome": 0.12, "selected": 0},
    "generic_fallback": {"trust": 0.48, "fatigue": 0.30, "outcome": 0.18, "selected": 0},
}


def _bounded(value, low=0.0, high=1.0):
    return round(max(low, min(high, value)), 4)


def _scenario_features(row):
    profile = CANDIDATE_PROFILES.get(
        row["expected_candidate_id"],
        {"business_value": 0.60, "compliance_sensitivity": 0.20, "base_revenue": 25},
    )
    tapl = TAPL_FACTORS.get(row["tapl_action"], TAPL_FACTORS["show"])
    intent_score = INTENT_STRENGTH.get(row["intent"], 0.35)
    journey_score = JOURNEY_STRENGTH.get(row["journey_stage"], 0.60)
    channel_fit = CHANNEL_FIT.get(row["channel"], 0.70)
    business_value = profile["business_value"]
    compliance = profile["compliance_sensitivity"]

    domain_adjustment = {
        "car_rental": 0.04,
        "hotel": 0.03,
        "restaurant": 0.01,
        "healthcare": -0.04,
    }.get(row["domain"], 0.0)
    semantic_similarity = _bounded(
        0.50
        + intent_score * 0.16
        + journey_score * 0.12
        + business_value * 0.10
        - compliance * 0.08
        + domain_adjustment
    )
    eds_score = _bounded(
        intent_score * 0.30
        + journey_score * 0.22
        + semantic_similarity * 0.20
        + business_value * 0.20
        + channel_fit * 0.08
        - compliance * 0.08
    )
    outcome_score = _bounded(
        eds_score * 0.32
        + semantic_similarity * 0.18
        + channel_fit * 0.16
        + tapl["trust"] * 0.16
        + business_value * 0.12
        - tapl["fatigue"] * 0.10
        - compliance * 0.08
    ) * tapl["outcome"]
    outcome_score = _bounded(outcome_score)
    conversion = int(outcome_score >= 0.58 and tapl["selected"] == 1)
    revenue = round(profile["base_revenue"] * outcome_score * conversion, 2)

    return {
        "eds_score": eds_score,
        "semantic_similarity": semantic_similarity,
        "channel_fit": round(channel_fit, 4),
        "trust_score": round(tapl["trust"], 4),
        "outcome_score": outcome_score,
        "business_value": round(business_value, 4),
        "compliance_sensitivity": round(compliance, 4),
        "fatigue_score": round(tapl["fatigue"], 4),
        "converted": conversion,
        "revenue": revenue,
        "selected": int(tapl["selected"] == 1),
    }


def sync_training_data_from_master():
    """Use one labeled scenario file to refresh the text-model CSVs."""
    if not MASTER_SCENARIO_PATH.exists():
        return {
            "intent": "data/intent_training.csv",
            "journey": "data/journey_training.csv",
            "tapl": "data/tapl_training.csv",
            "outcome": "data/outcome_training.csv",
            "ranker": "data/final_ranker_training.csv",
        }

    df = pd.read_csv(MASTER_SCENARIO_PATH)
    required = {
        "scenario_text",
        "intent",
        "journey_stage",
        "tapl_action",
        "domain",
        "channel",
        "expected_candidate_id",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(
            f"{MASTER_SCENARIO_PATH} is missing columns: {', '.join(sorted(missing))}"
        )

    GENERATED_DIR.mkdir(exist_ok=True)
    paths = {
        "intent": GENERATED_DIR / "intent_training.csv",
        "journey": GENERATED_DIR / "journey_training.csv",
        "tapl": GENERATED_DIR / "tapl_training.csv",
        "outcome": GENERATED_DIR / "outcome_training.csv",
        "ranker": GENERATED_DIR / "final_ranker_training.csv",
    }

    df[["scenario_text", "intent"]].rename(
        columns={"scenario_text": "text"}
    ).to_csv(paths["intent"], index=False)
    df[["scenario_text", "journey_stage"]].rename(
        columns={"scenario_text": "text"}
    ).to_csv(paths["journey"], index=False)
    df[["scenario_text", "tapl_action"]].rename(
        columns={"scenario_text": "text", "tapl_action": "action"}
    ).to_csv(paths["tapl"], index=False)

    feature_rows = [_scenario_features(row) for row in df.to_dict(orient="records")]
    feature_df = pd.DataFrame(feature_rows)
    feature_df[
        [
            "eds_score",
            "semantic_similarity",
            "channel_fit",
            "trust_score",
            "business_value",
            "compliance_sensitivity",
            "fatigue_score",
            "converted",
            "revenue",
        ]
    ].to_csv(paths["outcome"], index=False)
    feature_df[
        [
            "eds_score",
            "semantic_similarity",
            "channel_fit",
            "trust_score",
            "outcome_score",
            "business_value",
            "compliance_sensitivity",
            "selected",
        ]
    ].to_csv(paths["ranker"], index=False)

    print(f"Generated training CSVs from {MASTER_SCENARIO_PATH}")
    return paths


def train_text_classifier(data_path, model_path):
    df = pd.read_csv(data_path)
    text_col = "text"
    label_col = [c for c in df.columns if c != text_col][0]

    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("classifier", LogisticRegression(max_iter=1000)),
    ])
    model.fit(df[text_col], df[label_col])
    joblib.dump(model, model_path)
    print(f"Saved {model_path}")


def train_outcome_models(data_path):
    df = pd.read_csv(data_path)
    features = [
        "eds_score",
        "semantic_similarity",
        "channel_fit",
        "trust_score",
        "business_value",
        "compliance_sensitivity",
        "fatigue_score",
    ]

    conversion = GradientBoostingClassifier(random_state=42)
    conversion.fit(df[features], df["converted"])
    joblib.dump(conversion, "models/outcome_conversion_model.joblib")

    revenue = LinearRegression()
    revenue.fit(df[features], df["revenue"])
    joblib.dump(revenue, "models/outcome_revenue_model.joblib")

    print("Saved outcome models")


def train_final_ranker(data_path):
    df = pd.read_csv(data_path)
    features = [
        "eds_score",
        "semantic_similarity",
        "channel_fit",
        "trust_score",
        "outcome_score",
        "business_value",
        "compliance_sensitivity",
    ]

    model = GradientBoostingClassifier(random_state=42)
    model.fit(df[features], df["selected"])
    joblib.dump(model, "models/final_ranker_model.joblib")
    print("Saved final ranker model")


if __name__ == "__main__":
    generated_paths = sync_training_data_from_master()
    train_text_classifier(generated_paths["intent"], "models/intent_model.joblib")
    train_text_classifier(generated_paths["journey"], "models/journey_model.joblib")
    train_text_classifier(generated_paths["tapl"], "models/tapl_model.joblib")
    train_outcome_models(generated_paths["outcome"])
    train_final_ranker(generated_paths["ranker"])
