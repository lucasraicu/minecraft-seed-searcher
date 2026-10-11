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
