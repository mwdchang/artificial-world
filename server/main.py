import json
import os
import re
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

WORLDS_DIR = Path(__file__).resolve().parent.parent / "worlds"
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


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse({"error": "Endpoint not found"}, status_code=404)


ensure_worlds_dir()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
