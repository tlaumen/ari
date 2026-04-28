from dataclasses import dataclass


@dataclass
class Calculation:
    def calculate(self):
        """Abstract representation of the method to make a calculation"""
        raise NotImplementedError("calculate method is not a concrete implementation")
