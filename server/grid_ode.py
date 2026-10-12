import ast
import json
import re

import jax
import jax.numpy as jnp
import sympy as sp

# JAX defaults to float32; ODE integrators accumulate error over many
# steps, so switch to float64 globally before creating any arrays.
jax.config.update("jax_enable_x64", True)


# ============================================================
# 1. Equation parsing
# ============================================================

FUNCTIONS = {
    "exp": jnp.exp,
    "log": jnp.log,
    "sqrt": jnp.sqrt,
    "sin": jnp.sin,
    "cos": jnp.cos,
    "tan": jnp.tan,
    "abs": jnp.abs,
}


def parse_expression(source):
    """Parse a restricted mathematical expression without eval()."""

    def convert(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return sp.sympify(node.value)

        if isinstance(node, ast.Name):
            return sp.Symbol(node.id)

        if isinstance(node, ast.BinOp):
            a, b = convert(node.left), convert(node.right)
            operators = {
                ast.Add: lambda: a + b,
                ast.Sub: lambda: a - b,
                ast.Mult: lambda: a * b,
                ast.Div: lambda: a / b,
                ast.Pow: lambda: a ** b,
            }
            op = operators.get(type(node.op))
            if op is None:
                raise ValueError("Unsupported operator")
            return op()

        if isinstance(node, ast.UnaryOp):
            value = convert(node.operand)
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return value

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name not in FUNCTIONS or node.keywords:
                raise ValueError(f"Unsupported function: {name}")
            if len(node.args) != 1:
                raise ValueError(f"{name} expects one argument")
            return sp.Function(name)(convert(node.args[0]))

        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    return convert(ast.parse(source, mode="eval").body)


def parse_system(equations, width, height):
    """Build a reusable local ODE system for a width x height grid."""
    if width < 1 or height < 1:
        raise ValueError("Grid dimensions must be positive")

    parsed = {}

    for equation in equations:
        lhs, sep, rhs = equation.partition("=")
        if not sep:
            raise ValueError(f"Missing '=': {equation}")

        match = re.fullmatch(r"\s*d([A-Za-z_]\w*)/dt\s*", lhs)
        if not match:
            raise ValueError(f"Expected dSTATE/dt: {lhs}")

        state = match.group(1)
        if state in parsed:
            raise ValueError(f"Duplicate equation for {state}")

        parsed[state] = parse_expression(rhs.strip())

    if not parsed:
        raise ValueError("At least one equation is required")

    states = list(parsed)
    expressions = list(parsed.values())
    symbols = set().union(*(expr.free_symbols for expr in expressions))

    state_symbols = [sp.Symbol(s) for s in states]
    parameter_symbols = sorted(
        symbols - set(state_symbols), key=str
    )
    parameters = [str(s) for s in parameter_symbols]

    compiled = [
        sp.lambdify(
            state_symbols + parameter_symbols,
            expr,
            modules=[dict(FUNCTIONS)],
        )
        for expr in expressions
    ]

    def rhs(y, params):
        # y shape: (height, width, number_of_states)
        #
        # The lambdified expressions are plain scalars, but JAX broadcasts
        # them across the whole grid: each state slice y[..., i] is a
        # (height, width) array, so every cell is evaluated at once. This
        # is the "local" part of the ODE - cells do not interact here.
        # `params` values are likewise either scalars or (height, width)
        # arrays, so per-cell parameters work transparently.
        values = [y[..., i] for i in range(len(states))]
        values += [params[p] for p in parameters]
        return jnp.stack(
            [fn(*values) for fn in compiled], axis=-1
        )

    return {
        "width": width,
        "height": height,
        "states": states,
        "parameters": parameters,
        "rhs": rhs,
    }


# ============================================================
# 2. Movement configuration
# ============================================================

DIRECTIONS_4 = {
    "N": (-1, 0),
    "S": (1, 0),
    "E": (0, 1),
    "W": (0, -1),
}

DIRECTIONS_8 = {
    **DIRECTIONS_4,
    "NE": (-1, 1),
    "NW": (-1, -1),
    "SE": (1, 1),
    "SW": (1, -1),
}


def create_movement(model, default_rate=0.02,
                    directions=8, wrap=False):
    """Create per-state movement defaults and cell overrides."""
    if default_rate < 0:
        raise ValueError("Movement rate must be non-negative")
    if directions not in (4, 8):
        raise ValueError("directions must be 4 or 8")

    defaults = {
        state: float(default_rate) for state in model["states"]
    }

    return {
        "width": model["width"],
        "height": model["height"],
        "directions": (
            DIRECTIONS_4 if directions == 4 else DIRECTIONS_8
        ),
        "wrap": wrap,
        "defaults": defaults.copy(),
        "initial_defaults": defaults.copy(),
        "overrides": {s: {} for s in model["states"]},
    }


def set_default_movement_rate(movement, variable, rate):
    """Change a variable's default rate in every direction."""
    if variable not in movement["defaults"]:
        raise ValueError(f"Unknown state: {variable}")
    if rate < 0:
        raise ValueError("Rate must be non-negative")
    movement["defaults"][variable] = float(rate)


def reset_default_movement_rate(movement, variable):
    """Restore the variable's original default rate."""
    if variable not in movement["defaults"]:
        raise ValueError(f"Unknown state: {variable}")
    movement["defaults"][variable] = (
        movement["initial_defaults"][variable]
    )


def set_cell_movement_rate(movement, variable, row, col, rate):
    """
    Override a cell's outgoing rates.

    rate can be a scalar for all directions or a partial dictionary,
    e.g. {"N": 0.06, "E": 0.01}.
    """
    h, w = movement["height"], movement["width"]

    if variable not in movement["defaults"]:
        raise ValueError(f"Unknown state: {variable}")
    if not (0 <= row < h and 0 <= col < w):
        raise ValueError("Cell coordinates out of range")

    if isinstance(rate, dict):
        if not set(rate).issubset(movement["directions"]):
            raise ValueError("Invalid direction")
        if any(v < 0 for v in rate.values()):
            raise ValueError("Rates must be non-negative")

        current = movement["overrides"][variable].get(
            (row, col), {}
        ).copy()
        current.update({d: float(v) for d, v in rate.items()})
        movement["overrides"][variable][(row, col)] = current
    else:
        if rate < 0:
            raise ValueError("Rate must be non-negative")
        movement["overrides"][variable][(row, col)] = {
            d: float(rate) for d in movement["directions"]
        }


def reset_cell_movement_rates(
    movement, variable=None, row=None, col=None
):
    """Clear overrides, optionally for one variable and cell."""
    if (row is None) != (col is None):
        raise ValueError("Specify both row and col, or neither")

    if row is not None:
        if variable is None:
            raise ValueError("Specify a variable for one-cell reset")
        if variable not in movement["overrides"]:
            raise ValueError(f"Unknown state: {variable}")
        if not (0 <= row < movement["height"]
                and 0 <= col < movement["width"]):
            raise ValueError("Cell coordinates out of range")
        movement["overrides"][variable].pop((row, col), None)
        return

    targets = (
        [variable] if variable is not None
        else list(movement["overrides"])
    )

    for state in targets:
        if state not in movement["overrides"]:
            raise ValueError(f"Unknown state: {state}")
        movement["overrides"][state].clear()


def build_movement_rates(movement):
    """
    Expand rates to arrays shaped (height, width, directions).

    JAX arrays are immutable, so overrides are applied with the
    functional ``.at[idx].set(value)`` API, which returns a new array
    rather than mutating in place. Doing this here keeps the hot loop
    free of Python-side dictionary lookups and lets the result be
    traced/compiled as a constant array.
    """
    h, w = movement["height"], movement["width"]
    result = {}

    for state, default in movement["defaults"].items():
        rates = jnp.full(
            (h, w, len(movement["directions"])),
            default,
            dtype=jnp.float64,
        )

        for (row, col), overrides in movement["overrides"][state].items():
            for direction, rate in overrides.items():
                idx = list(movement["directions"]).index(direction)
                rates = rates.at[row, col, idx].set(rate)

        result[state] = rates

    return result


# ============================================================
# 3. Movement calculations
# ============================================================

def movement_delta(y, model, movement, rates):
    """
    Calculate net movement for all cells from one shared snapshot.

    Outgoing flux is subtracted from the source and added to the
    destination. Invalid outward flux is blocked when wrap=False.

    Everything is vectorized: `jnp.roll` shifts the whole flux grid by
    (dr, dc), so a single shift both removes flux from every source cell
    and deposits it into every destination cell. Reading from the same
    snapshot `y` (rather than an already-updated array) makes this a
    symmetric exchange, so total population is conserved up to blocked
    boundary flux.
    """
    h, w = model["height"], model["width"]
    delta = jnp.zeros_like(y)

    rows = jnp.arange(h)[:, None]
    cols = jnp.arange(w)[None, :]

    for i, state in enumerate(model["states"]):
        population = y[..., i]
        state_delta = jnp.zeros_like(population)

        for d, (dr, dc) in enumerate(movement["directions"].values()):
            flux = population * rates[state][..., d]

            if not movement["wrap"]:
                # Boolean mask over (height, width) selecting cells whose
                # destination is on-grid. Multiplying zeroes blocked flux.
                valid = (
                    (rows + dr >= 0) & (rows + dr < h)
                    & (cols + dc >= 0) & (cols + dc < w)
                )
                # Blocked movement remains at its source.
                flux = flux * valid

            # Same flux leaves one cell and enters another.
            state_delta = (
                state_delta - flux
                + jnp.roll(flux, shift=(dr, dc), axis=(0, 1))
            )

        delta = delta.at[..., i].set(state_delta)

    return delta


# ============================================================
# 4. Simulation
# ============================================================

SOLVERS = ("euler", "rk4", "rk45")


def simulate(
    model,
    initial_conditions,
    parameters,
    steps,
    dt=0.1,
    movement=None,
    movement_mode="continuous",
    solver="rk4",
):
    """
    movement_mode:
      "continuous": movement rates are per unit time and are included
                    in the ODE integrated by the chosen solver.
      "discrete":   first integrate local ODEs over dt, then move the
                    specified fraction of each cell's population.
                    Rates are fractions per step in this mode.

    solver: one of "euler", "rk4" or "rk45" (Dormand-Prince). Each
            advances the state by a fixed step dt; they trade accuracy
            for cost ("euler" < "rk4" < "rk45" evaluations per step).

    State layout throughout is a single array y of shape
    (height, width, number_of_states). Local reaction and grid movement
    are merged into one RHS so the whole thing can be handed to a single
    compiled time loop.
    """
    if steps < 1 or dt <= 0:
        raise ValueError("steps and dt must be positive")
    if movement_mode not in ("continuous", "discrete"):
        raise ValueError(
            "movement_mode must be 'continuous' or 'discrete'"
        )
    if solver not in SOLVERS:
        raise ValueError(f"solver must be one of {SOLVERS}")

    missing = set(model["parameters"]) - set(parameters)
    if missing:
        raise ValueError(f"Missing parameters: {sorted(missing)}")

    missing_states = set(model["states"]) - set(initial_conditions)
    extra_states = set(initial_conditions) - set(model["states"])
    if missing_states or extra_states:
        raise ValueError(
            f"Initial conditions mismatch; missing={missing_states}, "
            f"extra={extra_states}"
        )

    h, w = model["height"], model["width"]

    def grid_array(value):
        # Normalize scalar or (height, width) input to a grid, so a
        # single parameter value can broadcast against per-cell inputs.
        arr = jnp.asarray(value, dtype=jnp.float64)
        if arr.ndim == 0:
            return jnp.broadcast_to(arr, (h, w))
        if arr.shape != (h, w):
            raise ValueError(
                f"Expected scalar or grid of shape {(h, w)}, "
                f"got {arr.shape}"
            )
        return arr

    # Bundle the initial state dict into one (h, w, states) array along
    # the trailing axis - the canonical layout the whole simulation uses.
    y0 = jnp.stack(
        [grid_array(initial_conditions[s]) for s in model["states"]],
        axis=-1,
    )

    params = {p: grid_array(parameters[p]) for p in model["parameters"]}
    local_rhs = model["rhs"]

    if movement is not None:
        if (movement["height"], movement["width"]) != (h, w):
            raise ValueError("Movement grid size does not match model")
        rates = build_movement_rates(movement)
    else:
        rates = {}

    # Discrete fractions cannot sum to more than 1 per cell/state.
    if movement is not None and movement_mode == "discrete":
        for state, rate_grid in rates.items():
            total_fraction = jnp.sum(rate_grid, axis=-1)
            if bool(jnp.any(total_fraction > 1.0 + 1e-12)):
                raise ValueError(
                    f"Discrete outgoing fractions for {state} exceed "
                    "100% in at least one cell"
                )

    # One RHS for the integrator: reaction term plus, in continuous mode,
    # the movement term. In discrete mode movement is applied separately
    # after the local step (see `advance`), so it is added here only when
    # continuous.
    def full_rhs(y):
        dy = local_rhs(y, params)
        if movement is not None and movement_mode == "continuous":
            dy = dy + movement_delta(y, model, movement, rates)
        return dy

    # Fixed-step integrators. Each is pure array arithmetic over
    # `full_rhs`, which is what lets JAX trace and compile them.

    # Forward Euler: one evaluation, first-order accurate.
    def euler_step(y):
        return y + dt * full_rhs(y)

    # Classic 4th-order Runge-Kutta.
    def rk4_step(y):
        k1 = full_rhs(y)
        k2 = full_rhs(y + (dt / 2) * k1)
        k3 = full_rhs(y + (dt / 2) * k2)
        k4 = full_rhs(y + dt * k3)
        return y + (dt / 6) * (k1 + 2*k2 + 2*k3 + k4)

    # Dormand-Prince 5(4) - the 5th-order solution of the embedded RK45
    # pair. Six evaluations per step give 5th-order accuracy (the extra
    # stage needed only for the embedded error estimate is omitted since
    # the output is sampled on a fixed grid).
    def rk45_step(y):
        k1 = full_rhs(y)
        k2 = full_rhs(y + dt * (1/5) * k1)
        k3 = full_rhs(y + dt * (3/40 * k1 + 9/40 * k2))
        k4 = full_rhs(
            y + dt * (44/45 * k1 - 56/15 * k2 + 32/9 * k3)
        )
        k5 = full_rhs(
            y + dt * (
                19372/6561 * k1 - 25360/2187 * k2
                + 64448/6561 * k3 - 212/729 * k4
            )
        )
        k6 = full_rhs(
            y + dt * (
                9017/3168 * k1 - 355/33 * k2 + 46732/5247 * k3
                + 49/176 * k4 - 5103/18656 * k5
            )
        )
        return y + dt * (
            35/384 * k1 + 500/1113 * k3 + 125/192 * k4
            - 2187/6784 * k5 + 11/84 * k6
        )

    step_local = {
        "euler": euler_step,
        "rk4": rk4_step,
        "rk45": rk45_step,
    }[solver]

    def advance(y, _):
        # Always integrate local ODEs first.
        y_next = step_local(y)

        # Discrete movement happens after the local ODE step.
        if movement is not None and movement_mode == "discrete":
            y_next = y_next + movement_delta(
                y_next, model, movement, rates
            )

        # scan expects (carry, output); returning y_next twice keeps the
        # full trajectory while threading the state to the next step.
        return y_next, y_next

    @jax.jit
    def integrate(y):
        # jax.lax.scan is the JIT-friendly replacement for a Python loop:
        # the `steps` count is static, so the body is traced once and
        # executed without per-iteration Python overhead. `None` is a
        # dummy xs for the step index. We prepend y0 to the stacked
        # per-step outputs to get steps+1 saved frames.
        _, tail = jax.lax.scan(
            advance, y, None, length=steps
        )
        return jnp.concatenate([y[jnp.newaxis, ...], tail], axis=0)

    trajectory = integrate(y0)

    return {
        "grid": {"width": w, "height": h},
        "dt": dt,
        "steps": steps,
        "movement_mode": movement_mode,
        "solver": solver,
        "times": (jnp.arange(steps + 1) * dt).tolist(),
        "states": {
            state: trajectory[..., i].tolist()
            for i, state in enumerate(model["states"])
        },
    }




################################################################################
# Example: SIR on a 4x4 grid
################################################################################
def demo1():
    equations = [
        "dS/dt = -beta*S*I",
        "dI/dt = beta*S*I - gamma*I",
        "dR/dt = gamma*I",
    ]

    model = parse_system(equations, width=4, height=4)

    # Initialize all cells to zero, except cell (0, 0) and (3, 3).
    # .at[row, col].set(v) is JAX's functional update: it returns a new
    # array, which is why the result is reassigned.
    initial = {
        state: jnp.zeros((4, 4), dtype=jnp.float64)
        for state in model["states"]
    }
    initial["S"] = initial["S"].at[0, 0].set(990)
    initial["I"] = initial["I"].at[0, 0].set(10)

    initial["S"] = initial["S"].at[3, 3].set(990)
    initial["I"] = initial["I"].at[3, 3].set(10)


    movement = create_movement(
        model,
        default_rate=0.02,
        directions=8,
        wrap=False,
    )

    # Undesirable cell: triple the default outgoing rate.
    for state in model["states"]:
        set_cell_movement_rate(movement, state, 2, 2, 0.06)

    result = simulate(
        model,
        initial_conditions=initial,
        parameters={"beta": 0.0003, "gamma": 0.1},
        steps=100,
        dt=0.1,
        movement=movement,
        movement_mode="discrete",  # or "continuous"
    )

    # Inspect S at time index 10, row 2, column 2.
    print("S at time", result["times"][10])
    print(result["states"]["S"][10][2][2])

    # Check total population over time.
    totals = []
    for t in range(len(result["times"])):
        total = sum(
            jnp.sum(jnp.asarray(result["states"][s][t]))
            for s in model["states"]
        )
        totals.append(float(total))

    print("Initial total population:", totals[0])
    print("Final total population:", totals[-1])

    with open("simulation.json", "w") as f:
        json.dump(result, f)

    print("Results written to simulation.json")


if __name__ == "__main__":
    demo1()
