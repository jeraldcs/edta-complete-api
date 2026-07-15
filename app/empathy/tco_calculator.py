from app.empathy.contracts import EnrichmentBundle, RouteProfile, TripModel, WeatherSnapshot


class TCOCalculator:
    """Estimate total trip cost including fuel for vehicle recommendations."""

    EV_KWH_PER_MILE = 0.32
    EV_PRICE_PER_KWH = 0.18

    def estimate_fuel_cost(
        self,
        vehicle_spec: dict,
        distance_miles: float,
        gas_price_usd: float,
    ) -> float:
        fuel_type = (vehicle_spec.get("fuel_type") or "gas").lower()
        if fuel_type == "ev":
            return round(distance_miles * self.EV_KWH_PER_MILE * self.EV_PRICE_PER_KWH, 2)
        mpg = float(vehicle_spec.get("mpg_highway") or vehicle_spec.get("mpg_city") or 30)
        gallons = distance_miles / max(mpg, 1.0)
        return round(gallons * gas_price_usd, 2)

    def breakdown(
        self,
        candidate_id: str,
        vehicle_spec: dict,
        trip: TripModel,
        gas_price_usd: float,
        baseline_spec: dict | None = None,
        baseline_id: str | None = None,
    ):
        from app.empathy.contracts import TCOBreakdown

        distance = float(trip.distance_miles or 0)
        rental_days = int(trip.rental_days or 3)
        daily_rate = float(vehicle_spec.get("daily_rate_usd") or 0)
        fuel_cost = self.estimate_fuel_cost(vehicle_spec, distance, gas_price_usd) if distance else 0.0
        daily_total = daily_rate * rental_days
        total = round(daily_total + fuel_cost, 2)

        net_savings = None
        pitch = ""
        if baseline_spec and baseline_id and baseline_id != candidate_id:
            baseline_daily = float(baseline_spec.get("daily_rate_usd") or 0)
            baseline_fuel = self.estimate_fuel_cost(baseline_spec, distance, gas_price_usd) if distance else 0.0
            baseline_total = baseline_daily * rental_days + baseline_fuel
            net_savings = round(baseline_total - total, 2)
            daily_delta = daily_rate - baseline_daily
            fuel_delta = baseline_fuel - fuel_cost
            if net_savings and net_savings > 0:
                pitch = (
                    f"While this {vehicle_spec.get('title', candidate_id)} costs "
                    f"${abs(daily_delta):.0f}/day more than the compact gas car, "
                    f"it will save you ${fuel_delta:.0f} in fuel on your {distance:.0f}-mile route, "
                    f"saving you ${net_savings:.0f} overall."
                )
            elif distance:
                pitch = (
                    f"Estimated trip cost: ${total:.0f} "
                    f"(${daily_total:.0f} rental + ${fuel_cost:.0f} fuel) "
                    f"for {distance:.0f} miles over {rental_days} days."
                )
        elif distance:
            pitch = (
                f"Estimated trip cost: ${total:.0f} "
                f"(${daily_total:.0f} rental + ${fuel_cost:.0f} fuel)."
            )

        return TCOBreakdown(
            candidate_id=candidate_id,
            daily_rate_total=round(daily_total, 2),
            estimated_fuel_cost=fuel_cost,
            total_trip_cost=total,
            vs_baseline_candidate_id=baseline_id,
            net_savings=net_savings,
            recommendation_pitch=pitch,
        )

    def compare_candidates(
        self,
        vehicle_specs: dict[str, dict],
        trip: TripModel,
        enrichment: EnrichmentBundle,
        ranked_ids: list[str],
        baseline_id: str = "economy_compact",
    ):
        baseline_spec = vehicle_specs.get(baseline_id)
        if not baseline_spec:
            return []

        comparisons = []
        for candidate_id in ranked_ids:
            spec = vehicle_specs.get(candidate_id)
            if not spec:
                continue
            comparisons.append(
                self.breakdown(
                    candidate_id,
                    spec,
                    trip,
                    enrichment.gas_price_usd,
                    baseline_spec=baseline_spec,
                    baseline_id=baseline_id,
                )
            )
        return comparisons
