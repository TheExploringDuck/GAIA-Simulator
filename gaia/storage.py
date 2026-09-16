"""Portable JSON checkpoints, including both random streams for exact continuation."""

import csv
from dataclasses import asdict, fields
import io
import json
import math
from pathlib import Path

from .config import Config
from .engine import Simulation
from .genetics import Creature, Organism
from .world import World
from .events import validate_event


def checkpoint(sim):
    return {"schema_version": 5, "config": sim.config.to_dict(), "world": asdict(sim.world),
            "population": [asdict(p) for p in sim.population], "next_id": sim.next_id,
            "pollinators": [asdict(p) for p in sim.pollinators], "grazers": [asdict(p) for p in sim.grazers],
            "next_creature_id": sim.next_creature_id, "scheduled_events": sim.scheduled_events,
            "weather_rng": sim.weather_rng.getstate(), "life_rng": sim.life_rng.getstate(),
            "history": sim.history, "events": sim.events}


def _tuples(value):
    return tuple(_tuples(x) for x in value) if isinstance(value, list) else value


def restore(data):
    try:
        if data.get("schema_version") not in {1, 2, 3, 4, 5}:
            raise ValueError("Unsupported checkpoint version")
        # Reject NaN/Infinity throughout, including history and random state.
        json.dumps(data, allow_nan=False)
        sim = Simulation(Config.from_dict(data["config"]))
        world_data = dict(data["world"])
        migrated_plants = "plant_biomass" not in world_data
        if migrated_plants:
            # Old worlds used wild_food as the sole plant proxy. Give their
            # continuation a living plant layer while retaining the original
            # historical records before the restore point.
            world_data["plant_biomass"] = min(sim.config.plant_biomass_capacity, max(world_data.get("wild_food", 0.0), sim.config.initial_plant_biomass))
            world_data["seed_bank"] = sim.config.initial_seed_bank
        for field in fields(World):
            world_data.setdefault(field.name, field.default)
        sim.world = World(**world_data)
        if type(sim.world.tick) is not int or sim.world.tick < 0:
            raise ValueError("Invalid checkpoint tick")
        sim.population = [Organism(**p) for p in data["population"]]
        sim.pollinators = [Creature(**p) for p in data.get("pollinators", [])]
        sim.grazers = [Creature(**p) for p in data.get("grazers", [])]
        # Version 1 worlds predate animal populations. They retain their
        # original history and continue with an empty animal population rather
        # than receiving an artificial retrospective introduction.
        sim.world.pollinator_count = len(sim.pollinators)
        sim.world.grazer_count = len(sim.grazers)
        for p in sim.population:
            if len(p.genome) != 10 or any(type(g) is not int or not 0 <= g <= 10 for g in p.genome):
                raise ValueError("Invalid genome")
            if not 0 < p.health <= 1 or min(p.age, p.generation, p.cooldown, p.offspring, p.identifier) < 0:
                raise ValueError("Invalid inhabitant state")
            if any(type(v) is not int for v in (p.age, p.generation, p.cooldown, p.offspring, p.identifier)):
                raise ValueError("Invalid inhabitant counters")
            if (not all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1
                        for v in (p.cultivation_memory, p.foraging_memory, p.last_cultivation_share))):
                raise ValueError("Invalid inhabitant strategy state")
        ids = [p.identifier for p in sim.population]
        sim.next_id = data["next_id"]
        if type(sim.next_id) is not int or sim.next_id <= max(ids, default=-1) or len(ids) != len(set(ids)):
            raise ValueError("Invalid inhabitant IDs")
        creature_ids = [p.identifier for p in sim.pollinators + sim.grazers]
        for creature in sim.pollinators + sim.grazers:
            if creature.species not in {"pollinator", "grazer"} or not 0 < creature.health <= 1:
                raise ValueError("Invalid animal state")
            if (any(type(v) is not int or v < 0 for v in (creature.identifier, creature.age, creature.generation, creature.cooldown, creature.offspring))
                    or not isinstance(creature.resilience, (int, float)) or not 0 <= creature.resilience <= 1):
                raise ValueError("Invalid animal state")
        sim.next_creature_id = data.get("next_creature_id", 1_000_000)
        if type(sim.next_creature_id) is not int or sim.next_creature_id <= max(creature_ids, default=-1) or len(creature_ids) != len(set(creature_ids)):
            raise ValueError("Invalid animal IDs")
        sim.weather_rng.setstate(_tuples(data["weather_rng"]))
        sim.life_rng.setstate(_tuples(data["life_rng"]))
        scheduled = data.get("scheduled_events", [])
        if not isinstance(scheduled, list):
            raise ValueError("Invalid scheduled events")
        sim.scheduled_events = [validate_event(event, sim.world.tick) for event in scheduled]
        sim.scheduled_events.sort(key=lambda event: event["at_tick"])
        sim.history = data["history"]
        sim.events = data["events"]
        if not sim.history or len(sim.history) != sim.world.tick + 1:
            raise ValueError("Incomplete checkpoint history")
        expected_keys = set(Simulation(sim.config).history[0])
        # Populate only fields introduced after version 1. Their historical
        # value is unknown, so zero is more honest than fabricating a trend.
        defaults = {key: 0 for key in expected_keys}
        defaults["birth_policy"] = 1.0
        for row in sim.history:
            for key, value in defaults.items():
                row.setdefault(key, value)
        if migrated_plants:
            for key in ("plant_biomass", "seed_bank", "flowering_biomass", "plant_growth", "plant_dieback", "forage_yield"):
                sim.history[-1][key] = getattr(sim.world, key)
        for tick, row in enumerate(sim.history):
            if set(row) != expected_keys or row["tick"] != tick or any(not isinstance(v, (int, float, bool)) or not math.isfinite(v) for v in row.values()):
                raise ValueError("Invalid checkpoint history")
        if sim.history[-1]["population"] != len(sim.population):
            raise ValueError("Checkpoint population and history disagree")
        if sim.history[-1]["pollinator_count"] != len(sim.pollinators) or sim.history[-1]["grazer_count"] != len(sim.grazers):
            raise ValueError("Checkpoint animal populations and history disagree")
        if any(sim.history[-1][key] != value for key, value in asdict(sim.world).items()):
            raise ValueError("Checkpoint world and history disagree")
        if not isinstance(sim.events, list) or any(not isinstance(e.get("message"), str) or not isinstance(e.get("system"), str)
                                                  or type(e.get("tick")) is not int for e in sim.events):
            raise ValueError("Invalid checkpoint events")
        sim.check_invariants()
        return sim
    except (KeyError, TypeError, AttributeError, OverflowError, RuntimeError) as exc:
        raise ValueError(f"Invalid Gaia checkpoint: {exc}") from exc


def save(sim, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(checkpoint(sim), allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def load(path):
    return restore(json.loads(Path(path).read_text(encoding="utf-8")))


def history_csv(sim):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(sim.history[0]))
    writer.writeheader()
    writer.writerows(sim.history)
    return output.getvalue()


def render_report(sim):
    template = (Path(__file__).parent / "monitor.html").read_text(encoding="utf-8")
    payload = json.dumps({"live": False, "state": sim.snapshot(1500)}, allow_nan=False).replace("<", "\\u003c")
    return template.replace("__GAIA_BOOTSTRAP__", payload)


def export_run(sim, directory):
    from .metrics import summarize
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    save(sim, directory / "checkpoint.json")
    (directory / "history.csv").write_text(history_csv(sim), encoding="utf-8")
    (directory / "summary.json").write_text(json.dumps(summarize(sim), indent=2), encoding="utf-8")
    (directory / "report.html").write_text(render_report(sim), encoding="utf-8")
