from ..genetics import Organism, inherit


class Population:
    name = "Inhabitants"

    def step(self, sim):
        w, c = sim.world, sim.config
        w.births = w.deaths = 0
        if not sim.population:
            w.shortage = 0.0
            return
        demands = [(p, c.water_per_person * p.water_demand * (1 - w.conservation),
                    c.food_per_person * p.food_demand * (1 - w.conservation * 0.45)) for p in sim.population]
        water_need = sum(d[1] for d in demands)
        food_need = sum(d[2] for d in demands)
        water_share = min(1.0, w.water / water_need) if water_need else 1.0
        food_share = min(1.0, w.food / food_need) if food_need else 1.0
        w.water = max(0.0, w.water - water_need * water_share)
        w.food = max(0.0, w.food - food_need * food_share)
        w.shortage = 1 - min(water_share, food_share)
        w.pollution += len(sim.population) * c.pollution_per_person * (1 - w.conservation * 0.5)
        survivors = []
        for p, _, _ in demands:
            p.age += 1
            p.cooldown = max(0, p.cooldown - 1)
            exposure = max(0.0, w.pollution / (140 * p.tolerance) - 0.2) * 0.009
            recovery = 0.012 if w.shortage < 0.05 else 0.0
            p.health = min(1.0, p.health + recovery - w.shortage * c.starvation_damage - exposure)
            if p.health <= 0 or p.age >= c.max_age * p.lifespan:
                w.deaths += 1
            else:
                survivors.append(p)
        eligible = [p for p in survivors if p.age >= c.maturity_age and p.health > 0.75 and not p.cooldown]
        sim.life_rng.shuffle(eligible)
        children = []
        if w.shortage < 0.05:
            for first, second in zip(eligible[::2], eligible[1::2]):
                work_burden = (w.cultivation_effort + w.foraging_effort) / len(survivors) + w.preservation_effort if survivors else 0.0
                probability = c.birth_probability * (first.fecundity + second.fecundity) / 2 * (1 - w.cleanup * 0.45) * (1 - work_burden * c.work_reproduction_cost) * w.birth_policy
                if sim.life_rng.random() >= probability:
                    continue
                if len(survivors) + len(children) >= c.max_population:
                    w.population_limit_reached = True
                    continue
                if w.food < 3 or w.water < 1:
                    continue
                w.food -= 3
                w.water -= 1
                genome = inherit(first, second, sim.life_rng, c.mutation_rate)
                children.append(Organism(sim.next_id, genome, generation=max(first.generation, second.generation) + 1))
                sim.next_id += 1
                first.cooldown = second.cooldown = 30
                first.offspring += 1
                second.offspring += 1
        w.births = len(children)
        sim.population = survivors + children
        if w.births or w.deaths:
            sim.log(self.name, f"{w.births} births; {w.deaths} deaths; {len(sim.population)} alive")
