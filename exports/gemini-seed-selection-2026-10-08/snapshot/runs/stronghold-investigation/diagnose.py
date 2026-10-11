"""Read-only iterator experiments; these variants are NOT production predictions.

Run from the project root with .venv/bin/python runs/stronghold-investigation/diagnose.py.
Uses the installed backend for MT and village placement/viability. Does not change it.
"""
import ctypes
import itertools
import json
import math
from pathlib import Path

from seed_search import _native
from seed_search.backend import Backend, biome_name

native = ctypes.CDLL(_native.__file__)
native.mt_seed.argtypes = [ctypes.c_uint32]
native.mt_seed.restype = None
native.mt_next.argtypes = []
native.mt_next.restype = ctypes.c_uint32
f32 = lambda x: ctypes.c_float(x).value


def replay(seed, rounding_x, rounding_z, eligibility):
    native.mt_seed(seed & 0xffffffff)
    angle = f32(2 * math.pi * f32(native.mt_next() / 4294967296))
    distance = 40 + native.mt_next() % 16
    accepted, trace = [], []
    rounders = {"floor": math.floor, "truncate": int}
    with Backend(seed) as backend:
        cache = {}
        for step in range(10000):
            cx = rounders[rounding_x](math.cos(angle) * distance)
            cz = rounders[rounding_z](math.sin(angle) * distance)
            candidates = []
            for rx in range((cx - 8) // 34, (cx + 7) // 34 + 1):
                for rz in range((cz - 8) // 34, (cz + 7) // 34 + 1):
                    if (rx, rz) not in cache:
                        p = backend.attempt("village", rx, rz)
                        viable = bool(p and backend.structures("village", (*p, *p)))
                        name = biome_name(backend.biome(p[0], 319, p[1])) if p else None
                        cache[rx, rz] = p, viable, name
                    p, viable, name = cache[rx, rz]
                    if not p or not viable:
                        continue
                    if eligibility == "exclude_snow" and name in {"snowy_plains", "snowy_taiga"}:
                        continue
                    if eligibility == "legacy" and name not in {"plains", "desert", "savanna", "taiga"}:
                        continue
                    if cx - 8 <= p[0] // 16 <= cx + 7 and cz - 8 <= p[1] // 16 <= cz + 7:
                        candidates.append(p)
            if candidates:
                p = min(candidates)
                accepted.append([p[0] - 4, p[1] - 4])
                trace.append({"step": step, "angle": angle, "distance": distance,
                              "center_chunks": [cx, cz], "village": list(p)})
                if len(accepted) == 3:
                    return {"seed": str(seed), "x_rounding": rounding_x, "z_rounding": rounding_z,
                            "eligibility": eligibility, "positions": accepted, "trace": trace}
                angle += f32(0.6) * math.pi
                distance += 8
            else:
                angle += f32(0.25) * math.pi
                distance += 4
    raise RuntimeError("Diagnostic iteration bound reached")


if __name__ == "__main__":
    results = [replay(seed, x, z, eligibility) for seed, x, z, eligibility in itertools.product(
        [-1, 0, 12345, 4294979641], ["floor", "truncate"], ["floor", "truncate"],
        ["native", "exclude_snow", "legacy"])]
    destination = Path(__file__).with_name("axis-and-eligibility-variants.json")
    destination.write_text(json.dumps(results, indent=2) + "\n")
    for row in results:
        print(row["seed"], row["x_rounding"], row["z_rounding"], row["eligibility"], row["positions"])
