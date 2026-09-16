from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from gaia.config import Config
from gaia.engine import Simulation
from gaia.genetics import Creature, Organism, inherit, inherit_resilience
from gaia.metrics import diagnose
from gaia.storage import checkpoint, export_run, load, restore, save


class SimulationTests(unittest.TestCase):
    def test_same_seed_reproduces_whole_run(self):
        a = Simulation(Config(seed=7)).step(700)
        b = Simulation(Config(seed=7)).step(700)
        self.assertEqual(checkpoint(a), checkpoint(b))
        self.assertNotEqual(a.history, Simulation(Config(seed=8)).step(700).history)

    def test_checkpoint_continuation_is_exact(self):
        continuous = Simulation().step(450)
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "checkpoint.json"
            save(Simulation().step(173), file)
            resumed = load(file).step(277)
        self.assertEqual(checkpoint(continuous), checkpoint(resumed))

    def test_common_seed_keeps_weather_identical_between_modes(self):
        runs = [Simulation(Config(mode=mode)).step(500) for mode in ("off", "fixed", "feedback")]
        self.assertEqual([r["rainfall"] for r in runs[0].history], [r["rainfall"] for r in runs[2].history])
        self.assertNotEqual(runs[0].history[-1]["water"], runs[2].history[-1]["water"])

    def test_no_resources_means_extinction_without_negative_stores(self):
        config = Config(initial_water=0, initial_food=0, initial_reservoir=0, rainfall=0, food_growth=0)
        sim = Simulation(config).step(60)
        self.assertEqual(len(sim.population), 0)
        self.assertEqual(diagnose(sim.history, config)["status"], "extinct")
        self.assertTrue(all(row["water"] >= 0 and row["food"] >= 0 for row in sim.history))
        sim.step(100)
        self.assertEqual(len(sim.population), 0)

    def test_regulators_cannot_create_water_in_a_closed_system(self):
        sim = Simulation(Config(rainfall=0, evaporation=0)).step(1000)
        total = [r["water"] + r["reservoir"] for r in sim.history]
        self.assertTrue(all(b <= a + 1e-8 for a, b in zip(total, total[1:])))

    def test_poseidon_transfer_respects_reservoir_and_capacity(self):
        sim = Simulation(Config(initial_population=0, initial_water=1999, initial_reservoir=5))
        moved = sim.world.transfer_water(100, sim.config.water_capacity)
        self.assertEqual(moved, 1)
        self.assertEqual(sim.world.water, 2000)
        self.assertEqual(sim.world.reservoir, 4)

    def test_food_requires_water(self):
        sim = Simulation(Config(initial_population=0, initial_water=1, initial_food=0))
        grown = sim.world.grow_food(1000, sim.config)
        self.assertAlmostEqual(grown, 1 / sim.config.food_water_cost)
        self.assertAlmostEqual(sim.world.water, 0)

    def test_nature_grows_a_separate_wild_food_stock(self):
        sim = Simulation(Config(initial_population=0, initial_wild_food=0, initial_food=0, initial_grazers=0))
        sim.step(1)
        self.assertGreater(sim.world.wild_food, 0)
        self.assertEqual(sim.world.food, 0)

    def test_plant_layer_grows_forages_and_flowers_from_separate_stocks(self):
        config = Config(initial_population=0, initial_wild_food=0, initial_food=0, initial_grazers=0,
                        initial_plant_biomass=500, initial_seed_bank=400)
        sim = Simulation(config).step(1)
        self.assertGreater(sim.world.plant_growth, 0)
        self.assertGreater(sim.world.flowering_biomass, 0)
        self.assertGreater(sim.world.forage_yield, 0)
        self.assertEqual(sim.world.natural_growth, sim.world.forage_yield)

    def test_grazers_consume_vegetation_instead_of_human_forage(self):
        config = Config(initial_population=0, initial_wild_food=100, initial_grazers=1,
                        initial_plant_biomass=10, initial_seed_bank=0, food_growth=0,
                        rainfall=0, initial_reservoir=0, evaporation=0)
        sim = Simulation(config).step(1)
        self.assertLess(sim.world.plant_biomass, 10)
        self.assertEqual(sim.world.wild_food, 100)

    def test_demeter_needs_people_water_and_soil(self):
        config = Config(initial_population=10, initial_food=0, initial_wild_food=0,
                        food_growth=0, thor_enabled=False, rainfall=0, initial_reservoir=0,
                        initial_water=1000, fertility_recovery=0)
        sim = Simulation(config).step(1)
        self.assertGreater(sim.world.farm_workers, 0)
        self.assertGreater(sim.world.farm_harvest, 0)
        self.assertLess(sim.world.water, config.initial_water)
        self.assertLess(sim.world.fertility, config.initial_fertility)
        dry = Simulation(Config(**{**config.to_dict(), "initial_water": 0})).step(1)
        self.assertEqual(dry.world.farm_harvest, 0)

    def test_inhabitants_adapt_effort_without_assigned_roles(self):
        sim = Simulation(Config(initial_population=0, initial_pollinators=0, initial_grazers=0))
        cultivator = Organism(1, [5, 5, 5, 5, 5, 5, 10, 10, 0, 0])
        forager = Organism(2, [5, 5, 5, 5, 5, 5, 0, 0, 10, 10])
        sim.population = [cultivator, forager]
        sim.next_id = 3
        sim.step(1)
        self.assertGreater(cultivator.last_cultivation_share, forager.last_cultivation_share)
        self.assertGreater(sim.world.cultivation_effort, 0)
        self.assertGreater(sim.world.foraging_effort, 0)
        self.assertEqual(sim.world.cultivation_contributors, 2)
        self.assertEqual(sim.world.foraging_contributors, 2)

    def test_foraging_depletes_a_finite_wild_stock(self):
        config = Config(initial_population=8, initial_food=0, initial_wild_food=5, food_growth=0,
                        demeter_enabled=False, thor_enabled=False, rainfall=0, initial_reservoir=0, initial_grazers=0)
        sim = Simulation(config).step(1)
        self.assertEqual(sim.world.wild_harvest, 5)
        self.assertEqual(sim.world.wild_food, 0)

    def test_animals_have_individual_life_cycles_without_population_ceilings(self):
        config = Config(initial_population=0, initial_grazers=4, grazer_max_age=2, grazer_maturity_age=1,
                        initial_pollinators=8, pollinator_max_age=2, pollinator_maturity_age=1,
                        food_growth=0, thor_enabled=False, rainfall=0, initial_reservoir=0)
        sim = Simulation(config).step(3)
        self.assertEqual(sim.world.grazer_count, len(sim.grazers))
        self.assertEqual(sim.world.pollinator_count, len(sim.pollinators))
        self.assertGreaterEqual(sim.world.grazer_deaths, 0)
        self.assertGreaterEqual(sim.world.grazer_count, 0)
        self.assertGreaterEqual(sim.world.pollinator_count, 0)

    def test_pollinators_do_not_have_a_hard_population_ceiling(self):
        config = Config(initial_population=0, initial_pollinators=700, pollinator_pressure_scale=600,
                        initial_grazers=0, food_growth=0, rainfall=0, initial_reservoir=0)
        sim = Simulation(config).step(1)
        self.assertEqual(sim.world.pollinator_count, len(sim.pollinators))
        self.assertGreater(sim.world.pollinator_count, 600)

    def test_legacy_animal_capacities_restore_as_pressure_scales(self):
        config = Config.from_dict({"pollinator_capacity": 640, "grazer_capacity": 70})
        self.assertEqual(config.pollinator_pressure_scale, 640)
        self.assertEqual(config.grazer_pressure_scale, 70)

    def test_grazer_resilience_is_inherited_with_bounded_variation(self):
        import random
        first, second = Creature(1, "grazer", resilience=0.2), Creature(2, "grazer", resilience=0.8)
        resilience = inherit_resilience(first, second, random.Random(4), 0.08)
        self.assertGreater(resilience, 0.42)
        self.assertLess(resilience, 0.58)

    def test_scheduled_events_are_reproducible_and_apply_at_their_tick(self):
        config = Config(initial_population=0, initial_water=0, initial_reservoir=0, rainfall=0,
                        natural_flow=0, evaporation=0, poseidon_enabled=False)
        sim = Simulation(config)
        sim.schedule_event({"kind": "rainfall", "magnitude": 100, "at_tick": 3})
        resumed = restore(checkpoint(sim))
        sim.step(3)
        resumed.step(3)
        self.assertEqual(checkpoint(sim), checkpoint(resumed))
        self.assertEqual(sim.world.reservoir, 100)
        self.assertFalse(sim.scheduled_events)

    def test_metis_feedback_responds_to_persistent_ecological_loss(self):
        config = Config(initial_population=0, initial_food=0, initial_water=0, initial_reservoir=0,
                        rainfall=0, food_growth=0, initial_pollinators=0, initial_grazers=0)
        sim = Simulation(config).step(12)
        self.assertGreater(sim.world.ecosystem_pressure, 0)
        self.assertGreater(sim.world.feedback_response, 0)

    def test_off_mode_has_no_regulator_actions(self):
        sim = Simulation(Config(mode="off")).step(60)
        self.assertTrue(all(e["system"] not in {"Poseidon", "Thor", "Governance"} for e in sim.events))
        self.assertEqual(sim.world.conservation, 0)
        self.assertEqual(sim.world.cleanup, 0)

    def test_inherited_traits_change_resource_demand(self):
        a, b = Organism(1, [0] * 10), Organism(2, [10] * 10)
        self.assertLess(a.food_demand, b.food_demand)
        self.assertLess(a.tolerance, b.tolerance)
        import random
        genome = inherit(a, b, random.Random(1), 0)
        self.assertIn(0, genome)
        self.assertIn(10, genome)
        self.assertEqual(len(genome), 10)

    def test_deaths_births_account_for_population(self):
        sim = Simulation().step(1000)
        for before, after in zip(sim.history, sim.history[1:]):
            self.assertEqual(after["population"], before["population"] + after["births"] - after["deaths"])

    def test_population_limit_is_reported_as_a_limit(self):
        config = Config(initial_population=2, max_population=2, maturity_age=0, birth_probability=1,
                        water_per_person=0, food_per_person=0, pollution_per_person=0)
        sim = Simulation(config).step(10)
        self.assertEqual(len(sim.population), 2)
        self.assertTrue(sim.world.population_limit_reached)
        self.assertEqual(diagnose(sim.history, config)["status"], "capacity limit")

    def test_invalid_config_is_rejected(self):
        for changes in ({"water_capacity": 0}, {"mode": "magic"}, {"rainfall": float("nan")},
                        {"initial_population": 3.5}, {"initial_population": True}, {"mutation_rate": 2},
                        {"thor_interval": 0}, {"unknown": 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Config.from_dict(changes)

    def test_legacy_role_parameters_migrate_to_adaptive_effort(self):
        config = Config.from_dict({"farm_labor_fraction": 0.32, "farm_labor_half_saturation": 8,
                                   "farm_reproduction_cost": 0.35})
        self.assertAlmostEqual(config.work_intensity, 0.62)
        self.assertEqual(config.effort_half_saturation, 8)
        self.assertAlmostEqual(config.work_reproduction_cost, 0.35)

    def test_invalid_checkpoint_is_rejected(self):
        data = checkpoint(Simulation())
        data["population"][0]["genome"][0] = 99
        with self.assertRaises(ValueError):
            restore(data)

    def test_version_one_checkpoint_migrates_without_adding_animals(self):
        data = checkpoint(Simulation().step(3))
        data["schema_version"] = 1
        data.pop("pollinators")
        data.pop("grazers")
        data.pop("next_creature_id")
        for person in data["population"]:
            person.pop("cultivation_memory")
            person.pop("foraging_memory")
            person.pop("last_cultivation_share")
        for key in ("pollinator_count", "grazer_count", "pollination_bonus", "livestock_food",
                    "grazer_births", "grazer_deaths", "mean_farmer_skill", "mean_forager_skill"):
            data["world"].pop(key, None)
            for row in data["history"]:
                row.pop(key, None)
        migrated = restore(data)
        self.assertEqual(len(migrated.pollinators), 0)
        self.assertEqual(len(migrated.grazers), 0)
        data = checkpoint(Simulation())
        data["world"]["water"] = -1
        with self.assertRaises(ValueError):
            restore(data)

    def test_export_is_portable_and_contains_no_live_token(self):
        with tempfile.TemporaryDirectory() as directory:
            export_run(Simulation().step(20), directory)
            self.assertTrue((Path(directory) / "history.csv").read_text().startswith("water,food,"))
            report = (Path(directory) / "report.html").read_text(encoding="utf-8")
            self.assertIn('"live": false', report)
            self.assertNotIn("__GAIA_BOOTSTRAP__", report)
            self.assertNotIn('"token":', report)

    def test_long_runs_across_regimes_obey_invariants(self):
        for seed in (1, 42):
            for mode in ("off", "fixed", "feedback"):
                for rainfall in (0, 32, 100):
                    with self.subTest(seed=seed, mode=mode, rainfall=rainfall):
                        sim = Simulation(Config(seed=seed, mode=mode, rainfall=rainfall)).step(1500)
                        sim.check_invariants()


if __name__ == "__main__":
    unittest.main()
