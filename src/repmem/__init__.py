"""Break-even analysis of a bit-flip repetition-code memory under superconducting-style noise."""
from .sim import NoiseModel, logical_failure, per_cycle_rate, physical_rate

__all__ = ["NoiseModel", "logical_failure", "per_cycle_rate", "physical_rate"]
