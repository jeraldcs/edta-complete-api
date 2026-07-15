from app.empathy.contracts import ConstraintMatch, ImplicitConstraint


class ConstraintMatcher:
    """Score vehicle specs against implicit empathy constraints."""

    THRESHOLDS = {
        "low_step_in": lambda spec: spec.get("step_in_height_cm", 999) <= 52,
        "wide_door_opening": lambda spec: spec.get("step_in_height_cm", 999) <= 55,
        "easy_entry": lambda spec: spec.get("step_in_height_cm", 999) <= 50,
        "isofix_anchors": lambda spec: spec.get("isofix_count", 0) >= 2,
        "rear_legroom": lambda spec: spec.get("rear_legroom_score", 0) >= 0.75,
        "panoramic_roof": lambda spec: bool(spec.get("has_panoramic_roof")),
        "convertible_option": lambda spec: bool(spec.get("convertible")),
        "premium_audio": lambda spec: bool(spec.get("premium_audio")),
        "handling": lambda spec: spec.get("handling_score", 0) >= 0.75,
        "fold_flat_seats": lambda spec: bool(spec.get("fold_flat_seats")),
        "wide_tailgate": lambda spec: bool(spec.get("wide_tailgate")),
        "cargo_volume": lambda spec: spec.get("cargo_volume_cu_ft", 0) >= 50,
        "awd_preferred": lambda spec: bool(spec.get("awd")),
        "strong_engine": lambda spec: spec.get("engine_power_score", 0) >= 0.70,
    }

    def score_candidate(
        self,
        candidate_id: str,
        vehicle_spec: dict,
        constraints: list[ImplicitConstraint],
    ) -> ConstraintMatch:
        if not constraints:
            return ConstraintMatch(candidate_id=candidate_id, match_score=0.0)

        satisfied: list[str] = []
        gaps: list[str] = []
        weighted_score = 0.0
        total_weight = 0.0

        for constraint in constraints:
            checker = self.THRESHOLDS.get(constraint.constraint_id)
            total_weight += constraint.weight
            if checker and checker(vehicle_spec):
                satisfied.append(constraint.constraint_id)
                weighted_score += constraint.weight
            else:
                gaps.append(constraint.constraint_id)

        match_score = weighted_score / total_weight if total_weight else 0.0
        return ConstraintMatch(
            candidate_id=candidate_id,
            match_score=round(match_score, 4),
            satisfied=satisfied,
            gaps=gaps,
        )

    def score_all(
        self,
        vehicle_specs: dict[str, dict],
        constraints: list[ImplicitConstraint],
    ) -> dict[str, ConstraintMatch]:
        return {
            candidate_id: self.score_candidate(candidate_id, spec, constraints)
            for candidate_id, spec in vehicle_specs.items()
        }
