"""Gaia coordinates ticks and observations. Ecological intervention lives in systems."""

from dataclasses import asdict
import math
import random
from statistics import mean

from .config import Config
from .genetics import Creature, Organism
from .world import World
from .systems.environment import NaturalProcesses
from .systems.poseidon import Poseidon
from .systems.thor import Thor
from .systems.governance import Governance
from .systems.population import Population
from .systems.demeter import Demeter
from .systems.hestia import Hestia
from .systems.aristaeus import Aristaeus
from .systems.metis import Metis
from .systems.chloris import Chloris
from .events import apply_event, validate_event


class Simulation:
    def __init__(self, config=None):
        self.config = config or Config()
        self.world = World.create(self.config)
        # Weather has its own stream so equal seeds receive equal rain across modes.
        self.weather_rng = random.Random(f"weather:{self.config.seed}")
        self.life_rng = random.Random(f"life:{self.config.seed}")
        self.population = [self._founder(i) for i in range(self.config.initial_population)]
        self.next_id = self.config.initial_population
        self.next_creature_id = 1_000_000
        self.pollinators = [Creature(self.next_creature_id + index, "pollinator", age=self.life_rng.randint(0, self.config.pollinator_max_age // 2),
                                    resilience=self.life_rng.uniform(0.35, 0.65))
                             for index in range(self.config.initial_pollinators)]
        self.next_creature_id += self.config.initial_pollinators
        self.grazers = [Creature(self.next_creature_id + index, "grazer", age=self.life_rng.randint(0, self.config.grazer_max_age // 2),
                                 resilience=self.life_rng.uniform(0.35, 0.65))
                        for index in range(self.config.initial_grazers)]
        self.next_creature_id += self.config.initial_grazers
        # Replenishment precedes consumption. Metis and Hestia then assess the
        # current productive tick before governance and population decisions.
        self.systems = [NaturalProcesses(), Poseidon(), Chloris(), Aristaeus(), Demeter(), Thor(), Metis(), Hestia(), Governance(), Population()]
        self.events = []
        self.scheduled_events = []
        self.history = []
        self.log("Gaia", f"World initialized; seed {self.config.seed}; mode {self.config.mode}")
        self.record()

    def _founder(self, identifier):
        """Create a settled age distribution instead of an all-adult cohort.

        A world started from one randomly aged adult cohort suffers an
        artificial death wave before its first children can mature. Founders
        therefore include children, working-age adults, and elders. They are
        still ordinary organisms: no one is protected from death and future
        population only comes through Population.step().
        """
        genome = [self.life_rng.randint(0, 10) for _ in range(10)]
        organism = Organism(identifier, genome)
        lifespan = max(self.config.maturity_age + 1, int(self.config.max_age * organism.lifespan))
        phase = self.life_rng.random()
        if self.config.maturity_age and phase < 0.25:
            organism.age = self.life_rng.randint(0, self.config.maturity_age - 1)
        elif phase < 0.90:
            organism.age = self.life_rng.randint(self.config.maturity_age, max(self.config.maturity_age, int(lifespan * 0.65)))
        else:
            organism.age = self.life_rng.randint(max(self.config.maturity_age, int(lifespan * 0.65)), max(self.config.maturity_age, int(lifespan * 0.92)))
        return organism

    def log(self, system, message):
        self.events.append({"tick": self.world.tick, "system": system, "message": message})
        if len(self.events) > 500:
            del self.events[:-500]

    def step(self, ticks=1):
        if type(ticks) is not int or ticks < 0:
            raise ValueError("ticks must be a nonnegative integer")
        for _ in range(ticks):
            self.world.tick += 1
            due, self.scheduled_events = ([event for event in self.scheduled_events if event["at_tick"] == self.world.tick],
                                          [event for event in self.scheduled_events if event["at_tick"] != self.world.tick])
            for event in due:
                apply_event(self, event)
            for system in self.systems:
                system.step(self)
            self.check_invariants()
            self.record()
        return self

    def schedule_event(self, event):
        event = validate_event(event, self.world.tick)
        self.scheduled_events.append(event)
        self.scheduled_events.sort(key=lambda item: item["at_tick"])
        self.log("Event", f"Scheduled {event['kind']} for tick {event['at_tick']}")
        return event

    def check_invariants(self):
        w, c = self.world, self.config
        for name, maximum in (("water", c.water_capacity), ("food", c.food_capacity), ("wild_food", c.wild_food_capacity),
                              ("reservoir", c.reservoir_capacity), ("plant_biomass", c.plant_biomass_capacity),
                              ("seed_bank", c.seed_bank_capacity), ("fertility", 1.0)):
            value = getattr(w, name)
            if not math.isfinite(value) or not -1e-8 <= value <= maximum + 1e-8:
                raise RuntimeError(f"World invariant violated: {name}={value}")
        if not math.isfinite(w.pollution) or w.pollution < 0:
            raise RuntimeError("Pollution must remain finite and nonnegative")
        if w.pollinator_count != len(self.pollinators) or w.pollinator_count < 0:
            raise RuntimeError("Pollinator count must match the living population")
        if w.grazer_count != len(self.grazers) or w.grazer_count < 0:
            raise RuntimeError("Grazer count must match the living population")
        if len(self.population) > c.max_population:
            raise RuntimeError("Population exceeds computational limit")

    def record(self):
        row = asdict(self.world)
        row.update(population=len(self.population), mean_health=mean(p.health for p in self.population) if self.population else 0,
                   mean_food_demand=mean(p.food_demand for p in self.population) if self.population else 0,
                   mean_water_demand=mean(p.water_demand for p in self.population) if self.population else 0,
                   mean_tolerance=mean(p.tolerance for p in self.population) if self.population else 0,
                   max_generation=max((p.generation for p in self.population), default=0),
                   farm_labor_fraction=self.world.cultivation_effort / len(self.population) if self.population else 0,
                   mean_farmer_skill=self.world.mean_farmer_skill, mean_forager_skill=self.world.mean_forager_skill)
        self.history.append(row)

    def snapshot(self, history_limit=600):
        from .metrics import summarize
        stride = max(1, math.ceil(len(self.history) / history_limit))
        sampled = self.history[::stride]
        if sampled[-1] is not self.history[-1]:
            sampled.append(self.history[-1])
        return {"config": self.config.to_dict(), "current": self.history[-1], "summary": summarize(self),
                "history": sampled, "events": self.events[-50:],
                "inhabitants": [dict(name=p.name, age=p.age, health=p.health, generation=p.generation,
                                     offspring=p.offspring, genome=p.genome,
                                     cultivation_aptitude=p.cultivation_aptitude,
                                     foraging_aptitude=p.foraging_aptitude,
                                     cultivation_share=p.last_cultivation_share) for p in self.population[:30]],
                "species": {"pollinators": len(self.pollinators), "grazers": len(self.grazers)},
                "scheduled_events": self.scheduled_events}
