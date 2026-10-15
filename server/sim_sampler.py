import numpy as np


class SimSampler:
    def __init__(self, seed=None):
        self.rng = np.random.default_rng(seed)

    def scalar(self, value):
        return value

    def uniform(self, a=0.0, b=1.0, size=None):
        return self.rng.uniform(a, b, size)

    def normal(self, mu=0.0, sigma=1.0, size=None):
        return self.rng.normal(mu, sigma, size)

    def exponential(self, scale=1.0, size=None):
        return self.rng.exponential(scale, size)

    def bernoulli(self, p=0.5, size=None):
        return self.rng.binomial(1, p, size)

    def distribution(self, definition):
        """Sample one value from a world numeric distribution."""
        if not isinstance(definition, dict):
            raise ValueError("Numeric cells must be distribution objects")

        distribution_type = definition.get("type")
        value = definition.get("value")

        if distribution_type == "scalar":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Scalar distribution value must be a number")
            return float(value)

        if distribution_type == "normal":
            if not isinstance(value, dict):
                raise ValueError("Normal distribution value must be an object")
            mean = value.get("mean")
            stddev = value.get("stddev")
            if (
                isinstance(mean, bool)
                or not isinstance(mean, (int, float))
                or isinstance(stddev, bool)
                or not isinstance(stddev, (int, float))
                or stddev < 0
            ):
                raise ValueError(
                    "Normal distribution requires numeric mean and non-negative stddev"
                )
            return float(self.normal(mean, stddev))

        if distribution_type == "uniform":
            if not isinstance(value, dict):
                raise ValueError("Uniform distribution value must be an object")
            minimum = value.get("min")
            maximum = value.get("max")
            if (
                isinstance(minimum, bool)
                or not isinstance(minimum, (int, float))
                or isinstance(maximum, bool)
                or not isinstance(maximum, (int, float))
                or minimum > maximum
            ):
                raise ValueError(
                    "Uniform distribution requires numeric min and max with min <= max"
                )
            return float(self.uniform(minimum, maximum))

        raise ValueError(
            "Numeric distribution type must be scalar, normal, or uniform"
        )

    def grid(self, grid, height, width, label):
        """Sample a 2D distribution grid into a numeric grid."""
        if not isinstance(grid, list) or len(grid) != height:
            raise ValueError(
                f"Variable '{label}' grid does not match world size {width}x{height}"
            )

        sampled = []
        for row in grid:
            if not isinstance(row, list) or len(row) != width:
                raise ValueError(
                    f"Variable '{label}' grid does not match world size {width}x{height}"
                )
            sampled.append([self.distribution(cell) for cell in row])
        return sampled
