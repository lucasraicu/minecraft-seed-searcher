"""Bundle the 4 primary audit source files into AUDIT_SOURCE_BUNDLE.md."""
from pathlib import Path

files = [
    ('native/blueprint_dynamic.inc', 'C11 Dynamic Envelope Evaluation Kernel'),
    ('native/blueprint_batch.inc', 'C11 OpenMP Batch Runner & Memory Manager'),
    ('src/seed_search/realm/blueprint.py', 'Python Reference Scoring Oracle & Differential Evaluator'),
    ('src/seed_search/realm/dynamic.py', 'Python Spatial Helpers & Nether Lattice Sampler')
]

out = [
    '# Minecraft Seed Searcher — Full Source Code Bundle for Deep Audit\n',
    '> **Files Included:**\n',
    '> 1. `native/blueprint_dynamic.inc`\n',
    '> 2. `native/blueprint_batch.inc`\n',
    '> 3. `src/seed_search/realm/blueprint.py`\n',
    '> 4. `src/seed_search/realm/dynamic.py`\n\n---\n'
]

for rel_path, desc in files:
    p = Path(rel_path)
    content = p.read_text()
    lang = 'c' if rel_path.endswith('.inc') else 'python'
    fence = '```'
    out.append(f'## File: `{rel_path}` ({desc})\n\n{fence}{lang}\n{content}\n{fence}\n\n---\n')

target = Path('AUDIT_SOURCE_BUNDLE.md')
target.write_text('\n'.join(out))
print(f'Created {target} successfully, size: {target.stat().st_size:,} bytes ({len(target.read_text().splitlines()):,} lines)')
