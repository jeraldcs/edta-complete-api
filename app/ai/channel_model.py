from app.models import Channel


class ChannelFitModel:
    def score(self, channel: Channel, candidate_type: str, compliance_sensitivity: float) -> float:
        score = 0.75

        if channel == Channel.web:
            score += 0.10
        if channel in {Channel.chatbot, Channel.call_center} and candidate_type in {
            "next_best_action",
            "agent_script",
        }:
            score += 0.15
        if channel in {Channel.iot, Channel.wearable, Channel.connected_car} and candidate_type == "micro_prompt":
            score += 0.15
        if channel in {Channel.iot, Channel.wearable, Channel.connected_car, Channel.voice_assistant} and compliance_sensitivity >= 0.70:
            score -= 0.25
        if channel in {Channel.sms, Channel.push, Channel.wearable} and candidate_type in {"content", "long_form"}:
            score -= 0.20

        return round(max(0.0, min(1.0, score)), 4)
