# Authorized terrain-product removal — actual source review

User explicitly permits removing difficult/terrain/expensive products; remove all five from current v2 cards, keep 17 launch records, 16 presets, three Realm boards, 31 personalized filters. Preserve historical v1 IDs and immutable data. Do NOT change frozen products.json or automation policy digest. No predictor/queue/extraction change. Existing registry HTTP is parent-process code; an idle backend restart will adopt it; no personal restart or jobs.

Current targeted Python22PASS, real-registry React17PASS, frontend buildPASS. Checks are Codex-run, not reviewer claims. Review exact current sources below for missing cases/conflicts; no tools/edits required.

## Current v2 registry function
```python
def product_registry_v2():
    """Revised products replace earlier promises; legacy research stays separate."""
    result=product_registry();definitions=launch_definitions()
    # Terrain-heavy proposals remain historical v1 definitions, not launch cards.
    # Keep the frozen evaluator/retention contract unchanged for existing snapshots.
    result['products']=[]
    rows=[('realm','realm',p) for p in [definitions['realm'],*definitions.get('realm_sizes',[])]]
    rows += [('presets','preset',p) for p in definitions['presets']]
    rows += [('rare','record',p) for p in definitions['records']]
    for pillar,kind,p in rows:
        dimension=p.get('dimension','overworld')
        reference='the Nether coordinate projected from estimated world spawn (floor X/8, Z/8)' if dimension=='nether' else 'estimated world spawn'
        radius=p.get('radius');scope=dict(dimension=dimension,anchor='projected_world_spawn' if dimension=='nether' else 'world_spawn_estimated')
        if radius is not None:scope.update(radius=radius,scope_type='closed_horizontal_circle')
        category='Structure Density';criteria=''
        if kind=='realm':
            side=p['overworld_core']
            category='Shared Survival';scope=dict(dimension='overworld',anchor='realm_qualified_center',border_sides=[side])
            criteria=f'Qualify the versioned {side} Overworld / 1024 Nether Realm blueprint at one refined center. Score out of1250 points (845 Overworld,265 luxury biomes,140 Nether). '
            if side!=2048:criteria+='Frozen size-specific count floors and bonus tiers; bounded center search. Fixed1024 Nether square. Calibration controls validate rules, not seed-population prevalence.'
        elif kind=='preset':
            rename={'meadow_cherry':'alpine_meadow','village_two_shipwrecks':'shipwreck_bay','mushroom_monument':'mushroom_haven','warped_bastion':'safe_nether'}
            category=next((old[2] for old in PRESETS if old[0]==rename.get(p['id'].split('.')[-1],p['id'].split('.')[-1])),'Play Styles')
            features=[str(n)+' '+fid.removeprefix('structure.').replace('_',' ')+' predicted start(s)' for fid,n in p['structures'].items()]
            features += [family.replace('_',' ')+' biome witness' for family in p['biomes']]
            criteria=', '.join(features)+f' within {radius} {dimension} blocks of {reference}. All conditions share that reference.'
        elif p['kind']=='density':
            criteria=f'Most distinct predicted starts within {radius} {dimension} blocks of {reference}; complete scoped predictor inventory required.'
        elif p['kind']=='proximity':
            category='Start Proximity';criteria=f'Closest predicted start within {radius} {dimension} blocks of {reference}; distance is horizontal to its start coordinate.'
        elif p['kind']=='biome_sampler':
            category='Biome Exploration';criteria=f'Fourteen declared biome families witnessed within {radius} horizontal blocks of {reference}, using declared surface/cave heights. No walking-route or absence promise.'
        else:
            category='Structure Clusters'
            rules={'four_types':'Four distinct structure types, every pair at most100 blocks apart',
                   'four_huts':'Four swamp-hut starts inside one minimum enclosing circle of radius128',
                   'monument_cluster':'Two or three monument starts inside one minimum enclosing circle of radius128',
                   'nether_pair':'A fortress and bastion start at most64 Nether blocks apart'}
            criteria=rules[p['kind']]+f', all within {radius} {dimension} blocks of {reference}. No physical overlap or farm-suitability claim.'
        calibrated=kind!='realm' or p['overworld_core']==2048
        if not calibrated:
            import json
            from .registry import CONTRACT_ROOT
            policy=json.loads((CONTRACT_ROOT.parent/'v2'/'realm_scoring.json').read_text())
            from .realm_evaluation import load_calibration
            calibrated=policy['sizes'][str(p['overworld_core'])]['policy'] is not None and load_calibration() is not None
        result['products'].append(dict(id=p['id'],pillar_id=pillar,kind=kind,label=p['label'],category=category,
            criteria_summary=criteria,availability_status='predicted' if calibrated else 'gated',
            missing_dependencies=[] if calibrated else ['held_out_size_calibration'],
            evidence_needed=['Compatible source-bound predictor observations.'],scope=scope,
            predicates=[deepcopy(p)],ranking=dict(capacity=p['capacity'],ties=['world_id_ascending'])))
    result['revision']=definitions['revision']
    result['evidence_label']='Predicted starts and height-specific biome witnesses; scoped evidence accompanies each result.'
    return result

```
## Actual current ProductPillar
```tsx
export function ProductPillar({
  pillarId,
  snapshotId,
  initialRegistry,
  initialSelected,
}: {
  pillarId: PillarId;
  snapshotId: string;
  initialRegistry?: Registry;
  initialSelected?: string;
}) {
  const [registry, setRegistry] = useState<Registry | null>(initialRegistry || null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<string | null>(initialSelected || null);
  const inspector = useRef<HTMLElement>(null);
  const opener = useRef<HTMLButtonElement | null>(null);
  const closeCriteria = () => {setSelected(null); opener.current?.focus();};
  useEffect(() => {
    if (initialRegistry && registry === initialRegistry) return;
    const controller = new AbortController();
    setRegistry(null);setSelected(null);setError('');
    requestJson<Registry>(`/api/catalog/products${snapshotId ? `?snapshot_id=${encodeURIComponent(snapshotId)}` : ''}`, {method: 'GET', timeoutMs: 12000, signal: controller.signal})
      .then(({data}) => {if (!controller.signal.aborted) {
        if (!data.ok || (data.revision !== 'catalog-products-v1' && data.revision !== 'catalog-products-v2') || !Array.isArray(data.products))
          throw new Error('Catalog product definitions are unavailable.');
        setRegistry(data);
      }})
      .catch(e => {if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Catalog unavailable.');});
    return () => controller.abort();
  }, [initialRegistry,snapshotId]);
  useEffect(() => {if (!initialSelected) setSelected(null);}, [pillarId]);
  useEffect(() => {if (selected) inspector.current?.focus();}, [selected]);
  const products = registry?.products.filter(p => p.pillar_id === pillarId) || [];
  const chosen = products.find(p => p.id === selected);
  const categories = [...new Set(products.map(p => p.category))];
  return <main className="max-w-7xl mx-auto w-full p-4 sm:p-6 space-y-6">
    <h2 className="text-xl font-semibold">{PILLARS.find(([id]) => id === pillarId)?.[1]}</h2>
    {pillarId === 'realm' && <p className="text-slate-300">Browse worlds for shared survival play. Qualification requires public observations against the declared Realm blueprint; personal search winners are not automatically certified. Separate 2048, 4096 and 8192 Overworld boards use size-specific requirements and the same 1,250-point budget: 845 OW / 265 luxury / 140 Nether. The Nether square stays 1024 × 1024. Results are predicted at a supported center; an empty list means no retained match.</p>}
    {pillarId === 'presets' && <p className="text-slate-300">Sixteen fixed play-style presets. Open a card to inspect its exact criteria and browse launch results.</p>}
    {pillarId === 'rare' && <p className="text-slate-300">{registry?.revision==='catalog-products-v1' ? 'Legacy Origin-centered research density previews. Choose the current snapshot for the new record products.' : 'Seventeen record categories based on predicted structure counts, proximity, clusters and biome witnesses. Rankings describe this evaluated catalog, which includes selected research controls; these are not global Minecraft records.'}</p>}
    {pillarId === 'personalized' && <p className="text-slate-300">Personalized selection and criteria.</p>}
    {error && <p role="alert" className="text-amber-300">{error}</p>}
    {!registry && !error && <p role="status">Loading catalog definitions…</p>}
    {categories.map(category => <section key={category} className="space-y-3">
      <h3 className="font-semibold text-emerald-300">{category}</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{products.filter(p => p.category === category).map(p =>
        <button key={p.id} type="button" aria-expanded={chosen?.id === p.id} onClick={e => {opener.current = e.currentTarget; setSelected(p.id);}}
          className="text-left rounded-xl border border-slate-700 bg-slate-950 p-4 hover:border-emerald-500 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <span className="block font-semibold">{p.label}</span>
            {p.availability_status === 'predicted' && (
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border border-emerald-600 bg-emerald-950/70 text-emerald-300">
                Launch
              </span>
            )}
            {p.availability_status === 'research' && (
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border border-sky-600 bg-sky-950/70 text-sky-300">
                Research
              </span>
            )}
            {p.availability_status !== 'predicted' && p.availability_status !== 'research' && (
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border border-amber-600/70 bg-amber-950/70 text-amber-300">
                Gated
              </span>
            )}
          </div>
          <span className="block text-xs text-slate-400">{p.criteria_summary}</span>
          <span className={`block text-xs ${p.availability_status === 'predicted' || p.availability_status === 'research' ? 'text-emerald-300' : 'text-amber-300'}`}>
            {p.availability_status === 'predicted' ? 'Browse launch results' : (p.availability_status === 'research' ? 'Browse research preview' : 'Evidence pending · View criteria')}
          </span>
        </button>)}</div>
    </section>)}
    {chosen && <section ref={inspector} tabIndex={-1} aria-label={`${chosen.label} criteria`} onKeyDown={e => {if (e.key === 'Escape') {e.stopPropagation(); closeCriteria();}}}
      className="rounded-xl border border-emerald-700 p-5 bg-slate-950 space-y-3 outline-none focus:ring-2 focus:ring-emerald-500">
      <div className="flex justify-between gap-3"><h3 className="font-bold">{chosen.label}</h3>
        <button type="button" className="text-sm underline" onClick={closeCriteria}>Close criteria</button></div>
      <p>{chosen.criteria_summary}</p>
      {chosen.availability_status !== 'research' && chosen.availability_status !== 'predicted' && <>
        <p className="text-amber-300">Matching results are unavailable until the required evidence is implemented.</p>
        <ul className="list-disc pl-5 text-sm text-slate-300">{chosen.evidence_needed?.map(e => <li key={e}>{e}</li>)}</ul>
        {chosen.missing_dependencies?.length > 0 && (
          <p className="text-xs text-slate-400">Pending: {chosen.missing_dependencies.join(', ').replaceAll('_', ' ')}</p>
        )}
      </>}
      {chosen.availability_status === 'research' && <ResearchList key={chosen.id} product={chosen} snapshotId={snapshotId} />}
      {chosen.availability_status === 'predicted' && <LaunchProductList key={chosen.id} product={chosen} snapshotId={snapshotId} />}
    </section>}
  </main>;
}

```
## Frozen policy source list (products.py presentation is not in it)
```python
def automation_policy_revision():
    import json
    from .registry import REGISTRY_REVISION_V2,CONTRACT_ROOT
    from .products import launch_definitions
    from .product_evaluation import FAMILIES
    import hashlib
    from pathlib import Path
    module_root=Path(__file__).parent
    sources={name:hashlib.sha256((module_root/name).read_bytes()).hexdigest() for name in
             ('product_evaluation.py','realm_evaluation.py','calibration.py','realm_observations.py','models.py','extract.py','summaries.py','retention.py')}
    calibration_path=CONTRACT_ROOT.parent/'v2'/'realm_calibration.json'
    calibration=json.loads(calibration_path.read_text()) if calibration_path.is_file() else None
    return digest(['catalog-automation-v2-r3',sources,calibration,POLICY_REVISION,REGISTRY_REVISION_V2,launch_definitions(),FAMILIES,
        json.loads((CONTRACT_ROOT.parent/'v2'/'realm_scoring.json').read_text()),automation_objectives()])



```
