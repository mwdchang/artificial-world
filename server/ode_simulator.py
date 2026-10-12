"""Run a grid ODE simulation from a world JSON file.

This mirrors grid_ode.demo1() but pulls the ODE system, initial
conditions, parameters and per-cell movement from a world definition
instead of hardcoded values.

World mapping:
  - world["equations"]                  ODE system (list of "dState/dt = expr")
  - numeric variable named <state>      initial condition for that state
  - numeric variable named <parameter>  value for a non-state equation symbol
  - movement variable named
    "<state>_dispersal"                 per-cell 8-direction movement rates
                                        for that state

Usage:
  python ode_simulator.py worlds/Test123.json
  python ode_simulator.py worlds/Test123.json --steps 200 --dt 0.05 \
      --movement-mode continuous --wrap --output result.json
"""

import argparse
import json
import re
from pathlib import Path

import jax.numpy as jnp

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
    """Return a single (height, width) grid for a numeric variable."""
    grid_type = variable.get("gridType")
    data = variable.get("data")

    if grid_type == "timeVarying":
        if isinstance(data, list) and data:
            return data[0]
        keyframes = variable.get("keyframes") or []
        if keyframes:
            return keyframes[0].get("data")
        raise ValueError(
            f"Time-varying variable '{variable.get('name')}' has no frames"
        )

    return data


def validate_grid(grid, height, width, label):
    if not isinstance(grid, list) or len(grid) != height:
        raise ValueError(
            f"Variable '{label}' grid does not match world size {width}x{height}"
        )
    for row in grid:
        if not isinstance(row, list) or len(row) != width:
            raise ValueError(
                f"Variable '{label}' grid does not match world size {width}x{height}"
            )


def build_initial_conditions(world, states):
    height, width = world["height"], world["width"]
    initial = {}
    for state in states:
        variable = find_variable(world, state, "numeric")
        if variable is None:
            raise ValueError(
                f"ODE state '{state}' has no numeric variable named '{state}'"
            )
        grid = extract_grid(variable)
        validate_grid(grid, height, width, state)
        initial[state] = grid
    return initial


def build_parameters(world, parameters):
    height, width = world["height"], world["width"]
    resolved = {}
    for name in parameters:
        variable = find_variable(world, name, "numeric")
        if variable is None:
            raise ValueError(
                f"Parameter '{name}' has no numeric variable named '{name}'"
            )
        grid = extract_grid(variable)
        validate_grid(grid, height, width, name)
        resolved[name] = grid
    return resolved


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
        initial = build_initial_conditions(world, model["states"])
        parameters = build_parameters(world, model["parameters"])
        movement = build_movement(world, model, args.wrap)

        result = simulate(
            model,
            initial_conditions=initial,
            parameters=parameters,
            steps=args.steps,
            dt=args.dt,
            movement=movement,
            movement_mode=args.movement_mode,
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
    print(f"Steps:           {args.steps} (dt={args.dt}, mode={args.movement_mode})")
    print(f"Initial total:   {total_population(result, 0):.6g}")
    print(f"Final total:     {total_population(result, -1):.6g}")
    print(f"Results written: {output_path}")


if __name__ == "__main__":
    main()
