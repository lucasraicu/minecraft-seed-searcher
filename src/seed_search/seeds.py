MASK32 = (1 << 32) - 1
MASK64 = (1 << 64) - 1

def parse_seed(value: str | int) -> int:
    if isinstance(value, bool):
        raise ValueError("Seed must be a signed decimal integer")
    text = str(value).strip()
    if not text or not text.lstrip("-").isdigit() or text.count("-") > 1:
        raise ValueError("Seed must be a signed decimal integer")
    seed = int(text)
    if not -(1 << 63) <= seed < (1 << 63):
        raise ValueError("Seed outside signed 64-bit range")
    return seed

def seed_from_index(index: int, run_key: int = 0) -> int:
    if not 0 <= index <= MASK64:
        raise ValueError("Candidate index outside unsigned 64-bit range")
    z = (index + run_key) & MASK64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    z ^= z >> 31
    return z if z < (1 << 63) else z - (1 << 64)

def seed_strided(index: int, low32: int | str) -> int:
    """Generate a 64-bit world seed from upper sibling index and lower 32-bit seed.

    worldSeed = (low32 & MASK32) | ((index & MASK32) << 32)
    Returned as signed 64-bit integer.
    """
    if isinstance(index, bool) or not isinstance(index, int):
        raise ValueError("Candidate index must be an integer")
    if not 0 <= index <= MASK64:
        raise ValueError("Candidate index outside unsigned 64-bit range")
    if isinstance(low32, str):
        low32 = parse_seed(low32)
    elif isinstance(low32, bool) or not isinstance(low32, int):
        raise ValueError("low32 must be an integer or integer string")
    if not -(1 << 63) <= low32 < (1 << 63):
        raise ValueError("low32 outside 64-bit range")
    z = (low32 & MASK32) | ((index & MASK32) << 32)
    return z if z < (1 << 63) else z - (1 << 64)

def seeds_strided(start_index: int, count: int, low32: int | str) -> list[int]:
    """Generate a strided sequence of 64-bit seeds sharing a 32-bit lower seed.

    Each seed is formed as: worldSeed = (low32 & MASK32) | ((high32 & MASK32) << 32)
    where high32 is the upper 32-bit sibling index (start_index <= high32 < start_index + count).
    Seeds are returned as signed 64-bit integers.
    """
    if isinstance(start_index, bool) or not isinstance(start_index, int) or start_index < 0:
        raise ValueError("Candidate start index outside unsigned range")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("Candidate count must be non-negative")
    if start_index + count > MASK64 + 1:
        raise ValueError("Range exceeds 64-bit bounds")
    if isinstance(low32, str):
        low32 = parse_seed(low32)
    elif isinstance(low32, bool) or not isinstance(low32, int):
        raise ValueError("low32 must be an integer or integer string")
    if not -(1 << 63) <= low32 < (1 << 63):
        raise ValueError("low32 outside 64-bit range")

    low = low32 & MASK32
    results = []
    for high in range(start_index, start_index + count):
        val = low | ((high & MASK32) << 32)
        results.append(val if val < (1 << 63) else val - (1 << 64))
    return results
