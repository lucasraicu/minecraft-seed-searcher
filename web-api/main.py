import asyncio
import random
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SweepRequest(BaseModel):
    required_structures: list[str]
    biome_family: str
    terrain_spec: str

is_running = False

@app.post("/api/start-sweep")
async def start_sweep(req: SweepRequest):
    global is_running
    is_running = True
    print(f"Starting sweep with config: {req}")
    # TODO: Bridge to C backend (`src/seed_search/realm/runner.py`)
    return {"status": "started", "config": req.dict()}

@app.post("/api/stop-sweep")
async def stop_sweep():
    global is_running
    is_running = False
    return {"status": "stopped"}

@app.websocket("/api/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    global is_running

    seeds = 1452039
    candidates = 24
    progress = 42.5

    try:
        while True:
            if is_running:
                # Mock telemetry data
                seeds += random.randint(10000, 50000)
                progress += 0.05
                if progress > 100:
                    progress = 0
                if random.random() > 0.95:
                    candidates += 1

                await websocket.send_json({
                    "seeds_per_sec": seeds,
                    "candidates_found": candidates,
                    "progress_percent": round(progress, 1),
                    "status": "running"
                })
            else:
                await websocket.send_json({
                    "status": "idle"
                })

            await asyncio.sleep(1)
    except Exception as e:
        print(f"Client disconnected: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
