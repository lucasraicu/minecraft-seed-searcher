# GPU numerical and handoff contract v1

Defined October 22, 2026 for the approved readiness task. **Contract only: no GPU
kernel, GPU adoption, fleet throughput claim or engine migration is implemented.**
The [machine-readable companion](gpu_contract_v1.json) pins the current reference;
[CPU vectors](../../reviews/pre-gpu-implementation-2026-10-22/CPU_REFERENCE_VECTORS.json)
make its integer, coordinate and first raw-placement cases executable.

## Authority and scope

The frozen CPU source/build and exact outputs are authoritative. Current policies,
registry, sampling profiles and numerical identities must accompany a device build;
no kernel may quietly reinterpret a different Bedrock model or world-settings ID.
Source authority is `src/seed_search/seeds.py`, `backend.py`, `native/filters.inc`,
`vendor/cubiomes-bedrock/`, `realm/config.py`, `realm/native_records.py`, and the
catalog geometry, coverage, codec, request, query, retention and reserve contracts.
The full personal configuration is saved with the CPU vectors.

The existing host is an AMD Radeon Pro Vega 56/8GB iMac. The intended conversion
host, GPU model/count/VRAM, OS, driver and compiler are **not selected or verified**.
This contract supports a later bounded one-device proposal. It does not authorize
CUDA specifically or require an unavailable local CUDA toolchain.

## 1. Seed identity and finite input population

- External seeds are canonical signed decimal strings in `[-2^63, 2^63-1]`.
  Transport may carry the corresponding unsigned 64-bit bit pattern, little endian.
  Never pass seeds through JavaScript Number, floating point or a lower-32-bit ID.
- Candidate indices and on-wire run-key bit patterns are unsigned 64-bit values.
  Existing signed CPU run keys are normalized with `& MASK64`, preserving their
  interpretation. Full64 generation is
  exactly `seed_from_index`: add run key modulo 2^64; xor/shift/multiply with
  `0xBF58476D1CE4E5B9` and `0x94D049BB133111EB`, masking each multiplication; final
  xor-right-shift31; convert the bit pattern to its signed representation.
- Strided generation is exactly `seed_strided`: finite unsigned high32 index plus
  the low32 bits of the declared signed seed. Validate the entire range before
  masking. Do not wrap a range past 2^32 or 2^64, duplicate indices, or alias siblings.
- Every job declares its sequence, exact range/manifest, sampler version and public
  evaluated population. Repeated benchmark inputs are not new unique seeds.
  Invalid integers, bools, malformed IDs and out-of-range buffers fail validation.

## 2. Independent personal and public admission

Let `P` be the explicitly selected public evaluated population and `O` its targeted
objectives. For every `s` in `P`, the pipeline must deliver a CPU-evaluable candidate
or retain a conservative proof that it cannot improve any applicable objective in
`O`, including all relevant anchors, dimensions, scopes and tie-breaking fields.
A personal-floor failure or personal Top-K cutoff is never such a public proof.

Personal and public selection must bifurcate **before** personal rejection. An
independent public sampler can select from the original stream, or the public branch
can bypass personal screening. Public sampling may be bounded, but its selection
and unvisited counts must be explicit. This does not claim exhaustive coverage of
all 2^64 seeds outside `P` or that current retained worlds are global optima.

Optional public pruning needs a reviewed conservative upper bound and objective
cutoff generation. Unknown, missing, unsupported, incomplete or overflowed evidence
cannot prove rejection. A score tie is retained unless the complete ordering proves
it cannot improve. Initial kernels should forward public-selected seeds unchanged.

## 3. Integer placement, coordinates and provider boundaries

- Match the pinned C PRNG, salt, region seed and raw structure-placement behavior,
  including unsigned 32/64-bit overflow, exact shift widths and region ordering.
  Do not replace an upstream generator with a similarly named generic RNG.
- Raw attempts, viable starts, predicted variants, biome samples and generated game
  structures are separate evidence types. A raw-placement kernel cannot certify
  viability, generated structures, terrain safety or absence.
- Preserve full signed X/Z and Y. Nether anchors use mathematical floor division
  by eight: `-1 // 8 = -1`, not truncation toward zero. Apply the same rule at negative
  region/tile boundaries. No implicit coordinate clamping or origin substitution.
- Overworld layout sides remain 2048/4096/8192; Nether remains 1024. Borders are
  half-open `[x0,x1) × [z0,z1)`. Near-base membership uses inclusive squared radius
  intersected with that border, with Overworld radii 256/512/1024 and Nether 64/128/256.
- Use sufficiently wide intermediates. Within the codec's coordinate domain,
  squared distances fit signed int64; ranking expressions such as
  `isqrt(distance_squared * 10^12)` require wider arithmetic or CPU evaluation.
  Never let a 64-bit multiplication silently overflow a ranking key.

## 4. Counts, biomes, coverage and anchors

Factual V3 counts are uint32-compatible integers up to the existing validated bound
of 200,000; the UI threshold maximum 32 is not a storage cap. Count, completeness
and overflow/error state are separate fields. Overflow fails or falls back; it must
not saturate into a valid fact. Frozen V1/V2 wire adapters remain compatible.

The runtime registry defines 56 exact Overworld choices, five Nether choices, four
groups and all current structure options. Eligible sampled heights, canonical names,
group overlap, provider/dimension and sampling-profile identity are part of a biome
fact. A missing sampled witness remains unknown; zero samples is not exact absence.
Unavailable features stay unavailable. Preserve partial stronghold coverage.

Required rows must hold at the same anchor; alternatives within one biome row mean
ANY. Preserve origin, recommended and estimated/observed spawn modes, source anchor
identities, overlapping-mode layouts and exact witness ordering. Estimated spawn is
not a certified player landing. No GPU stage may promote pending evidence to complete.

## 5. Scoring, reserves and exact ordering

The pinned CPU configuration and scorer remain normative for the 845/265/140 budgets,
mandatory floors, caps, distances, profile arithmetic and stable tie keys. Initial
GPU work does not port the scorer. Preserve exact ranks, signed seeds, distinct-world
selection, anchors, witnesses and unknown/pending results; retain Decimal/integer
precision rather than converting sort keys to binary float.

New personal Top-50 runs retain 100 distinct candidates, including reserve, throughout
heap filling and cutoff propagation. No cutoff is valid before capacity is filled.
Historical 50-capacity runs keep their original policy. Public retention is 2K per
objective: 7,543 objectives, 115,964 primary and 231,928 total membership slots.
Membership slots do not mean unique worlds. Per-objective roles are not global flags.

Any later floating-point port must declare precision and compiler flags, compare
against the pinned CPU math at threshold/tie boundaries and use conservative CPU
fallback when exact classification cannot be established. Fast-math, altered noise,
reduced height coverage or approximate ranking is a separate reviewed contract.

## 6. Batched transport and output completeness

The first implementation plan must freeze a concrete binary ABI. This contract
requires a versioned header containing run/batch ID, contract digest, CPU/device
source/build/compiler IDs, policy/registry/provider/profile IDs, sequence/range,
input count, bounds, output capacity and declared supported stages.

Input is an ordered uint64 seed-bit buffer plus original input indices when needed.
Output carries each original index and seed identity, explicit per-branch verdict,
error/completeness bits and typed variable-length fact/witness sections. All sizes,
offsets, lengths, enum values and integer ranges are validated before interpretation.
A fixed authoritative 64-byte record is not assumed.

Compaction may change physical order but cannot lose, duplicate or invent indices.
The receiver restores canonical order or validates an equivalent complete index map.
A sparse payload needs an explicit disposition bitmap for every input. An omitted
record is not silently a rejected public candidate. Checksum frames and reject
truncation, stale IDs, reordered offsets and unsupported versions.

Buffer overflow triggers bounded deterministic subdivision/retry or an error/pending
receipt; never drop a tail. Record transferred bytes and compaction/transfer time.
Choose batch size from measured VRAM, worst-case output and host limits. Existing
queue, memory, IPC, cache and disk caps remain effective; they are not device defaults.

### Concrete frame v1

The initial wire envelope is defined, even though no transport is implemented:

| Section | Packed little-endian record | Bytes |
|---|---|---:|
| Prefix | `<8sIQ32s32s`: magic `SSGPUV1` plus NUL, header length, payload length, header SHA256, payload SHA256 | 84 |
| Inputs | `<QQII`: original index, seed bits, selection flags, reserved zero | 24 |
| Verdicts | `<QQBBHI`: original index, seed bits, personal/public verdict, error flags, stage-completeness flags | 24 |
| Facts | `<IHBBiiiI`: input ordinal, feature slot, evidence kind, dimension, X/Y/Z, value | 24 |
| Coverage | `<IHBBiiiiBBHI`: input ordinal, feature slot, stage, dimension, half-open bounds, status, method slot, height-profile slot, reserved zero | 32 |

The prefix is followed by canonical finite UTF8 JSON header bytes and payload bytes.
The entire frame is at most 4MiB; the header is at most 64KiB; 1–16,384 inputs
and two frames/8MiB of host transport may be in flight. Header section descriptors
state exact offsets/counts/record sizes. Sections cannot overlap or escape payload
bounds, and trailing bytes are invalid. Header methods and height profiles define
slot interpretation. Registry order pins feature slots. See JSON for exact enums.

CPU-owned input flags declare personal-enabled and public-selected membership.
Verdict records cover every input exactly once. Facts/coverage refer to valid input
ordinals. Y=`INT32_MIN` means undefined structure height, never a biome Y. Initial
raw village facts use value zero, raw-attempt evidence kind and explicit raw-region
coverage; their completeness cannot imply viability or a game structure. Reserved
bits/fields must be zero and unsupported enums fail validation.

Initial operations are finite full64/strided seed mapping and raw village region
attempts. For seed mapping, input seed bits are zero and the header carries the
sequence parameters; verdict seed bits contain the generated result. Raw placement
uses supplied seed bits and declared regions. Enabled branches forward to CPU;
public-selected inputs cannot return not-selected. Proven-rejection verdicts are
reserved and forbidden for these initial operations. Any pruning-capable operation
requires its own proof and reviewed capability addition.

## 7. Durable progress, failure and backpressure

A batch receipt binds its full input coverage and source identities to both branch
outcomes and durable downstream ownership. Commit observations/output and consumed
budget before acknowledging progress. Out-of-order completion can use explicit ranges;
a single high-water mark advances only over a contiguous acknowledged prefix.

Retry is idempotent by source-bound run/batch/range identity. Duplicate arrivals do
not duplicate worlds, charge away already-accounted budgets or reset allocations.
A crash before acknowledgement can replay only the declared bounded quantum; a crash
after acknowledgement must recover all committed facts and consumed budgets. Corrupt
progress fails closed; never fall back to a snapshot that loses acknowledged deltas.
Personal completion alone cannot acknowledge an unfinished public branch.

A bounded host queue controls emission. When full, pause the emitter or retain a
bounded durable replay descriptor; do not allocate an unbounded GPU/host buffer,
quietly strengthen filtering or discard selected public inputs. Specify maximum
in-flight batches, bytes, retries, leases, time and disk before a kernel trial.
GPU workers submit through the coordinator; they do not write a shared SQLite WAL
file over a network filesystem or own personal/live processes.

## 8. CPU fallback and compatibility

Unsupported provider, feature, geometry, overflow, device loss or parity mismatch
routes to the pinned CPU evaluator within its existing budget, or remains pending.
It must not fabricate a zero, pass or completeness flag. Kernel/schema changes use
new explicit identities; old checkpoints, snapshots, cursors, pins, shares, reserves
and verification receipts keep their original interpretation.

The optimized derivation is source-pinned separately for new workspaces. Existing
catalog configurations retain the historical implementation. Before production
concurrent writers, adopt a SQLite runtime containing the documented WAL-reset fix
(or a separately validated control engine). A private SQLite 3.54.1 environment was
validated in this task; the live bundled 3.50.4 runtime was not replaced.

## 9. Acceptance before any GPU implementation is adopted

1. Confirm one actual device/host/toolchain and exact CPU/device source/build IDs.
2. Start with one integer kernel, such as seed mapping or raw village placement.
   Run the frozen CPU vectors plus signed extrema, low32 siblings, negative regions,
   border corners, duplicate/tie, incomplete and adversarial output cases.
3. Compare fixed work, not equal wall-time budgets. Require exact classifications,
   coordinates, counts, IDs, witnesses and ordering for every claim being ported.
   Keep other stages authoritative on CPU. Predictor parity is not game certification.
4. Exercise overflow/subdivision, malformed frames, duplicates, reordering, device
   loss, cancellation, full queues, lease expiry, durable commit/ack crashes and restart.
5. Measure kernel, compaction, transfers, CPU verification, queueing, serialization,
   derivation, publication and guarded queries separately, and then end to end.
6. Report raw input seeds/sec, selected candidates/sec, completed full observations/sec
   and retained useful worlds/hour separately. Demonstrate useful improvement beyond
   variability at fixed work without weaker admission, evidence or resource bounds.
7. Keep CPU fallback and a tested rollback path. Pass the numerical contract and
   CPU/catalog sustained acceptance before integrating high-volume output.

No 100M-seeds/sec, zero-cost harvesting, 2/4/8-device scaling or production SLA follows
from this contract or the current CPU benchmark. A bounded kernel implementation
plan and its approval remain future work.
