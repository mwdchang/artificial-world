import json
import os
import re
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WORLDS_DIR = PROJECT_ROOT / "worlds"
SIMULATIONS_DIR = PROJECT_ROOT / "simulations"
PORT = int(os.environ.get("PORT", "3001"))

app = FastAPI(redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def ensure_worlds_dir():
    try:
        WORLDS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        print(f"Failed to create worlds directory: {err}")


def ensure_simulations_dir():
    try:
        SIMULATIONS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        print(f"Failed to create simulations directory: {err}")


# def run_simulation(world_path, steps, dt=0.1, movement_mode="discrete", wrap=False):
# def run_simulation(world_path, steps, dt=0.1, movement_mode="continuous", wrap=False):
def run_simulation(world_path, steps, dt=0.1, movement_mode="discrete", wrap=False):
    """Run the ODE simulator for a world file, writing and returning the result."""
    # Imported lazily so world CRUD stays fast and does not require jax.
    import ode_simulator

    world = ode_simulator.load_world(world_path)
    width, height = world["width"], world["height"]

    model = ode_simulator.parse_system(world["equations"], width=width, height=height)
    model = ode_simulator.sanitize_local_rhs(model)
    initial = ode_simulator.build_initial_conditions(world, model["states"])
    parameters = ode_simulator.build_parameters(world, model["parameters"])
    movement = ode_simulator.build_movement(world, model, wrap)

    result = ode_simulator.simulate(
        model,
        initial_conditions=initial,
        parameters=parameters,
        steps=steps,
        dt=dt,
        movement=movement,
        movement_mode=movement_mode,
    )

    world_name = world.get("name") or world_path.stem
    output_path = SIMULATIONS_DIR / f"{sanitize_world_name(world_name)}_simulation.json"
    ensure_simulations_dir()
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


def sanitize_world_name(name):
    return re.sub(r"[^\w\s-]", "", name, flags=re.ASCII).strip()


@app.get("/api/worlds")
async def list_worlds():
    try:
        ensure_worlds_dir()
        files = os.listdir(WORLDS_DIR)
        world_names = [file[: -len(".json")] for file in files if file.endswith(".json")]
        return JSONResponse(world_names)
    except Exception as err:
        return JSONResponse(
            {"error": "Failed to read worlds", "details": str(err)}, status_code=500
        )


@app.get("/api/worlds/{world}")
async def get_world(world: str):
    world_name = sanitize_world_name(world)
    if not world_name:
        return JSONResponse({"error": "Invalid world name"}, status_code=400)

    file_path = WORLDS_DIR / f"{world_name}.json"

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return JSONResponse(data)
    except FileNotFoundError:
        return JSONResponse(
            {"error": f'World "{world_name}" not found'}, status_code=404
        )
    except Exception as err:
        return JSONResponse(
            {"error": "Failed to read world file", "details": str(err)},
            status_code=500,
        )


@app.post("/api/worlds/{world}")
async def save_world(world: str, request: Request):
    world_name = sanitize_world_name(world)
    if not world_name:
        return JSONResponse({"error": "Invalid world name"}, status_code=400)

    file_path = WORLDS_DIR / f"{world_name}.json"

    try:
        body = await request.body()
        parsed = json.loads(body)
        ensure_worlds_dir()
        file_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        return JSONResponse(
            {
                "success": True,
                "message": f'World "{world_name}" saved successfully',
                "name": world_name,
            }
        )
    except Exception as err:
        return JSONResponse(
            {
                "error": "Failed to save world. Invalid JSON or filesystem error.",
                "details": str(err),
            },
            status_code=400,
        )


@app.post("/api/worlds/{world}/simulate")
async def simulate_world(world: str, request: Request):
    world_name = sanitize_world_name(world)
    if not world_name:
        return JSONResponse({"error": "Invalid world name"}, status_code=400)

    file_path = WORLDS_DIR / f"{world_name}.json"
    if not file_path.exists():
        return JSONResponse(
            {"error": f'World "{world_name}" not found'}, status_code=404
        )

    try:
        body = await request.body()
        parsed = json.loads(body) if body else {}
        steps = int(parsed.get("steps", 50))
        stepSize = float(parsed.get('stepSize', 0.1))
    except Exception as err:
        return JSONResponse(
            {"error": "Invalid JSON body", "details": str(err)}, status_code=400
        )

    try:
        result = run_simulation(file_path, steps, stepSize)
    except ValueError as err:
        return JSONResponse({"error": str(err)}, status_code=400)
    except Exception as err:
        return JSONResponse(
            {"error": "Simulation failed", "details": str(err)}, status_code=500
        )

    return JSONResponse(result)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse({"error": "Endpoint not found"}, status_code=404)


ensure_worlds_dir()
ensure_simulations_dir()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
