"""Run a grid ODE simulation from a world JSON file.

This mirrors grid_ode.demo1() but pulls the ODE system, initial
conditions, parameters and per-cell movement from a world definition
instead of hardcoded values.

World mapping:
  - world["equations"]                  ODE system (list of "dState/dt = expr")
  - numeric variable named <state>      distribution grid sampled for that state
  - numeric variable named <parameter>  distribution grid sampled for a parameter
  - movement variable named
    "<state>_dispersal"                 per-cell 8-direction movement rates
                                        for that state

Usage:
  python ode_simulator.py worlds/Test123.json
  python ode_simulator.py worlds/Test123.json --steps 200 --dt 0.05 \
      --movement-mode continuous --solver rk45 \
      --wrap --output result.json
"""

import argparse
import json
import math
import re
from pathlib import Path

import jax.numpy as jnp

from sim_sampler import SimSampler

from grid_ode import (
    create_movement,
    parse_system,
    set_cell_movement_rate,
    simulate,
)

# Movement editor stores lowercase direction keys; the solver uses uppercase.
DIRECTION_KEY_MAP = {
    "n": "N",
    "s": "S",
    "e": "E",
    "w": "W",
    "ne": "NE",
    "nw": "NW",
    "se": "SE",
    "sw": "SW",
}


# ============================================================
# World loading / extraction
# ============================================================

def load_world(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("World file must contain a JSON object")

    for key in ("width", "height"):
        if not isinstance(data.get(key), int) or data[key] < 1:
            raise ValueError(f"World must define a positive integer '{key}'")

    equations = data.get("equations")
    if not isinstance(equations, list) or not equations:
        raise ValueError("World must define a non-empty 'equations' list")

    if not isinstance(data.get("variables"), list):
        raise ValueError("World must define a 'variables' list")

    return data


def find_variable(world, name, variable_type=None):
    for variable in world.get("variables", []):
        if variable.get("name") != name:
            continue
        if variable_type is not None and variable.get("variableType") != variable_type:
            continue
        return variable
    return None


def extract_grid(variable):
    """Return a single static (height, width) grid."""
    data = variable.get("data")
    return data


def extract_time_varying_frames(variable):
    """Return all time slices for a time-varying numeric variable."""
    data = variable.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError(
            f"Time-varying variable '{variable.get('name')}' has no data frames"
        )
    return data


def sample_numeric_grid(variable, height, width, sampler):
    return sampler.grid(
        extract_grid(variable), height, width, variable.get("name", "numeric")
    )


def sample_time_varying_grids(variable, height, width, sampler, steps, dt):
    frames = extract_time_varying_frames(variable)
    required_frames = math.floor(steps / dt) + 1
    if len(frames) != required_frames:
        raise ValueError(
            f"Simulate wants {required_frames} frames, but variable '{variable.get('name')}' has {len(frames)}"
        )

    sampled = []
    for frame in frames:
        for row in frame or []:
            for cell in row or []:
                if not isinstance(cell, dict) or cell.get("type") != "scalar":
                    raise ValueError(
                        "Time-varying numeric variables currently support only scalar distributions"
                    )
        sampled.append(
            sampler.grid(
                frame, height, width, variable.get("name", "numeric")
            )
        )
    return sampled


def build_initial_conditions(world, states, sampler):
    height, width = world["height"], world["width"]
    initial = {}
    for state in states:
        variable = find_variable(world, state, "numeric")
        if variable is None:
            raise ValueError(
                f"ODE state '{state}' has no numeric variable named '{state}'"
            )
        if variable.get("gridType") != "static":
            raise ValueError(
                f"ODE state '{state}' must be static because time-varying "
                "variables cannot have equations"
            )
        initial[state] = sample_numeric_grid(variable, height, width, sampler)
    return initial


def build_parameters(world, parameters, sampler, steps, dt):
    height, width = world["height"], world["width"]
    resolved = {}
    time_varying = {}
    for name in parameters:
        variable = find_variable(world, name, "numeric")
        if variable is None:
            raise ValueError(
                f"Parameter '{name}' has no numeric variable named '{name}'"
            )
        if variable.get("gridType") == "timeVarying":
            time_varying[name] = sample_time_varying_grids(
                variable, height, width, sampler, steps, dt
            )
        else:
            resolved[name] = sample_numeric_grid(variable, height, width, sampler)
    return resolved, time_varying


def sanitize_local_rhs(model):
    """Make the local reaction term safe against undefined cells.

    Equations like ``-beta*S*I/(S+I+R)`` are mathematically undefined
    (0/0) in cells where every state is zero, which yields NaN and then
    spreads across the grid through movement. Replace any non-finite
    derivative with 0; finite dynamics are left untouched.
    """
    original_rhs = model["rhs"]

    def safe_rhs(y, params):
        dy = original_rhs(y, params)
        return jnp.where(jnp.isfinite(dy), dy, 0.0)

    model["rhs"] = safe_rhs
    return model


def build_movement(world, model, wrap):
    """Assemble movement from '<state>_dispersal' movement variables."""
    height, width = world["height"], world["width"]
    states = model["states"]

    dispersal_vars = {
        state: find_variable(world, f"{state}_dispersal", "movement")
        for state in states
    }
    if not any(dispersal_vars.values()):
        return None

    movement = create_movement(
        model, default_rate=0.0, directions=8, wrap=wrap
    )

    for state, variable in dispersal_vars.items():
        if variable is None:
            continue
        grid = variable.get("data")
        if not isinstance(grid, list) or len(grid) != height:
            raise ValueError(
                f"Movement variable '{state}_dispersal' does not match "
                f"world size {width}x{height}"
            )

        for row in range(height):
            for col in range(width):
                rates = grid[row][col]
                if not isinstance(rates, dict):
                    continue
                override = {
                    DIRECTION_KEY_MAP[direction]: float(rates[direction])
                    for direction in DIRECTION_KEY_MAP
                    if direction in rates
                }
                if override:
                    set_cell_movement_rate(
                        movement, state, row, col, override
                    )

    return movement


# ============================================================
# CLI
# ============================================================

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run a grid ODE simulation from a world JSON file."
    )
    parser.add_argument(
        "world", help="Path to a world JSON file, e.g. worlds/Test123.json"
    )
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument(
        "--movement-mode",
        choices=["continuous", "discrete"],
        default="discrete",
    )
    parser.add_argument(
        "--solver",
        choices=["euler", "rk4", "rk45"],
        default="rk4",
        help="ODE integrator (default: rk4)",
    )
    parser.add_argument(
        "--wrap",
        action="store_true",
        help="Wrap movement across grid edges (default: blocked)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: <world_name>_simulation.json)",
    )
    return parser.parse_args(argv)


def default_output_path(world_name):
    safe = re.sub(r"[^\w\s-]", "", world_name or "world", flags=re.ASCII).strip()
    safe = safe.replace(" ", "_") or "world"
    return f"{safe}_simulation.json"


def total_population(result, time_index):
    return sum(
        sum(sum(row) for row in result["states"][state][time_index])
        for state in result["states"]
    )


def main(argv=None):
    args = parse_args(argv)

    try:
        world = load_world(args.world)
        width, height = world["width"], world["height"]

        model = parse_system(world["equations"], width=width, height=height)
        model = sanitize_local_rhs(model)
        sampler = SimSampler()
        initial = build_initial_conditions(world, model["states"], sampler)
        parameters, time_varying_parameters = build_parameters(
            world, model["parameters"], sampler, args.steps, args.dt
        )
        movement = build_movement(world, model, args.wrap)

        result = simulate(
            model,
            initial_conditions=initial,
            parameters=parameters,
            steps=args.steps,
            dt=args.dt,
            movement=movement,
            movement_mode=args.movement_mode,
            solver=args.solver,
            time_varying_parameters=time_varying_parameters,
        )
    except ValueError as err:
        raise SystemExit(f"error: {err}")

    output_path = Path(args.output or default_output_path(world.get("name")))
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"World:           {world.get('name')}")
    print(f"Grid:            {width} x {height}")
    print(f"States:          {', '.join(model['states'])}")
    print(f"Parameters:      {', '.join(model['parameters']) or '(none)'}")
    print(f"Movement:        {'yes' if movement is not None else 'none'}")
    print(f"Steps:           {args.steps} (dt={args.dt}, mode={args.movement_mode}, solver={args.solver})")
    print(f"Initial total:   {total_population(result, 0):.6g}")
    print(f"Final total:     {total_population(result, -1):.6g}")
    print(f"Results written: {output_path}")


if __name__ == "__main__":
    main()
