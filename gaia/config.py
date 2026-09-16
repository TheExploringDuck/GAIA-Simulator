"""Explicit assumptions for the first Gaia model. Units are abstract."""

from dataclasses import asdict, dataclass, fields
import math


@dataclass(frozen=True)
class Config:
    seed: int = 42
    mode: str = "feedback"
    initial_population: int = 36
    initial_water: float = 1000.0
    initial_food: float = 500.0
    initial_wild_food: float = 500.0
    initial_reservoir: float = 3000.0
    initial_pollution: float = 0.0
    initial_fertility: float = 0.8
    water_capacity: float = 2000.0
    food_capacity: float = 1200.0
    wild_food_capacity: float = 1000.0
    initial_plant_biomass: float = 650.0
    initial_seed_bank: float = 450.0
    plant_biomass_capacity: float = 1800.0
    seed_bank_capacity: float = 1000.0
    reservoir_capacity: float = 6000.0
    # Mean renewable inflow. It exceeds the default settlement's maintenance
    # demand modestly, leaving room for growth while remaining finite.
    rainfall: float = 45.0
    rainfall_variability: float = 0.3
    season_length: int = 240
    natural_flow: float = 12.0
    evaporation: float = 0.001
    food_growth: float = 80.0
    plant_water_cost: float = 0.025
    flowering_fraction: float = 0.25
    seed_yield: float = 0.03
    seed_decay: float = 0.002
    forage_from_growth: float = 0.55
    plant_dieback: float = 0.008
    plant_pollution_sensitivity: float = 0.002
    food_water_cost: float = 0.45
    food_decay: float = 0.008
    forage_per_inhabitant: float = 0.7
    farm_land: float = 0.65
    farm_yield: float = 90.0
    farm_water_cost: float = 0.30
    # Inhabitants allocate this general work capacity adaptively; Gaia no
    # longer begins by assigning farmer and forager roles.
    work_intensity: float = 0.82
    scarcity_work_response: float = 0.12
    effort_half_saturation: float = 8.0
    farm_pollution_per_food: float = 0.006
    work_reproduction_cost: float = 0.25
    strategy_learning_rate: float = 0.08
    hestia_enabled: bool = True
    preservation_labor_fraction: float = 0.08
    preservation_max: float = 0.65
    preservation_food_days: float = 12.0
    capacity_window: int = 60
    capacity_birth_floor: float = 0.75
    capacity_birth_surplus: float = 0.15
    initial_pollinators: int = 120
    # These are ecological pressure scales, not population ceilings. Both
    # species may exceed them when conditions support it.
    pollinator_pressure_scale: float = 600.0
    pollinator_effect_scale: float = 180.0
    pollinator_growth: float = 0.06
    pollinator_pollution_sensitivity: float = 0.0001
    pollination_bonus_max: float = 0.75
    pollinator_birth_probability: float = 0.06
    pollinator_maturity_age: int = 8
    pollinator_max_age: int = 90
    pollinator_starvation_damage: float = 0.03
    pollinator_adaptation_strength: float = 0.30
    pollinator_adaptation_mutation: float = 0.05
    initial_grazers: int = 8
    grazer_pressure_scale: float = 48.0
    grazer_density_stress: float = 0.030
    grazer_adaptation_strength: float = 0.50
    grazer_adaptation_mutation: float = 0.08
    grazer_birth_probability: float = 0.035
    grazer_wild_food_per_animal: float = 0.40
    grazer_water_per_animal: float = 0.18
    grazer_food_yield: float = 0.16
    grazer_pollution_per_animal: float = 0.012
    grazer_maturity_age: int = 40
    grazer_max_age: int = 500
    grazer_starvation_damage: float = 0.16
    metis_enabled: bool = True
    feedback_window: int = 60
    feedback_gain: float = 0.65
    pollution_per_person: float = 0.12
    pollution_decay: float = 0.006
    fertility_recovery: float = 0.003
    water_per_person: float = 0.7
    food_per_person: float = 1.1
    # Per eligible pair per tick, before health, reserves, carrying capacity,
    # labour, and feedback modify it. This permits a resource-secure
    # settlement to replace natural deaths and grow.
    birth_probability: float = 0.010
    mutation_rate: float = 0.03
    maturity_age: int = 30
    max_age: int = 600
    starvation_damage: float = 0.13
    max_population: int = 2000
    # Reservoir water is released every tick before ecological consumers act.
    # This prevents ten-tick shortages followed by a large corrective pulse.
    poseidon_interval: int = 1
    poseidon_transfer: float = 100.0
    thor_interval: int = 15
    thor_harvest: float = 50.0
    governance_interval: int = 10
    governance_enabled: bool = True
    poseidon_enabled: bool = True
    thor_enabled: bool = True
    demeter_enabled: bool = True
    observation_window: int = 240
    stability_tolerance: float = 0.08

    def __post_init__(self):
        if self.mode not in {"fixed", "feedback", "off"}:
            raise ValueError("mode must be fixed, feedback, or off")
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(field.default, bool):
                if type(value) is not bool:
                    raise ValueError(f"{field.name} must be true or false")
            elif isinstance(field.default, int):
                if type(value) is not int:
                    raise ValueError(f"{field.name} must be an integer")
            elif isinstance(field.default, float):
                if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                    raise ValueError(f"{field.name} must be a finite number")
            if isinstance(value, (int, float)) and not isinstance(value, bool) and field.name != "seed" and value < 0:
                raise ValueError(f"{field.name} cannot be negative")
        for name in ("water_capacity", "food_capacity", "wild_food_capacity", "reservoir_capacity", "plant_biomass_capacity", "seed_bank_capacity", "season_length",
                     "max_age", "max_population", "poseidon_interval", "thor_interval", "governance_interval",
                     "capacity_window", "feedback_window", "effort_half_saturation", "pollinator_pressure_scale", "pollinator_effect_scale", "grazer_pressure_scale", "pollinator_maturity_age",
                     "pollinator_max_age", "grazer_maturity_age", "grazer_max_age"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.observation_window < 20:
            raise ValueError("observation_window must be at least 20")
        for name in ("initial_fertility", "rainfall_variability", "evaporation", "food_decay",
                     "pollution_decay", "fertility_recovery", "birth_probability", "mutation_rate", "stability_tolerance", "plant_water_cost", "flowering_fraction", "seed_yield", "seed_decay", "forage_from_growth", "plant_dieback", "plant_pollution_sensitivity",
                     "farm_land", "work_intensity", "scarcity_work_response", "work_reproduction_cost", "strategy_learning_rate", "preservation_labor_fraction",
                     "preservation_max", "capacity_birth_floor", "capacity_birth_surplus", "pollinator_growth", "pollinator_pollution_sensitivity",
                     "pollination_bonus_max", "pollinator_birth_probability", "pollinator_starvation_damage", "pollinator_adaptation_strength", "pollinator_adaptation_mutation",
                     "grazer_density_stress", "grazer_adaptation_strength", "grazer_adaptation_mutation",
                     "grazer_birth_probability", "grazer_starvation_damage", "feedback_gain"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        for initial, capacity in (("initial_water", "water_capacity"), ("initial_food", "food_capacity"),
                                  ("initial_wild_food", "wild_food_capacity"), ("initial_plant_biomass", "plant_biomass_capacity"),
                                  ("initial_seed_bank", "seed_bank_capacity"),
                                  ("initial_reservoir", "reservoir_capacity"), ("initial_population", "max_population")):
            if getattr(self, initial) > getattr(self, capacity):
                raise ValueError(f"{initial} exceeds {capacity}")
        if self.maturity_age >= self.max_age:
            raise ValueError("maturity_age must be below max_age")
        if self.pollinator_maturity_age >= self.pollinator_max_age or self.grazer_maturity_age >= self.grazer_max_age:
            raise ValueError("Animal maturity ages must be below their maximum ages")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, values):
        if not isinstance(values, dict):
            raise ValueError("Configuration must be a JSON object")
        values = dict(values)
        # Earlier versions prescribed a settlement-wide farmer fraction.
        # Preserve old experiments by translating it to neutral total work
        # capacity; individual allocation is now adaptive.
        if "farm_labor_fraction" in values:
            values.setdefault("work_intensity", min(1.0, values["farm_labor_fraction"] + 0.30))
            values.pop("farm_labor_fraction")
        if "farm_labor_half_saturation" in values:
            values.setdefault("effort_half_saturation", values["farm_labor_half_saturation"])
            values.pop("farm_labor_half_saturation")
        if "farm_reproduction_cost" in values:
            values.setdefault("work_reproduction_cost", values["farm_reproduction_cost"])
            values.pop("farm_reproduction_cost")
        # Pre-0.1.1 saves used hard animal capacities. Preserve their numeric
        # intent as the density scale after removing those ceilings.
        if "pollinator_capacity" in values:
            values.setdefault("pollinator_pressure_scale", values["pollinator_capacity"])
            values.pop("pollinator_capacity")
        if "grazer_capacity" in values:
            values.setdefault("grazer_pressure_scale", values["grazer_capacity"])
            values.pop("grazer_capacity")
        unknown = set(values) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"Unknown configuration fields: {', '.join(sorted(unknown))}")
        return cls(**values)
