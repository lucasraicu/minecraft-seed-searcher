# Disk budget diagnostic fix

The active survivor policy estimates 32 bytes per seed, with a 128 GiB run cap and 16 GiB free-space reserve. The filesystem had approximately 636 GiB free. The original failed request body was not logged, so its seed count cannot be established retrospectively. The current 10-million-seed default passes; a 5-billion-seed request reproduces the cap failure.

Shared projection validation now reports the limiting budget, projected size, available disk, reserve, and estimated remaining seed capacity. Preview checks the same disk policy as launch; runtime monitoring retains the same safeguards. No budget or blueprint rules were relaxed. Browser verification reproduced the error at 5 billion and restored 10 million without launching a sweep.

Verification: 37 Python tests passed (disk resources, web evidence, machine contract, and new preview cases); frontend build and lint passed. Dashboard/server refreshed. diagnostic.png shows the oversized-request feedback.
