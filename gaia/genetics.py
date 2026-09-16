"""Ten inherited genes, replacing the skeleton's disconnected sum-of-genes score."""

from dataclasses import dataclass


@dataclass
class Organism:
    identifier: int
    genome: list[int]
    age: int = 0
    health: float = 1.0
    generation: int = 0
    cooldown: int = 0
    offspring: int = 0
    cultivation_memory: float = 0.5
    foraging_memory: float = 0.5
    last_cultivation_share: float = 0.5

    @property
    def name(self):
        return f"Human {self.identifier:05d}"

    def pair(self, index):
        return (self.genome[index] + self.genome[index + 1]) / 20

    @property
    def food_demand(self):
        return 0.8 + 0.4 * self.pair(0)

    @property
    def water_demand(self):
        return 0.8 + 0.4 * self.pair(2)

    @property
    def tolerance(self):
        return 0.65 + 0.7 * self.pair(4)

    @property
    def fecundity(self):
        # Efficient consumption has a reproduction cost: no universally best genome.
        return (0.7 + 0.6 * self.pair(6)) * (self.food_demand + self.water_demand) / 2

    @property
    def lifespan(self):
        return 0.75 + 0.5 * self.pair(8)

    @property
    def cultivation_aptitude(self):
        """Inherited effectiveness at converting effort into farm output."""
        return 0.65 + 0.7 * self.pair(6)

    @property
    def foraging_aptitude(self):
        """Inherited effectiveness at locating and harvesting wild food."""
        return 0.65 + 0.7 * self.pair(8)

    # Compatibility names for older reports and saved analysis scripts.
    @property
    def agriculture_skill(self):
        return self.cultivation_aptitude

    @property
    def foraging_skill(self):
        return self.foraging_aptitude


@dataclass
class Creature:
    """An individual non-human inhabitant with the same basic life cycle."""
    identifier: int
    species: str
    age: int = 0
    health: float = 1.0
    generation: int = 0
    cooldown: int = 0
    offspring: int = 0
    resilience: float = 0.5


def inherit(parent1, parent2, rng, mutation_rate):
    point = rng.randint(1, 9)
    genome = parent1.genome[:point] + parent2.genome[point:]
    varied = []
    for gene in genome:
        if rng.random() >= mutation_rate:
            varied.append(gene)
        elif rng.random() < 0.85:
            # Most mutations are small drift; rare ones remain larger jumps.
            varied.append(min(10, max(0, gene + rng.choice((-1, 1)))))
        else:
            varied.append(rng.randint(0, 10))
    return varied


def inherit_resilience(parent1, parent2, rng, mutation):
    """Pass a grazer's stress resilience on with small, bounded variation."""
    inherited = (parent1.resilience + parent2.resilience) / 2
    return min(1.0, max(0.0, inherited + rng.uniform(-mutation, mutation)))
