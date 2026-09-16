"""Settlement stewardship: preservation and anticipatory reproductive pacing."""

from statistics import mean


class Hestia:
    name = "Hestia"

    def step(self, sim):
        w, c = sim.world, sim.config
        if not sim.population or not c.hestia_enabled:
            w.preservation = 0.0
            w.preservation_workers = 0
            w.preservation_effort = 0.0
            w.estimated_food_supply = 0.0
            w.estimated_carrying_capacity = 0.0
            w.birth_policy = 1.0
            return

        food_need = sum(c.food_per_person * person.food_demand for person in sim.population)
        water_need = sum(c.water_per_person * person.water_demand for person in sim.population)
        if food_need == 0 and water_need == 0:
            w.preservation = 0.0
            w.preservation_workers = 0
            w.preservation_effort = 0.0
            w.estimated_food_supply = 0.0
            w.estimated_carrying_capacity = float(len(sim.population))
            w.birth_policy = 1.0
            return
        food_days = w.food / food_need if food_need else 0.0
        water_days = w.water / water_need if water_need else 0.0
        reserve_signal = min(1.0, food_days / c.preservation_food_days)
        w.preservation = c.preservation_max * reserve_signal
        # Preservation is a small shared practice, not a group permanently
        # assigned away from other life. It reduces every inhabitant's usable
        # work capacity by the same fraction.
        w.preservation_effort = c.preservation_labor_fraction * reserve_signal
        w.preservation_workers = 0

        # Include the production that already occurred this tick. Hestia used
        # to assess only an old history window before today's harvest, which
        # made reproductive pacing lag behind a recovering settlement.
        recent = sim.history[-(c.capacity_window - 1):] if c.capacity_window > 1 else []
        supplies = [
            row.get("farm_harvest", 0.0) + row.get("wild_harvest", 0.0)
            + row.get("thor_harvest", 0.0) + row.get("livestock_food", 0.0)
            for row in recent
        ]
        supplies.append(w.farm_harvest + w.wild_harvest + w.thor_harvest + w.livestock_food)
        w.estimated_food_supply = mean(supplies)
        per_person_need = food_need / len(sim.population)
        w.estimated_carrying_capacity = w.estimated_food_supply / per_person_need if per_person_need else 0.0

        reserve_factor = min(1.0, food_days / c.preservation_food_days, water_days / c.preservation_food_days)
        # Capacity is a noisy estimate, not an instant prohibition. Below the
        # configured floor births stop; between that floor and the estimate a
        # settlement can still replace ordinary deaths; a durable surplus
        # raises the chance of growth.
        support_ratio = w.estimated_carrying_capacity / len(sim.population)
        viable = min(1.0, max(0.0, (support_ratio - c.capacity_birth_floor) / (1 - c.capacity_birth_floor)))
        surplus = min(1.0, max(0.0, (support_ratio - 1.0) / 0.50))
        capacity_factor = viable * (0.35 + 0.65 * surplus)
        # Metis may slow growth under broad ecological pressure, but cannot
        # veto available reserves and capacity by itself.
        w.birth_policy = reserve_factor * capacity_factor * (1 - w.feedback_response * 0.35)
        if w.tick % c.governance_interval == 0:
            sim.log(self.name, f"Preservation {w.preservation:.0%}; food capacity {w.estimated_carrying_capacity:.1f}; birth policy {w.birth_policy:.0%}")
