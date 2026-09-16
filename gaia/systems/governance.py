class Governance:
    """Resource conservation and cleanup effort; no resource injection."""

    name = "Governance"

    def step(self, sim):
        w, c = sim.world, sim.config
        if not c.governance_enabled or c.mode == "off":
            w.conservation = w.cleanup = 0.0
            return
        if w.tick % c.governance_interval == 0:
            if c.mode == "fixed":
                w.conservation, w.cleanup = 0.12, 0.3
            else:
                pressure = max(1 - min(w.water / (c.water_capacity * 0.4), w.food / (c.food_capacity * 0.4), 1),
                               w.feedback_response)
                w.conservation = max(0.0, min(0.4, pressure * 0.4))
                w.cleanup = min(0.8, w.pollution / 90)
            sim.log(self.name, f"Conservation {w.conservation:.0%}; cleanup effort {w.cleanup:.0%}")
        # Cleanup is a shared civic contribution made by all inhabitants. It
        # is not a third permanent occupation and therefore remains possible
        # even when everyone is contributing some adaptive food effort.
        labor = len(sim.population) * w.cleanup * 0.60
        spent = min(w.food, labor * 0.05)
        w.food -= spent
        effective_labor = min(labor, spent / 0.05)
        w.pollution = max(0.0, w.pollution - effective_labor * 0.4)
