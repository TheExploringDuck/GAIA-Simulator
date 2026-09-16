"""Adaptive food gathering: traits and conditions, not preset social roles."""


class Demeter:
    name = "Demeter"

    def step(self, sim):
        w, c = sim.world, sim.config
        w.wild_harvest = w.farm_harvest = 0.0
        w.farm_workers = w.foragers = 0
        w.cultivation_effort = w.foraging_effort = 0.0
        w.cultivation_contributors = w.foraging_contributors = 0
        if not sim.population:
            return

        population = len(sim.population)
        w.mean_cultivation_aptitude = sum(p.cultivation_aptitude for p in sim.population) / population
        w.mean_foraging_aptitude = sum(p.foraging_aptitude for p in sim.population) / population
        # Each person has a limited amount of general effort. Its amount rises
        # under scarcity, while its direction is decided independently from
        # inherited aptitude, learned payoff, and the world now present.
        pantry_ratio = min(1.0, w.food / (c.food_capacity * 0.45))
        shortage_pressure = max(0.0, 1 - pantry_ratio)
        available_effort = population * max(0.0, 1 - w.preservation_effort)
        total_effort = available_effort * min(1.0, c.work_intensity + shortage_pressure * c.scarcity_work_response)
        farm_conditions = w.fertility * min(1.0, w.water / (c.water_capacity * 0.15))
        forage_conditions = min(1.0, w.wild_food / max(1.0, c.wild_food_capacity * 0.20))
        decisions = []
        for person in sim.population:
            # Cultivation retains a baseline pull because it replenishes the
            # pantry. Conditions and past payoff can change the mix, but a
            # single poor harvest must not make the settlement abandon farming.
            farm_score = (person.cultivation_aptitude * (0.80 + 0.80 * shortage_pressure) * (0.60 + 0.40 * farm_conditions) * (0.80 + 0.20 * person.cultivation_memory)
                          if c.demeter_enabled else 0.0)
            forage_score = person.foraging_aptitude * (0.25 + 0.75 * forage_conditions) * (0.80 + 0.20 * person.foraging_memory)
            cultivation_share = farm_score / (farm_score + forage_score) if farm_score + forage_score else 0.5
            person.last_cultivation_share = cultivation_share
            effort = total_effort / population
            cultivation_effort = effort * cultivation_share
            foraging_effort = effort - cultivation_effort
            decisions.append((person, cultivation_effort, foraging_effort))

        w.cultivation_effort = sum(item[1] for item in decisions)
        w.foraging_effort = sum(item[2] for item in decisions)
        w.mean_cultivation_share = sum(person.last_cultivation_share for person in sim.population) / population
        # Legacy count fields now mean contributors, not assigned occupations.
        w.cultivation_contributors = w.farm_workers = sum(effort > 0.05 for _, effort, _ in decisions)
        w.foraging_contributors = w.foragers = sum(effort > 0.05 for _, _, effort in decisions)
        w.mean_farmer_skill = (sum(person.cultivation_aptitude * effort for person, effort, _ in decisions) / w.cultivation_effort
                               if w.cultivation_effort else 0.0)
        w.mean_forager_skill = (sum(person.foraging_aptitude * effort for person, _, effort in decisions) / w.foraging_effort
                                if w.foraging_effort else 0.0)

        forage_work = sum(person.foraging_aptitude * effort for person, _, effort in decisions)
        potential_forage = forage_work * c.forage_per_inhabitant
        wild_harvest = w.harvest_wild_food(potential_forage, c)

        farm_work = sum(person.cultivation_aptitude * effort for person, effort, _ in decisions)
        if not farm_work:
            self._learn(decisions, c, 0.0, wild_harvest / potential_forage if potential_forage else 0.0)
            return
        labor_factor = farm_work / (farm_work + c.effort_half_saturation)
        water_factor = min(1.0, w.water / (c.water_capacity * 0.15))
        pollution_factor = 1 / (1 + w.pollution / 120)
        potential = c.farm_yield * c.farm_land * labor_factor * w.fertility * water_factor * pollution_factor * (1 + w.pollination_bonus)
        harvested = w.grow_farm_food(potential, c)
        self._learn(decisions, c, harvested / potential if potential else 0.0,
                    wild_harvest / potential_forage if potential_forage else 0.0)
        if harvested:
            w.pollution += harvested * c.farm_pollution_per_food
            sim.log(self.name, f"Cultivation effort {w.cultivation_effort:.1f}; foraging effort {w.foraging_effort:.1f}; harvested {harvested:.1f} farm and {w.wild_harvest:.1f} wild food")

    @staticmethod
    def _learn(decisions, config, cultivation_success, foraging_success):
        """Successful effort strengthens a temporary preference, never a role."""
        rate = config.strategy_learning_rate
        for person, _, _ in decisions:
            person.cultivation_memory += rate * (cultivation_success - person.cultivation_memory)
            person.foraging_memory += rate * (foraging_success - person.foraging_memory)
