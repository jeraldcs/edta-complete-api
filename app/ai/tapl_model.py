from app.ai.model_utils import TextClassifier
from app.models import TAPLAction, TAPLDecision
from app.tapl_policy import TAPLPolicyEngine


class TAPLModel:
    def __init__(self):
        self.classifier = TextClassifier(
            model_path="models/tapl_model.joblib",
            labels=[x.value for x in TAPLAction],
            fallback_label=TAPLAction.show.value,
        )
        self.policy_engine = TAPLPolicyEngine()
        self.last_policy_source: str | None = None

    def evaluate(self, context, candidate, context_text: str) -> TAPLDecision:
        label, confidence, source = self.classifier.predict(
            context_text + " " + candidate.title + " " + candidate.description
        )

        consent_score = 1.0 if context.consent.get("personalization", False) else 0.0
        fatigue_count = int(context.profile_attributes.get("fatigue_count", 0) or 0)
        fatigue_score = min(1.0, fatigue_count / 10.0)
        memory_trust = float(context.profile_attributes.get("trust_score", 0.65) or 0.65)
        memory_trust = max(0.0, min(1.0, memory_trust))
        sensitivity_score = candidate.compliance_sensitivity
        compliance_score = max(0.0, 1.0 - candidate.compliance_sensitivity)

        trust_score = self.policy_engine.trust_score(
            consent_score=consent_score,
            memory_trust=memory_trust,
            compliance_score=compliance_score,
            fatigue_score=fatigue_score,
            sensitivity_score=sensitivity_score,
        )

        override_action, override_reason, policy_source = self.policy_engine.evaluate_overrides(
            consent_score=consent_score,
            fatigue_score=fatigue_score,
            channel=context.channel,
            compliance_sensitivity=candidate.compliance_sensitivity,
        )
        self.last_policy_source = policy_source

        if override_action is not None:
            action = override_action
            reason = override_reason or "TAPL policy override applied."
        else:
            action = TAPLAction(label)
            reason = f"TAPL model action={label}, confidence={confidence}, source={source}."
            policy_source = "model:classifier"

        self.last_policy_source = policy_source

        return TAPLDecision(
            action=action,
            trust_score=round(trust_score, 4),
            fatigue_score=round(fatigue_score, 4),
            sensitivity_score=round(sensitivity_score, 4),
            compliance_score=round(compliance_score, 4),
            reason=reason,
        )
