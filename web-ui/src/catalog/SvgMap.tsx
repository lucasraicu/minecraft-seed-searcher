import { useState, useMemo } from 'react';
import type { BiomeWitnessPoint, BorderSide, AnchorMode } from './types';

interface SvgMapProps {
  bounds: [number, number, number, number]; // [lox, loz, hix, hiz]
  borderSide: BorderSide;
  anchor: [number, number] | string;
  anchorMode?: AnchorMode;
  structures?: Record<string, [number, number][]>;
  biomeWitnesses?: BiomeWitnessPoint[];
  className?: string;
  showCoordinates?: boolean;
}

const FEATURE_COLORS: Record<string, string> = {
  'structure.village': '#f59e0b', // Amber
  'structure.trial_chamber': '#fb923c', // Orange
  'structure.ancient_city': '#06b6d4', // Cyan
  'structure.mansion': '#a855f7', // Purple
  'structure.monument': '#38bdf8', // Sky
  'structure.ruined_portal': '#c084fc', // Light purple
  'structure.desert_pyramid': '#eab308', // Yellow
  'structure.outpost': '#ef4444', // Red
  'structure.swamp_hut': '#84cc16', // Lime
  'structure.shipwreck': '#60a5fa', // Blue
  'structure.jungle_temple': '#10b981', // Emerald
  'structure.mineshaft': '#78716c', // Stone
  'structure.fortress': '#f43f5e', // Rose
  'structure.bastion': '#e11d48', // Dark rose
};

function getFeatureColor(id: string): string {
  if (FEATURE_COLORS[id]) return FEATURE_COLORS[id];
  if (id.startsWith('biome.')) return '#34d399'; // Emerald light for biomes
  return '#94a3b8'; // Slate default
}

function formatFeatureLabel(id: string): string {
  const clean = id.replace(/^(structure|biome)\./, '');
  return clean
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export function SvgMap({
  bounds,
  borderSide,
  anchor,
  anchorMode = 'recommended',
  structures = {},
  biomeWitnesses = [],
  className = '',
  showCoordinates = true,
}: SvgMapProps) {
  const [lox, loz, hix, hiz] = bounds;
  const width = Math.max(1, hix - lox);
  const height = Math.max(1, hiz - loz);

  // 6% margin around border for visual breathing room
  const padX = width * 0.06;
  const padZ = height * 0.06;
  const vbX = lox - padX;
  const vbZ = loz - padZ;
  const vbW = width + padX * 2;
  const vbH = height + padZ * 2;

  // Scale-dependent marker sizes
  const markerRadius = Math.max(12, Math.round(width / 160));
  const strokeW = Math.max(2, Math.round(width / 600));

  const [activeTooltip, setActiveTooltip] = useState<{
    label: string;
    x: number;
    z: number;
    extra?: string;
  } | null>(null);

  const anchorCoords: [number, number] | null = useMemo(() => {
    if (Array.isArray(anchor) && anchor.length === 2 && typeof anchor[0] === 'number') {
      return [anchor[0], anchor[1]];
    }
    if (anchorMode === 'origin') {
      return [0, 0];
    }
    return null;
  }, [anchor, anchorMode]);

  return (
    <div className={`relative flex flex-col bg-slate-950 rounded-lg border border-slate-800 overflow-hidden ${className}`}>
      {/* Header bar with coordinates range & bounds info */}
      <div className="flex flex-wrap items-center justify-between px-3 py-2 bg-slate-900 border-b border-slate-800 text-xs text-slate-300 gap-2">
        <div className="flex items-center space-x-2">
          <span className="font-semibold text-emerald-400">Geometry Map</span>
          <span className="text-slate-500">|</span>
          <span>Side: <strong className="text-slate-100">{borderSide}</strong> blocks</span>
          <span className="text-slate-500">|</span>
          <span>Mode: <strong className="text-slate-100">{anchorMode}</strong></span>
        </div>
        {showCoordinates && (
          <div className="font-mono text-slate-400 text-[11px]">
            X: [{lox}, {hix}) &bull; Z: [{loz}, {hiz})
          </div>
        )}
      </div>

      {/* Main SVG canvas */}
      <div className="relative flex-1 min-h-[340px] max-h-[500px] flex items-center justify-center p-2">
        <svg
          viewBox={`${vbX} ${vbZ} ${vbW} ${vbH}`}
          className="w-full h-full max-h-[460px] select-none"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label={`Minecraft layout geometry map showing ${borderSide}x${borderSide} border`}
        >
          <defs>
            {/* Pattern for background coordinate grid */}
            <pattern
              id="grid-pattern"
              width={borderSide / 8}
              height={borderSide / 8}
              patternUnits="userSpaceOnUse"
            >
              <path
                d={`M ${borderSide / 8} 0 L 0 0 0 ${borderSide / 8}`}
                fill="none"
                stroke="#1e293b"
                strokeWidth={strokeW * 0.5}
              />
            </pattern>
          </defs>

          {/* Background rect with subtle grid */}
          <rect
            x={vbX}
            y={vbZ}
            width={vbW}
            height={vbH}
            fill="#090d16"
          />
          <rect
            x={lox}
            y={loz}
            width={width}
            height={height}
            fill="url(#grid-pattern)"
          />

          {/* Border bounds boundary */}
          <rect
            x={lox}
            y={loz}
            width={width}
            height={height}
            fill="none"
            stroke="#10b981"
            strokeWidth={strokeW}
            strokeDasharray={`${strokeW * 4} ${strokeW * 2}`}
          />

          {/* Origin axes (X=0 and Z=0 if inside bounds) */}
          {0 >= lox && 0 <= hix && (
            <line
              x1={0}
              y1={loz}
              x2={0}
              y2={hiz}
              stroke="#334155"
              strokeWidth={strokeW * 0.75}
              strokeDasharray={`${strokeW * 2} ${strokeW * 2}`}
            />
          )}
          {0 >= loz && 0 <= hiz && (
            <line
              x1={lox}
              y1={0}
              x2={hix}
              y2={0}
              stroke="#334155"
              strokeWidth={strokeW * 0.75}
              strokeDasharray={`${strokeW * 2} ${strokeW * 2}`}
            />
          )}

          {/* Biome witnesses rendered as subtle circles with center dot */}
          {biomeWitnesses.map((bw, idx) => {
            const color = getFeatureColor(bw.feature);
            return (
              <g
                key={`bw-${idx}`}
                className="cursor-pointer transition-opacity hover:opacity-100"
                opacity={0.85}
                onMouseEnter={() =>
                  setActiveTooltip({
                    label: formatFeatureLabel(bw.feature),
                    x: bw.x,
                    z: bw.z,
                    extra: `Biome witness (dist²: ${bw.distance_squared})`,
                  })
                }
                onMouseLeave={() => setActiveTooltip(null)}
              >
                <circle
                  cx={bw.x}
                  cy={bw.z}
                  r={markerRadius * 1.5}
                  fill={color}
                  fillOpacity={0.15}
                  stroke={color}
                  strokeWidth={strokeW * 0.75}
                />
                <circle
                  cx={bw.x}
                  cy={bw.z}
                  r={markerRadius * 0.4}
                  fill={color}
                />
              </g>
            );
          })}

          {/* Structure starts points */}
          {Object.entries(structures).flatMap(([featId, coords]) =>
            coords.map(([sx, sz], sidx) => {
              const color = getFeatureColor(featId);
              return (
                <g
                  key={`st-${featId}-${sidx}`}
                  className="cursor-pointer transition-transform hover:scale-125"
                  onMouseEnter={() =>
                    setActiveTooltip({
                      label: formatFeatureLabel(featId),
                      x: sx,
                      z: sz,
                      extra: 'Structure start',
                    })
                  }
                  onMouseLeave={() => setActiveTooltip(null)}
                >
                  <circle
                    cx={sx}
                    cy={sz}
                    r={markerRadius * 0.9}
                    fill={color}
                    stroke="#0f172a"
                    strokeWidth={strokeW * 0.8}
                  />
                  <circle
                    cx={sx}
                    cy={sz}
                    r={markerRadius * 0.3}
                    fill="#ffffff"
                  />
                </g>
              );
            })
          )}

          {/* Anchor location marker */}
          {anchorCoords && (
            <g
              className="cursor-pointer"
              onMouseEnter={() =>
                setActiveTooltip({
                  label: `Anchor (${anchorMode})`,
                  x: anchorCoords[0],
                  z: anchorCoords[1],
                  extra: 'Evaluation anchor point',
                })
              }
              onMouseLeave={() => setActiveTooltip(null)}
            >
              {/* Outer pulse ring */}
              <circle
                cx={anchorCoords[0]}
                cy={anchorCoords[1]}
                r={markerRadius * 2.2}
                fill="none"
                stroke="#34d399"
                strokeWidth={strokeW}
                opacity={0.4}
              />
              {/* Diamond marker */}
              <polygon
                points={`
                  ${anchorCoords[0]},${anchorCoords[1] - markerRadius * 1.4}
                  ${anchorCoords[0] + markerRadius * 1.4},${anchorCoords[1]}
                  ${anchorCoords[0]},${anchorCoords[1] + markerRadius * 1.4}
                  ${anchorCoords[0] - markerRadius * 1.4},${anchorCoords[1]}
                `}
                fill="#10b981"
                stroke="#ffffff"
                strokeWidth={strokeW}
              />
            </g>
          )}

          {/* World Origin (0,0) dot if distinct from anchor */}
          {(!anchorCoords || anchorCoords[0] !== 0 || anchorCoords[1] !== 0) &&
            0 >= lox && 0 <= hix && 0 >= loz && 0 <= hiz && (
              <g
                className="cursor-pointer"
                onMouseEnter={() =>
                  setActiveTooltip({
                    label: 'Origin (0, 0)',
                    x: 0,
                    z: 0,
                    extra: 'World center coordinates',
                  })
                }
                onMouseLeave={() => setActiveTooltip(null)}
              >
                <circle cx={0} cy={0} r={markerRadius * 0.5} fill="#64748b" stroke="#0f172a" strokeWidth={strokeW * 0.5} />
              </g>
            )}
        </svg>

        {/* Hover Floating Tooltip */}
        {activeTooltip && (
          <div className="absolute top-4 right-4 pointer-events-none bg-slate-900/95 backdrop-blur border border-emerald-500/50 shadow-xl rounded-md px-3 py-2 text-xs z-20">
            <div className="font-semibold text-emerald-400">{activeTooltip.label}</div>
            <div className="font-mono text-slate-200 mt-0.5">
              X: {activeTooltip.x}, Z: {activeTooltip.z}
            </div>
            {activeTooltip.extra && (
              <div className="text-[11px] text-slate-400 mt-0.5">{activeTooltip.extra}</div>
            )}
          </div>
        )}
      </div>

      {/* Legend footer */}
      <div className="flex flex-wrap items-center gap-3 px-3 py-2 bg-slate-900/80 border-t border-slate-800 text-[11px] text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 bg-emerald-500 rotate-45 border border-white inline-block"></span>
          <span>Anchor</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full border border-emerald-400/80 border-dashed inline-block"></span>
          <span>Border ({borderSide}m)</span>
        </div>
        {Object.keys(structures).length > 0 &&
          Object.keys(structures).slice(0, 5).map(feat => (
            <div key={feat} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full inline-block"
                style={{ backgroundColor: getFeatureColor(feat) }}
              ></span>
              <span>{formatFeatureLabel(feat)}</span>
            </div>
          ))}
        {biomeWitnesses.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/40 border border-emerald-400 inline-block"></span>
            <span>Biome Witnesses ({biomeWitnesses.length})</span>
          </div>
        )}
      </div>
    </div>
  );
}
