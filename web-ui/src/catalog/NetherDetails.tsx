import type {BiomeWitnessPoint} from './types';
import {featureLabel} from './constants';

export function NetherDetails({structures,bounds,witnesses}:{structures:Record<string,[number,number][]>;bounds:[number,number,number,number];witnesses:BiomeWitnessPoint[]}){
  const [x0,z0,x1,z1]=bounds,ax=x0+512,az=z0+512;
  return <details className="my-3 rounded border border-amber-900 p-3 text-xs space-y-3">
    <summary className="cursor-pointer font-semibold text-amber-200">Nether observations · fixed 1024 × 1024 blocks</summary>
    <p>Projected reference X={ax}, Z={az}. These are Nether block coordinates, calculated by flooring the Overworld anchor divided by 8. A generated portal location has not been established.</p>
    <p>Bounds: X [{x0}, {x1}), Z [{z0}, {z1}); upper edges excluded.</p>
    <svg role="img" aria-label="Predicted Nether structure starts; north up, east right" viewBox={`${x0-24} ${z0-24} 1072 1072`} className="w-full max-w-sm bg-slate-900">
      <rect x={x0} y={z0} width={1024} height={1024} fill="none" stroke="#fbbf24" strokeWidth={3}/>
      <path d={`M ${ax-12} ${az} H ${ax+12} M ${ax} ${az-12} V ${az+12}`} stroke="white" strokeWidth={3}/>
      {Object.entries(structures).flatMap(([feature,points])=>points.map(([x,z])=><circle key={`${feature}:${x}:${z}`} cx={x} cy={z} r={6} fill={feature==='structure.fortress'?'#fb923c':'#a78bfa'}><title>{`${featureLabel(feature)} predicted start: X=${x}, Z=${z}`}</title></circle>))}
    </svg>
    {Object.entries(structures).map(([feature,points])=><section key={feature}><h4 className="font-semibold">{featureLabel(feature)} · {points.length} saved predicted starts</h4><p className="select-all break-words">{points.map(([x,z])=>`(${x}, ${z})`).join(' · ')||'No saved positive evidence.'}</p></section>)}
    <h4 className="font-semibold">Saved Nether biome witnesses</h4>
    <ul>{witnesses.map(w=><li key={`${w.feature}:${w.x}:${w.y}:${w.z}`}>{featureLabel(w.feature)}: X={w.x}, Y={w.y}, Z={w.z}; horizontal distance {Math.sqrt(w.distance_squared).toFixed(1)} Nether blocks.</li>)}</ul>
    {!witnesses.length&&<p>No saved biome witnesses. Missing samples do not establish absence.</p>}
  </details>;
}
