from dataclasses import dataclass


@dataclass
class World:
    water: float
    food: float
    reservoir: float
    pollution: float
    fertility: float
    tick: int = 0
    conservation: float = 0.0
    cleanup: float = 0.0
    births: int = 0
    deaths: int = 0
    shortage: float = 0.0
    rainfall: float = 0.0
    population_limit_reached: bool = False
    wild_food: float = 0.0
    natural_growth: float = 0.0
    wild_harvest: float = 0.0
    farm_harvest: float = 0.0
    farm_workers: int = 0
    foragers: int = 0
    thor_harvest: float = 0.0
    food_spoilage: float = 0.0
    preservation: float = 0.0
    preservation_workers: int = 0
    estimated_food_supply: float = 0.0
    estimated_carrying_capacity: float = 0.0
    birth_policy: float = 1.0
    pollinator_count: int = 0
    grazer_count: int = 0
    pollination_bonus: float = 0.0
    livestock_food: float = 0.0
    grazer_births: int = 0
    grazer_deaths: int = 0
    mean_farmer_skill: float = 0.0
    mean_forager_skill: float = 0.0
    ecosystem_pressure: float = 0.0
    biodiversity: float = 1.0
    feedback_response: float = 0.0
    plant_biomass: float = 0.0
    seed_bank: float = 0.0
    flowering_biomass: float = 0.0
    plant_growth: float = 0.0
    plant_dieback: float = 0.0
    forage_yield: float = 0.0
    preservation_effort: float = 0.0
    cultivation_effort: float = 0.0
    foraging_effort: float = 0.0
    cultivation_contributors: int = 0
    foraging_contributors: int = 0
    mean_cultivation_aptitude: float = 0.0
    mean_foraging_aptitude: float = 0.0
    mean_cultivation_share: float = 0.0

    @classmethod
    def create(cls, config):
        return cls(water=config.initial_water, food=config.initial_food,
                   reservoir=config.initial_reservoir, pollution=config.initial_pollution,
                   fertility=config.initial_fertility, wild_food=config.initial_wild_food,
                   plant_biomass=config.initial_plant_biomass, seed_bank=config.initial_seed_bank,
                   pollinator_count=config.initial_pollinators, grazer_count=config.initial_grazers)

    def transfer_water(self, amount, capacity):
        moved = max(0.0, min(amount, self.reservoir, capacity - self.water))
        self.reservoir -= moved
        self.water += moved
        return moved

    def grow_food(self, amount, config):
        """Thor's production consumes water and fertility; it never creates either."""
        available = self.water / config.food_water_cost if config.food_water_cost else float("inf")
        grown = max(0.0, min(amount, available, config.food_capacity - self.food))
        self.water = max(0.0, self.water - grown * config.food_water_cost)
        self.food += grown
        self.fertility = max(0.0, self.fertility - grown * 0.000008)
        return grown

    def grow_wild_food(self, amount, config):
        """Nature replenishes forageable food without filling the human pantry."""
        grown = max(0.0, min(amount, config.wild_food_capacity - self.wild_food))
        self.wild_food += grown
        self.natural_growth = grown
        return grown

    def harvest_wild_food(self, amount, config):
        """Foraging converts a finite wild stock into edible reserves."""
        harvested = max(0.0, min(amount, self.wild_food, config.food_capacity - self.food))
        self.wild_food -= harvested
        self.food += harvested
        self.wild_harvest = harvested
        return harvested

    def grow_farm_food(self, amount, config):
        """Demeter's harvest needs land, workers, water, and fertile soil."""
        available = self.water / config.farm_water_cost if config.farm_water_cost else float("inf")
        grown = max(0.0, min(amount, available, config.food_capacity - self.food))
        self.water = max(0.0, self.water - grown * config.farm_water_cost)
        self.food += grown
        self.fertility = max(0.0, self.fertility - grown * 0.000012)
        self.farm_harvest = grown
        return grown
