# Demeter: the agriculture cycle

Gaia now has a real plant layer. **Chloris** tracks `plant_biomass`, a `seed_bank`, seasonal `flowering_biomass`, plant growth and dieback, and `forage_yield`. Seeds, soil fertility, accessible water, season, pollution, and prior pollination determine vegetation growth. Flowers support pollinators; pollination replenishes seeds; plant growth creates the separate, finite `wild_food` forage stock. Grazers consume vegetation, while inhabitants must forage edible wild food into the `food` pantry.

**Demeter** does not assign people permanent farming or foraging roles. Each inhabitant divides a finite amount of effort between cultivation and foraging according to inherited aptitude, the payoff they recently experienced, and the food, soil, water, and forage now available. The inherited aptitude traits recombine and mutate across generations, so the settlement’s collective behavior can evolve without a role being prescribed in advance. Farm production still depends on cultivated land, a diminishing-return effort curve, water, soil fertility, and pollution. A harvest consumes water, reduces fertility, and adds a small pollution cost.

Agriculture is connected to the rest of the world:

```text
rain + reservoir → accessible water → vegetation → flowers → pollinators → seed bank
                                      ↓                 ↓
                               grazers / forage → pantry → inhabitants
                                      ↑
                              soil fertility ← recovery / depletion ← labor, pollution
```

Adaptive food effort affects reproduction, while cleanup is a shared contribution across the settlement. This lets the world express a real tradeoff between food production, pollution, and population growth without converting anyone into a permanent cleanup role.

**Hestia** adds settlement stewardship. She allocates a small amount of labor to food preservation, reducing pantry spoilage, and estimates carrying capacity from recent harvests. Below the configured capacity floor she closes births; near the estimated limit she permits only low replacement pressure; durable reserves and a surplus permit growth.

## Timing and water budget

Each tick follows a resource order: rainfall enters the finite reservoir, Poseidon releases water toward the usable-water target, plants and animals use water, people produce and consume food, then Metis and Hestia assess the result. Poseidon releases water every tick, rather than storing up a ten-tick pulse. The default rainfall rate modestly exceeds the default settlement's maintenance demand, creating room for demographic growth; it does not create water, and the reservoir can still be depleted when population or production outgrows the climate.

**Aristaeus** adds two productive species. Pollinators improve wild growth and crop yield, but age, reproduce, and die from poor habitat or pollution. They have no fixed population ceiling: reproduction declines gradually with density, while their contribution to plant growth has diminishing returns because habitat is finite. Grazers consume wild food and water, convert some into pantry food, and have their own maturation, reproduction, aging, and scarcity-driven mortality. Dense herds face compounding survival pressure; resilience is inherited with small variation, so favorable conditions can select for a better-adapted herd. No population has a protected minimum; humans, pollinators, and grazers can all grow, fluctuate, or disappear.

**Metis** is Gaia's transparent self-feedback loop. She reads recent food and water security, shortages, soil fertility, and species retention, smooths them into ecological pressure, and feeds that signal into conservation, cleanup, and birth pacing. The feedback loop changes behavior; it cannot create resources or override death.

Human genomes begin diverse and mutate through mostly small inherited changes, with rare larger changes. Pollinators and grazers inherit a resilience trait with small variation. Organisms with resilience better suited to their habitat are more likely to remain healthy and reproduce, so the population can change across generations without any guaranteed direction.

The monitor can schedule recorded events at a future tick: rainfall, drought, food supply, blight, and disease. Events are saved in checkpoints and appear in the chronicle, so a scenario can be replayed exactly. End a run to freeze it and unlock its CSV export.

Useful experiments:

- Disable Demeter to see whether foraging alone can sustain the population.
- Reduce `farm_land` or `farm_yield` to study cultivation limits.
- Increase `farm_pollution_per_food` to test a productive but degrading agricultural regime.
- Change `food_growth` to change ecological wild-food regeneration.
- Compare the same seed in `off`, `fixed`, and `feedback` modes.

Two ready-to-edit configuration files are included in `configs/`:

- `foraging-only.json` removes cultivated agriculture and Thor, while making the wild ecosystem more productive.
- `intensive-agriculture.json` creates higher farm yields at greater water, soil, pollution, and population pressure.
