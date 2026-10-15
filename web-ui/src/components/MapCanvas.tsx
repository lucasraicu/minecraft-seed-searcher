import { playableBounds } from '../utils/geometry';
import type { SearchProfileName } from '../constants/baselinePolicy';
import { spawnEvidenceLabel } from '../utils/spawn';
import React, { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import type {
  SeedCandidate,
  StructureMarker,
  Dimension,
  RavineMarker,
  CaveClusterMarker,
  MapLabelMode,
  MapElevationFilter,
} from '../types';

interface MapCanvasProps {
  profile: SearchProfileName;
  candidate: SeedCandidate | null;
  dimension: Dimension;
  onDimensionChange: (dim: Dimension) => void;
  showBorders: boolean;
  onToggleBorders?: () => void;
  showBiomes: boolean;
  onToggleBiomes?: () => void;
  showGrid: boolean;
  onToggleGrid?: () => void;
  showRavines?: boolean;
  onToggleRavines?: () => void;
  showCaves?: boolean;
  onToggleCaves?: () => void;
}

const isUndergroundStructure = (type: string): boolean =>
  [
    'ancient_city',
    'trial_chamber',
    'stronghold',
    'mineshaft',
    'lush_caves',
    'dripstone_caves',
    'deep_dark',
  ].includes(type);

const isApexLandmark = (type: string): boolean =>
  ['stronghold', 'mansion', 'ancient_city', 'monument', 'fortress', 'bastion'].includes(type);

const getStructureAbbr = (type: string, name?: string): string => {
  if (type === 'stronghold') return 'SH';
  if (type === 'mansion') return 'MAN';
  if (type === 'ancient_city') return 'ANC';
  if (type === 'trial_chamber') return 'TRI';
  if (type === 'village') return 'VIL';
  if (type === 'monument') return 'MON';
  if (type === 'shipwreck') return 'SHP';
  if (type === 'pyramid' || type === 'desert_pyramid') return 'PYR';
  if (type === 'jungle_temple') return 'JNG';
  if (type === 'outpost') return 'OUT';
  if (type === 'mineshaft') return 'MSH';
  if (type === 'lush_caves') return 'LSH';
  if (type === 'dripstone_caves') return 'DRP';
  if (type === 'deep_dark') return 'DRK';
  if (type === 'fortress') return 'FRT';
  if (type === 'bastion') return 'BST';
  if (type === 'ruined_portal') return 'PRT';
  return (name || type).slice(0, 3).toUpperCase();
};

interface BiomeGridData {
  seed: string;
  dimension: string;
  bounds: { x0: number; z0: number; nx: number; nz: number; step: number };
  grid: number[][];
  approx_height: number[][] | null;
  center: [number, number];
  names: Record<string, string>;
}

const BIOME_COLORS: Record<string, string> = {
  // Oceans
  ocean: '#1e40af',
  deep_ocean: '#172554',
  warm_ocean: '#0284c7',
  deep_warm_ocean: '#0369a1',
  lukewarm_ocean: '#0ea5e9',
  deep_lukewarm_ocean: '#0284c7',
  cold_ocean: '#3b82f6',
  deep_cold_ocean: '#1d4ed8',
  frozen_ocean: '#93c5fd',
  deep_frozen_ocean: '#60a5fa',

  // Rivers & Shores
  river: '#2563eb',
  frozen_river: '#7dd3fc',
  beach: '#fef08a',
  snowy_beach: '#e2e8f0',
  stony_shore: '#94a3b8',

  // Plains & Meadows
  plains: '#84cc16',
  sunflower_plains: '#a3e635',
  snowy_plains: '#f8fafc',
  ice_spikes: '#e0f2fe',
  meadow: '#4ade80',
  cherry_grove: '#f472b6',

  // Forests
  forest: '#15803d',
  flower_forest: '#22c55e',
  birch_forest: '#16a34a',
  old_growth_birch_forest: '#15803d',
  dark_forest: '#14532d',
  pale_garden: '#64748b',

  // Taigas
  taiga: '#047857',
  snowy_taiga: '#0f766e',
  old_growth_pine_taiga: '#065f46',
  old_growth_spruce_taiga: '#064e3b',

  // Jungles
  jungle: '#16a34a',
  sparse_jungle: '#65a30d',
  bamboo_jungle: '#84cc16',

  // Savannas & Deserts
  savanna: '#ca8a04',
  savanna_plateau: '#a16207',
  windswept_savanna: '#b45309',
  desert: '#d97706',
  badlands: '#ea580c',
  wooded_badlands: '#c2410c',
  eroded_badlands: '#9a3412',

  // Swamps
  swamp: '#0d9488',
  mangrove_swamp: '#115e59',

  // Mountains & Peaks
  jagged_peaks: '#cbd5e1',
  frozen_peaks: '#e2e8f0',
  stony_peaks: '#94a3b8',
  snowy_slopes: '#f1f5f9',
  grove: '#0284c7',
  windswept_hills: '#64748b',
  windswept_gravelly_hills: '#475569',
  windswept_forest: '#334155',

  // Caves & Subterranean
  dripstone_caves: '#78350f',
  lush_caves: '#059669',
  deep_dark: '#030712',

  // Nether
  nether_wastes: '#7f1d1d',
  crimson_forest: '#991b1b',
  warped_forest: '#0f766e',
  soul_sand_valley: '#451a03',
  basalt_deltas: '#334155',
};

export const MapCanvas: React.FC<MapCanvasProps> = ({
  candidate,
  profile,
  dimension,
  onDimensionChange,
  showBorders,
  onToggleBorders,
  showBiomes,
  onToggleBiomes,
  showGrid,
  onToggleGrid,
  showRavines = true,
  onToggleRavines,
  showCaves = true,
  onToggleCaves,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Pan & Zoom state
  const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState<number>(0.35); // 1 pixel = 1/zoom blocks
  const zoomRef = useRef<number>(zoom);
  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const cursorWorldRef = useRef<{ x: number; z: number }>({ x: 0, z: 0 });
  const cursorCoordXRef = useRef<HTMLSpanElement | null>(null);
  const cursorCoordZRef = useRef<HTMLSpanElement | null>(null);
  const cursorCoordDistRef = useRef<HTMLSpanElement | null>(null);
  const cursorCoordBiomeRef = useRef<HTMLSpanElement | null>(null);

  const boundsForView = playableBounds(candidate, dimension, profile);
  const gridCenterX = (boundsForView[0] + boundsForView[2]) / 2;
  const gridCenterZ = (boundsForView[1] + boundsForView[3]) / 2;
  const gridSide = boundsForView[2] - boundsForView[0];

  // Biome Grid State & Fetching
  const [biomeGrid, setBiomeGrid] = useState<BiomeGridData | null>(null);
  const [isLoadingBiomeGrid, setIsLoadingBiomeGrid] = useState<boolean>(false);
  const biomeGridCacheRef = useRef<Map<string, BiomeGridData>>(new Map());
  const offscreenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const offscreenGridKeyRef = useRef<string>('');

  useEffect(() => {
    if (!candidate?.seed || !showBiomes) return;
    const cacheKey = `${candidate.seed}_${dimension}_${gridCenterX}_${gridCenterZ}_${gridSide}`;
    const cached = biomeGridCacheRef.current.get(cacheKey);
    if (cached) {
      setBiomeGrid(cached);
      return;
    }
    let isCancelled = false;
    setBiomeGrid(null);
    setIsLoadingBiomeGrid(true);
    fetch(`/api/candidate/biome-grid?seed=${encodeURIComponent(candidate.seed)}&dimension=${dimension}&centerX=${gridCenterX}&centerZ=${gridCenterZ}&side=${gridSide}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!isCancelled && data && data.ok) {
          if (biomeGridCacheRef.current.size >= 20) biomeGridCacheRef.current.delete(biomeGridCacheRef.current.keys().next().value!);
          biomeGridCacheRef.current.set(cacheKey, data);
          setBiomeGrid(data);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!isCancelled) setIsLoadingBiomeGrid(false);
      });
    return () => {
      isCancelled = true;
    };
  }, [candidate?.seed, dimension, showBiomes, gridCenterX, gridCenterZ, gridSide]);

  const [hoveredStructure, setHoveredStructure] = useState<StructureMarker | null>(null);
  const [hoveredRavine, setHoveredRavine] = useState<RavineMarker | null>(null);
  const [hoveredCave, setHoveredCave] = useState<CaveClusterMarker | null>(null);
  const [pinnedFeature, setPinnedFeature] = useState<
    StructureMarker | RavineMarker | CaveClusterMarker | null
  >(null);
  const [showDistanceRings, setShowDistanceRings] = useState<boolean>(true);

  // Hover entity ID tracking for RAF throttling
  const hoverRafRef = useRef<number | null>(null);
  const latestMousePosRef = useRef<{ clientX: number; clientY: number } | null>(null);
  const hoveredStructureIdRef = useRef<string | null>(null);
  const hoveredCaveIdRef = useRef<string | null>(null);
  const hoveredRavineIdRef = useRef<string | null>(null);

  useEffect(() => {
    hoveredStructureIdRef.current = hoveredStructure?.id ?? null;
  }, [hoveredStructure]);

  useEffect(() => {
    hoveredCaveIdRef.current = hoveredCave?.id ?? null;
  }, [hoveredCave]);

  useEffect(() => {
    hoveredRavineIdRef.current = hoveredRavine?.id ?? null;
  }, [hoveredRavine]);

  useEffect(() => {
    return () => {
      if (hoverRafRef.current != null) {
        cancelAnimationFrame(hoverRafRef.current);
      }
    };
  }, []);

  // Smart Level-of-Detail & Layer Filters
  const [labelMode, setLabelMode] = useState<MapLabelMode>('smart');
  const [elevationFilter, setElevationFilter] = useState<MapElevationFilter>('all');

  // Memoized ravines and subterranean cave clusters (render nothing if absent)
  const ravinesList: RavineMarker[] = useMemo(() => {
    return candidate?.ravines ?? [];
  }, [candidate]);

  const cavesList: CaveClusterMarker[] = useMemo(() => {
    return candidate?.caveClusters ?? [];
  }, [candidate]);

  const mouseDownPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  const jumpToLocation = useCallback(
    (
      targetX: number,
      targetZ: number,
      feature?: StructureMarker | CaveClusterMarker | RavineMarker | null
    ) => {
      const targetZoom = 0.85;
      setZoom(targetZoom);
      setOffset({
        x: -targetX * targetZoom,
        y: -targetZ * targetZoom,
      });
      if (feature) {
        setPinnedFeature(feature);
        if ('yaw' in feature) {
          setHoveredRavine(feature as RavineMarker);
          setHoveredCave(null);
          setHoveredStructure(null);
        } else if ('notes' in feature && !('viable' in feature)) {
          setHoveredCave(feature as CaveClusterMarker);
          setHoveredRavine(null);
          setHoveredStructure(null);
        } else {
          setHoveredStructure(feature as StructureMarker);
          setHoveredRavine(null);
          setHoveredCave(null);
        }
      }
    },
    []
  );

  // Quick Jump targets
  const quickJumpTargets = useMemo(() => {
    if (!candidate) return [];
    if (dimension === 'overworld') {
      const targets: { label: string; icon: string; x: number; z: number; y?: number | null; feature: any }[] =
        [];
      const lush = cavesList.find((c) => c.type === 'lush_caves');
      if (lush)
        targets.push({ label: 'Lush Caves', icon: '🌿', x: lush.x, z: lush.z, y: lush.y, feature: lush });

      const mega = ravinesList.find((r) => r.giant);
      if (mega)
        targets.push({ label: 'Mega Ravine', icon: '🌋', x: mega.x, z: mega.z, y: mega.y, feature: mega });

      const sh = candidate.structures.find(
        (s) => s.type === 'stronghold' && s.dimension === 'overworld'
      );
      if (sh)
        targets.push({ label: 'Stronghold marker', icon: '🏰', x: sh.x, z: sh.z, y: sh.y, feature: sh });

      const mansion = candidate.structures.find(
        (s) => s.type === 'mansion' && s.dimension === 'overworld'
      );
      if (mansion)
        targets.push({ label: 'Mansion', icon: '🏛️', x: mansion.x, z: mansion.z, y: mansion.y, feature: mansion });

      const ac = candidate.structures.find(
        (s) => s.type === 'ancient_city' && s.dimension === 'overworld'
      );
      if (ac)
        targets.push({ label: 'Ancient City', icon: '🏙️', x: ac.x, z: ac.z, y: ac.y, feature: ac });

      return targets;
    } else {
      const targets: { label: string; icon: string; x: number; z: number; y?: number | null; feature: any }[] =
        [];
      const fort = candidate.structures.find(
        (s) => s.type === 'fortress' && s.dimension === 'nether'
      );
      if (fort)
        targets.push({ label: 'Nether Fortress', icon: '🏯', x: fort.x, z: fort.z, y: fort.y, feature: fort });

      const bast = candidate.structures.find(
        (s) => s.type === 'bastion' && s.dimension === 'nether'
      );
      if (bast)
        targets.push({ label: 'Bastion Remnant', icon: '🐖', x: bast.x, z: bast.z, y: bast.y, feature: bast });

      return targets;
    }
  }, [candidate, dimension, cavesList, ravinesList]);

  // Use an evidence-backed anchor, the policy evaluation center, or world
  // origin as a view position. The origin is not treated as a stronghold.
  const candidateId = candidate?.id;
  const anchorX = candidate?.evaluationCenter?.[0] ?? candidate?.strongholdAnchor?.[0] ?? 0;
  const anchorZ = candidate?.evaluationCenter?.[1] ?? candidate?.strongholdAnchor?.[1] ?? 0;
  useEffect(() => {
    const scale = dimension === 'overworld' ? 1 : 1 / 8;
    const frame = requestAnimationFrame(() => {
      setOffset({ x: -(anchorX * scale) * zoomRef.current, y: -(anchorZ * scale) * zoomRef.current });
    });
    return () => cancelAnimationFrame(frame);
  }, [candidateId, anchorX, anchorZ, dimension]);

  // Convert screen coordinates to Minecraft world coordinates
  const screenToWorld = useCallback(
    (screenX: number, screenY: number, width: number, height: number) => {
      const centerX = width / 2;
      const centerY = height / 2;
      const worldX = Math.round((screenX - centerX - offset.x) / zoom);
      const worldZ = Math.round((screenY - centerY - offset.y) / zoom);
      return { x: worldX, z: worldZ };
    },
    [offset, zoom]
  );

  // Convert Minecraft world coordinates to screen coordinates
  const worldToScreen = useCallback(
    (worldX: number, worldZ: number, width: number, height: number) => {
      const centerX = width / 2;
      const centerY = height / 2;
      const screenX = centerX + offset.x + worldX * zoom;
      const screenY = centerY + offset.y + worldZ * zoom;
      return { x: screenX, y: screenY };
    },
    [offset, zoom]
  );

  // Main Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // High-DPI handling
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    ctx.clearRect(0, 0, width, height);

    // 1. Background fill
    if (dimension === 'overworld') {
      ctx.fillStyle = '#081226'; // Deep Ocean sea floor
    } else {
      ctx.fillStyle = '#1c0808'; // Nether deep red
    }
    ctx.fillRect(0, 0, width, height);

    const originScreen = worldToScreen(0, 0, width, height);

    // 2. Concentric distance rings from the world origin (blocks)
    if (showDistanceRings) {
      ctx.save();
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.12)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);

      // 500m ring
      ctx.beginPath();
      ctx.arc(originScreen.x, originScreen.y, 500 * zoom, 0, Math.PI * 2);
      ctx.stroke();

      // 1000m ring
      ctx.beginPath();
      ctx.arc(originScreen.x, originScreen.y, 1000 * zoom, 0, Math.PI * 2);
      ctx.stroke();

      ctx.fillStyle = 'rgba(148, 163, 184, 0.35)';
      ctx.font = 'bold 9px monospace';
      ctx.fillText('500 blocks from origin', originScreen.x + 500 * zoom + 5, originScreen.y - 4);
      ctx.fillText('1000 blocks from origin', originScreen.x + 1000 * zoom + 5, originScreen.y - 4);
      ctx.restore();
    }

    // 3. Sampled predicted Bedrock biome map (no block or height verification)
    if (showBiomes && candidate) {
      if (biomeGrid && String(biomeGrid.seed) === String(candidate.seed) && biomeGrid.dimension === dimension && biomeGrid.center[0] === gridCenterX && biomeGrid.center[1] === gridCenterZ) {
        const { bounds, grid, approx_height, names } = biomeGrid;
        const { x0, z0, nx, nz, step } = bounds;

        const gridKey = `${candidate.seed}_${dimension}_${gridCenterX}_${gridCenterZ}_${nx}_${nz}`;
        if (offscreenGridKeyRef.current !== gridKey || !offscreenCanvasRef.current) {
          let offscreen = offscreenCanvasRef.current;
          if (!offscreen) {
            offscreen = document.createElement('canvas');
            offscreenCanvasRef.current = offscreen;
          }
          offscreen.width = nx;
          offscreen.height = nz;
          const offCtx = offscreen.getContext('2d');
          if (offCtx) {
            for (let r = 0; r < nz; r++) {
              for (let c = 0; c < nx; c++) {
                const bId = grid[r][c];
                const bName = names[String(bId)] || 'unknown';
                const h = approx_height?.[r]?.[c];
                const baseColor = BIOME_COLORS[bName] || '#334155';
                offCtx.fillStyle = baseColor;
                offCtx.fillRect(c, r, 1, 1);

                if (h != null && h < 63) {
                  const depth = Math.min(0.35, Math.max(0.05, (63 - h) / 50));
                  offCtx.fillStyle = `rgba(15, 23, 42, ${depth})`;
                  offCtx.fillRect(c, r, 1, 1);
                } else if (h != null && h > 100) {
                  const peak = Math.min(0.25, (h - 100) / 80);
                  offCtx.fillStyle = `rgba(255, 255, 255, ${peak})`;
                  offCtx.fillRect(c, r, 1, 1);
                }
              }
            }
          }
          offscreenGridKeyRef.current = gridKey;
        }

        const p1 = worldToScreen(x0, z0, width, height);
        const p2 = worldToScreen(x0 + nx * step, z0 + nz * step, width, height);
        const drawW = p2.x - p1.x;
        const drawH = p2.y - p1.y;

        if (offscreenCanvasRef.current && p1.x + drawW >= 0 && p1.x <= width && p1.y + drawH >= 0 && p1.y <= height) {
          ctx.save();
          ctx.imageSmoothingEnabled = false;
          ctx.drawImage(offscreenCanvasRef.current, Math.floor(p1.x), Math.floor(p1.y), Math.ceil(drawW), Math.ceil(drawH));
          ctx.restore();
        }
      } else if (candidate.biomeSamples && candidate.biomeSamples.length > 0) {
        // Fallback: render discrete sampled biome lattice points
        ctx.save();
        for (const sample of candidate.biomeSamples) {
          const sx = sample.x ?? sample.coordinate?.[0] ?? 0;
          const sz = sample.z ?? sample.coordinate?.[2] ?? 0;
          const p = worldToScreen(sx, sz, width, height);
          const color = BIOME_COLORS[sample.biome] || '#475569';
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(p.x, p.y, Math.max(2, 16 * zoom), 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      }
    }

    // 4. Subtle Coordinate Grid
    if (showGrid) {
      ctx.save();
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.08)';
      ctx.lineWidth = 1;
      ctx.fillStyle = 'rgba(148, 163, 184, 0.35)';
      ctx.font = '9px monospace';

      const gridStep = zoom < 0.2 ? 1000 : zoom < 0.8 ? 500 : 200;
      const bounds = {
        min: screenToWorld(0, 0, width, height),
        max: screenToWorld(width, height, width, height),
      };

      const startX = Math.floor(bounds.min.x / gridStep) * gridStep;
      const endX = Math.ceil(bounds.max.x / gridStep) * gridStep;
      const startZ = Math.floor(bounds.min.z / gridStep) * gridStep;
      const endZ = Math.ceil(bounds.max.z / gridStep) * gridStep;

      // Vertical lines
      for (let gx = startX; gx <= endX; gx += gridStep) {
        const sx = worldToScreen(gx, 0, width, height).x;
        ctx.beginPath();
        ctx.moveTo(sx, 0);
        ctx.lineTo(sx, height);
        ctx.stroke();
        ctx.fillText(`${gx}`, sx + 4, 14);
      }

      // Horizontal lines
      for (let gz = startZ; gz <= endZ; gz += gridStep) {
        const sy = worldToScreen(0, gz, width, height).y;
        ctx.beginPath();
        ctx.moveTo(0, sy);
        ctx.lineTo(width, sy);
        ctx.stroke();
        ctx.fillText(`${gz}`, 6, sy - 4);
      }
      ctx.restore();
    }

    // Playable bounds follow the chosen density center, with exact Nether scaling.
    if (showBorders) {
      const bounds = playableBounds(candidate, dimension, profile);
      const topLeft = worldToScreen(bounds[0], bounds[1], width, height);
      const bottomRight = worldToScreen(bounds[2], bounds[3], width, height);
      ctx.save();
      ctx.strokeStyle = dimension === 'overworld' ? 'rgba(16, 185, 129, 0.85)' : 'rgba(239, 68, 68, 0.85)';
      ctx.fillStyle = dimension === 'overworld' ? '#10b981' : '#ef4444';
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 6]);
      ctx.strokeRect(topLeft.x, topLeft.y, bottomRight.x - topLeft.x, bottomRight.y - topLeft.y);
      ctx.font = 'bold 10px monospace';
      ctx.fillText(`${dimension.toUpperCase()} ${bounds[2] - bounds[0]} × ${bounds[3] - bounds[1]} · (${(bounds[0]+bounds[2])/2}, ${(bounds[1]+bounds[3])/2})`, topLeft.x + 8, topLeft.y + 18);
      ctx.restore();
    }

    // 6. World Origin (0, 0) Marker
    ctx.save();
    ctx.fillStyle = '#f8fafc';
    ctx.beginPath();
    ctx.arc(originScreen.x, originScreen.y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(originScreen.x, originScreen.y, 10, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = '#94a3b8';
    ctx.font = 'bold 11px monospace';
    ctx.fillText('Origin (0,0)', originScreen.x + 14, originScreen.y + 4);
    ctx.restore();

    if (candidate?.evaluationCenter) {
      const scale = dimension === 'nether' ? 1 / 8 : 1;
      const center = candidate.evaluationCenter;
      const hub = worldToScreen(center[0] * scale, center[1] * scale, width, height);
      ctx.save();
      ctx.strokeStyle = '#fbbf24'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(hub.x, hub.y, 7, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = '#fbbf24'; ctx.font = 'bold 11px monospace';
      ctx.fillText('Realm center', hub.x + 14, hub.y + 19);
      ctx.restore();
    }

    // 7. Spawn Point Marker & Vector
    if (candidate?.spawnPoint && dimension === 'overworld') {
      const sp = candidate.spawnPoint;
      const spawnScreen = worldToScreen(sp[0], sp[1], width, height);
      const spawnDist = candidate.spawnDistance;

      ctx.save();
      // Distance is measured from the evaluation hub, which may differ on archived runs.
      ctx.strokeStyle = 'rgba(234, 179, 8, 0.75)';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      const hub = candidate.evaluationCenter ?? [0, 0];
      const hubScreen = worldToScreen(hub[0], hub[1], width, height);
      ctx.moveTo(hubScreen.x, hubScreen.y);
      ctx.lineTo(spawnScreen.x, spawnScreen.y);
      ctx.stroke();

      // Golden compass pin
      ctx.fillStyle = '#eab308';
      ctx.shadowColor = '#eab308';
      ctx.shadowBlur = 14;
      ctx.beginPath();
      ctx.arc(spawnScreen.x, spawnScreen.y, 10, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.shadowBlur = 0;
      ctx.fillStyle = '#fef08a';
      ctx.font = 'bold 11px system-ui';
      ctx.fillText(
        `🧭 ${spawnEvidenceLabel(candidate)} (${sp[0]}, ${sp[1]})${spawnDist == null ? '' : ` • ${spawnDist} ${candidate.spawnDistanceUnits ?? 'blocks'}`}`,
        spawnScreen.x + 14,
        spawnScreen.y + 4
      );
      ctx.restore();
    }

    // 7.5. Ravines & Chasms (Overworld)
    if (showRavines && dimension === 'overworld' && ravinesList.length > 0) {
      ctx.save();
      if (elevationFilter === 'surface') {
        ctx.globalAlpha = 0.25; // dimmed if surface-only view
      }

      ravinesList.forEach((ravine) => {
        const halfLen = (ravine.length || 100) / 2;
        const cosA = Math.cos(ravine.yaw);
        const sinA = Math.sin(ravine.yaw);

        // Generate craggy multi-segment jagged path
        const numSegs = 4;
        const perpCos = -sinA;
        const perpSin = cosA;
        const pts: { x: number; y: number }[] = [];

        for (let i = 0; i <= numSegs; i++) {
          const t = i / numSegs;
          const baseWX = (ravine.x - cosA * halfLen) + t * (cosA * ravine.length);
          const baseWZ = (ravine.z - sinA * halfLen) + t * (sinA * ravine.length);
          let perpOffset = 0;
          if (i > 0 && i < numSegs) {
            const hashVal = Math.sin(ravine.x * 12.9898 + ravine.z * 78.233 + i * 43.123);
            perpOffset = (hashVal * 0.5) * (ravine.thick || 3.5);
          }
          const wx = baseWX + perpCos * perpOffset;
          const wz = baseWZ + perpSin * perpOffset;
          pts.push(worldToScreen(wx, wz, width, height));
        }

        const mid = worldToScreen(ravine.x, ravine.z, width, height);

        // Viewport culling
        const minX = Math.min(...pts.map((p) => p.x));
        const maxX = Math.max(...pts.map((p) => p.x));
        const minY = Math.min(...pts.map((p) => p.y));
        const maxY = Math.max(...pts.map((p) => p.y));
        if (minX > width + 70 || maxX < -70 || minY > height + 70 || maxY < -70) {
          return;
        }

        const isHovered =
          hoveredRavine?.id === ravine.id || pinnedFeature?.id === ravine.id;
        const fissureWidth = Math.max(isHovered ? 6.5 : 4.0, (ravine.thick || 3.5) * zoom * 2.0);

        // 1. High-contrast jagged outer rock cliff rim
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
        ctx.strokeStyle = isHovered ? '#ffffff' : ravine.giant ? '#fb923c' : '#cbd5e1';
        ctx.lineWidth = fissureWidth + 3.0;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.stroke();

        // 2. Inner fissure trench
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);

        if (ravine.giant) {
          // Mega-ravine: molten magma glow with dark core
          ctx.strokeStyle = '#c2410c';
          ctx.lineWidth = fissureWidth;
          ctx.shadowColor = '#f97316';
          ctx.shadowBlur = isHovered ? 26 : 16;
          ctx.stroke();

          // Molten lava core line
          ctx.strokeStyle = '#ffedd5';
          ctx.lineWidth = Math.max(2.0, fissureWidth - 2.5);
          ctx.stroke();
          ctx.shadowBlur = 0;

          // Midpoint Badge
          if (elevationFilter !== 'surface') {
            if (isHovered) {
              // Full expanded pill on hover
              const badgeText = `🌋 Mega Ravine Fissure (${ravine.length} blocks) • Bed Y=${ravine.y ?? 'unknown'}`;
              ctx.font = 'bold 12px system-ui';
              const tw = ctx.measureText(badgeText).width;
              ctx.fillStyle = 'rgba(15, 23, 42, 0.96)';
              ctx.strokeStyle = '#f97316';
              ctx.lineWidth = 1.5;
              ctx.beginPath();
              ctx.roundRect(mid.x + 6, mid.y - 14, tw + 14, 26, 4);
              ctx.fill();
              ctx.stroke();
              ctx.fillStyle = '#fed7aa';
              ctx.fillText(badgeText, mid.x + 13, mid.y + 3);
            } else {
              // Clear, punchy abbreviation badge
              const badgeText = `🌋 MEGA ${ravine.length} blocks`;
              ctx.font = 'bold 11px monospace';
              const tw = ctx.measureText(badgeText).width;
              ctx.fillStyle = 'rgba(67, 20, 7, 0.94)';
              ctx.strokeStyle = '#ea580c';
              ctx.lineWidth = 1;
              ctx.beginPath();
              ctx.roundRect(mid.x + 4, mid.y - 10, tw + 8, 20, 3);
              ctx.fill();
              ctx.stroke();
              ctx.fillStyle = '#fed7aa';
              ctx.fillText(badgeText, mid.x + 8, mid.y + 4);
            }
          }
        } else if (ravine.underwater) {
          // Submerged ocean canyon trench
          ctx.strokeStyle = '#0369a1';
          ctx.lineWidth = fissureWidth;
          ctx.shadowColor = '#0284c7';
          ctx.shadowBlur = isHovered ? 14 : 6;
          ctx.stroke();
          ctx.shadowBlur = 0;

          if (elevationFilter !== 'surface') {
            if (isHovered) {
              const badgeText = `🌊 Ocean Trench (${ravine.length} blocks) • Y=${ravine.y ?? 'unknown'}`;
              ctx.font = 'bold 12px system-ui';
              const tw = ctx.measureText(badgeText).width;
              ctx.fillStyle = 'rgba(15, 23, 42, 0.96)';
              ctx.strokeStyle = '#38bdf8';
              ctx.lineWidth = 1.5;
              ctx.beginPath();
              ctx.roundRect(mid.x + 6, mid.y - 14, tw + 14, 26, 4);
              ctx.fill();
              ctx.stroke();
              ctx.fillStyle = '#bae6fd';
              ctx.fillText(badgeText, mid.x + 13, mid.y + 3);
            } else {
              const badgeText = `🌊 TRN`;
              ctx.font = 'bold 10px monospace';
              const tw = ctx.measureText(badgeText).width;
              ctx.fillStyle = 'rgba(12, 74, 110, 0.92)';
              ctx.strokeStyle = '#38bdf8';
              ctx.lineWidth = 1;
              ctx.beginPath();
              ctx.roundRect(mid.x + 4, mid.y - 9, tw + 6, 18, 3);
              ctx.fill();
              ctx.stroke();
              ctx.fillStyle = '#e0f2fe';
              ctx.fillText(badgeText, mid.x + 7, mid.y + 4);
            }
          }
        } else {
          // Overland chasm fissure (dark abyss void)
          ctx.strokeStyle = '#050811';
          ctx.lineWidth = fissureWidth;
          ctx.stroke();

          if (elevationFilter !== 'surface') {
            if (isHovered) {
              // Expanded full badge on hover
              const badgeText = `🌋 Ravine (${ravine.length} blocks) • Bed Y=${ravine.y ?? 'unknown'} • Heading ${Math.round((ravine.yaw * 180) / Math.PI)}°`;
              ctx.font = 'bold 12px system-ui';
              const tw = ctx.measureText(badgeText).width;
              ctx.fillStyle = 'rgba(15, 23, 42, 0.96)';
              ctx.strokeStyle = '#38bdf8';
              ctx.lineWidth = 1.5;
              ctx.beginPath();
              ctx.roundRect(mid.x + 6, mid.y - 14, tw + 14, 26, 4);
              ctx.fill();
              ctx.stroke();
              ctx.fillStyle = '#f1f5f9';
              ctx.fillText(badgeText, mid.x + 13, mid.y + 3);
            } else {
              // Compact abbreviation badge
              const badgeText = `🌋 RAV`;
              ctx.font = 'bold 10px monospace';
              const tw = ctx.measureText(badgeText).width;
              ctx.fillStyle = 'rgba(15, 23, 42, 0.90)';
              ctx.strokeStyle = '#64748b';
              ctx.lineWidth = 1;
              ctx.beginPath();
              ctx.roundRect(mid.x + 4, mid.y - 9, tw + 6, 18, 3);
              ctx.fill();
              ctx.stroke();
              ctx.fillStyle = '#f1f5f9';
              ctx.fillText(badgeText, mid.x + 7, mid.y + 4);
            }
          }
        }
      });
      ctx.restore();
    }

    // 7.6. Subterranean Cave Clusters (Overworld)
    if (showCaves && dimension === 'overworld' && cavesList.length > 0) {
      ctx.save();
      if (elevationFilter === 'surface') {
        ctx.globalAlpha = 0.2; // dimmed if surface-only view
      }

      cavesList.forEach((cave) => {
        const cPos = worldToScreen(cave.x, cave.z, width, height);
        if (cPos.x < -60 || cPos.x > width + 60 || cPos.y < -60 || cPos.y > height + 60) return;

        const isHovered = hoveredCave?.id === cave.id || pinnedFeature?.id === cave.id;

        // 1. Organic Cavern Chamber Aura
        ctx.save();
        const cavernRadius = Math.max(28, 65 * zoom);
        const grad = ctx.createRadialGradient(cPos.x, cPos.y, 0, cPos.x, cPos.y, cavernRadius);
        if (cave.type === 'lush_caves') {
          grad.addColorStop(0, 'rgba(16, 185, 129, 0.35)');
          grad.addColorStop(0.5, 'rgba(5, 150, 105, 0.18)');
          grad.addColorStop(1, 'rgba(2, 44, 34, 0)');
        } else if (cave.type === 'dripstone_caves') {
          grad.addColorStop(0, 'rgba(245, 158, 11, 0.30)');
          grad.addColorStop(0.5, 'rgba(217, 119, 6, 0.15)');
          grad.addColorStop(1, 'rgba(69, 26, 3, 0)');
        } else {
          grad.addColorStop(0, 'rgba(6, 182, 212, 0.35)');
          grad.addColorStop(0.5, 'rgba(8, 145, 178, 0.18)');
          grad.addColorStop(1, 'rgba(8, 51, 68, 0)');
        }
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(cPos.x, cPos.y, cavernRadius, 0, Math.PI * 2);
        ctx.fill();

        // Lush Caves glowing spore particles
        if (cave.type === 'lush_caves') {
          const sporeOffsets = [[-14, -10], [16, -14], [-10, 16], [18, 12], [4, -20]];
          ctx.fillStyle = '#6ee7b7';
          sporeOffsets.forEach(([dx, dz]) => {
            ctx.beginPath();
            ctx.arc(cPos.x + dx * zoom * 1.5, cPos.y + dz * zoom * 1.5, 2.0, 0, Math.PI * 2);
            ctx.fill();
          });
        }
        ctx.restore();

        // 2. Concentric Pulsating Beacon Badge
        const pinRadius = isHovered ? 16 : 13;
        ctx.save();
        ctx.fillStyle = cave.color;
        ctx.shadowColor = cave.color;
        ctx.shadowBlur = isHovered ? 28 : 14;

        ctx.beginPath();
        ctx.arc(cPos.x, cPos.y, pinRadius + 4, 0, Math.PI * 2);
        ctx.globalAlpha = 0.40;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cPos.x, cPos.y, pinRadius, 0, Math.PI * 2);
        ctx.globalAlpha = 0.95;
        ctx.fill();
        ctx.restore();

        // 3. Dark contrast core inside badge
        ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
        ctx.beginPath();
        ctx.arc(cPos.x, cPos.y, pinRadius - 2, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = isHovered ? '#ffffff' : cave.color;
        ctx.lineWidth = isHovered ? 2.5 : 2.0;
        ctx.stroke();

        // 4. Icon inside badge
        ctx.font = `${isHovered ? 15 : 13}px system-ui`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(cave.icon, cPos.x, cPos.y);

        // 5. Label: Abbreviation by default, expanded on hover
        if (elevationFilter !== 'surface') {
          ctx.textAlign = 'left';
          ctx.textBaseline = 'alphabetic';

          if (isHovered) {
            // Full expanded pill with depth
            const title = cave.name;
            const sub = `Y=${cave.y ?? 'unknown'} • ${cave.notes || 'Cavern System'}`;
            ctx.font = 'bold 13px system-ui';
            const tw1 = ctx.measureText(title).width;
            ctx.font = '10px monospace';
            const tw2 = ctx.measureText(sub).width;
            const cardW = Math.max(tw1, tw2) + 16;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.98)';
            ctx.strokeStyle = cave.color;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.roundRect(cPos.x + pinRadius + 6, cPos.y - 16, cardW, 36, 5);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 13px system-ui';
            ctx.fillText(title, cPos.x + pinRadius + 12, cPos.y - 1);

            ctx.fillStyle = cave.color;
            ctx.font = 'bold 10px monospace';
            ctx.fillText(sub, cPos.x + pinRadius + 12, cPos.y + 13);
          } else {
            // Crisp, clear abbreviation pill
            const abbr = cave.type === 'lush_caves' ? 'LSH' : cave.type === 'dripstone_caves' ? 'DRP' : 'DRK';
            ctx.font = 'bold 11px monospace';
            const tw = ctx.measureText(abbr).width;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
            ctx.strokeStyle = cave.color;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.roundRect(cPos.x + pinRadius + 4, cPos.y - 10, tw + 10, 20, 4);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = '#ffffff';
            ctx.fillText(abbr, cPos.x + pinRadius + 9, cPos.y + 4);
          }
        }
      });
      ctx.restore();
    }

    // 8. Structures Rendering (with Larger Icons, Clear Abbreviations & Hover Expansion)
    if (candidate) {
      const activeStructures = candidate.structures.filter((s) => s.dimension === dimension);

      activeStructures.forEach((struct) => {
        const sPos = worldToScreen(struct.x, struct.z, width, height);
        if (sPos.x < -60 || sPos.x > width + 60 || sPos.y < -60 || sPos.y > height + 60) return;

        const isUnderground = isUndergroundStructure(struct.type);
        let alpha = 1.0;
        if (dimension === 'overworld') {
          if (elevationFilter === 'underground' && !isUnderground) alpha = 0.15;
          if (elevationFilter === 'surface' && isUnderground) alpha = 0.15;
        }

        ctx.save();
        ctx.globalAlpha = alpha;

        const isHovered =
          hoveredStructure?.id === struct.id || pinnedFeature?.id === struct.id;
        const dist = struct.distanceToHub;

        const isApex = isApexLandmark(struct.type);

        // 1. Glowing outer halo
        ctx.fillStyle = struct.color;
        ctx.shadowColor = struct.color;
        ctx.shadowBlur = isHovered ? 26 : isApex ? 16 : 8;

        // 2. Circular marker pin (Slightly bigger: radius 13-16px, diameter 26-32px)
        const pinRadius = isHovered ? 16 : 13;
        ctx.beginPath();
        ctx.arc(sPos.x, sPos.y, pinRadius, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(15, 23, 42, 0.96)';
        ctx.fill();

        // High-contrast border
        ctx.strokeStyle = isHovered ? '#ffffff' : struct.color;
        ctx.lineWidth = isHovered ? 2.5 : 2.0;
        ctx.stroke();

        // 3. Emoji icon centered in pin (Slightly bigger: 13-15px font)
        ctx.shadowBlur = 0;
        ctx.font = `${isHovered ? 15 : 13}px system-ui`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(struct.icon, sPos.x, sPos.y);

        // 4. Attached Pill: Clear Abbreviation by default, Full Text + Coords on Hover
        if (alpha > 0.3) {
          ctx.textAlign = 'left';
          ctx.textBaseline = 'alphabetic';

          if (isHovered) {
            // Full expanded card on hover
            const title = struct.name;
            const dist0 = Math.round(struct.distanceToOrigin ?? Math.hypot(struct.x, struct.z));
            const sub = `X:${struct.x} Z:${struct.z} • ${dist0}b from (0,0)${dist != null && Math.abs(dist - dist0) > 2 ? ` • ${dist}b to Hub` : ''}${struct.distanceToSpawn != null ? ` • ${Math.round(struct.distanceToSpawn)}b to Spawn` : ''}`;
            ctx.font = 'bold 13px system-ui';
            const tw1 = ctx.measureText(title).width;
            ctx.font = '10px monospace';
            const tw2 = ctx.measureText(sub).width;
            const cardW = Math.max(tw1, tw2) + 16;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.98)';
            ctx.strokeStyle = isHovered ? '#ffffff' : struct.color;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.roundRect(sPos.x + pinRadius + 6, sPos.y - 16, cardW, 36, 5);
            ctx.fill();
            ctx.stroke();

            // Title
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 13px system-ui';
            ctx.fillText(title, sPos.x + pinRadius + 12, sPos.y - 1);

            // Coords & Distance subtitle
            ctx.fillStyle = struct.color;
            ctx.font = 'bold 10px monospace';
            ctx.fillText(sub, sPos.x + pinRadius + 12, sPos.y + 13);
          } else {
            // Standard state: Clear Abbreviation Pill
            const abbr = getStructureAbbr(struct.type, struct.name);
            ctx.font = 'bold 11px monospace';
            const tw = ctx.measureText(abbr).width;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
            ctx.strokeStyle = struct.color;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.roundRect(sPos.x + pinRadius + 4, sPos.y - 10, tw + 10, 20, 4);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = isApex ? '#ffffff' : '#f1f5f9';
            ctx.fillText(abbr, sPos.x + pinRadius + 9, sPos.y + 4);
          }
        }

        ctx.restore();
      });
    }

    // 9. Metric Scale Bar (Bottom Left)
    ctx.save();
    const scaleBarX = 16;
    const scaleBarY = height - 16;
    const targetPx = 90;
    const rawBlocks = targetPx / zoom;
    let niceBlocks = 100;
    if (rawBlocks > 750) niceBlocks = 1000;
    else if (rawBlocks > 350) niceBlocks = 500;
    else if (rawBlocks > 150) niceBlocks = 200;
    else if (rawBlocks > 75) niceBlocks = 100;
    else niceBlocks = 50;

    const actualBarPx = niceBlocks * zoom;

    // Background bar backdrop
    ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(scaleBarX - 4, scaleBarY - 18, actualBarPx + 8, 22, 4);
    ctx.fill();
    ctx.stroke();

    // Scale tick line
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(scaleBarX, scaleBarY - 4);
    ctx.lineTo(scaleBarX + actualBarPx, scaleBarY - 4);
    ctx.moveTo(scaleBarX, scaleBarY - 8);
    ctx.lineTo(scaleBarX, scaleBarY);
    ctx.moveTo(scaleBarX + actualBarPx, scaleBarY - 8);
    ctx.lineTo(scaleBarX + actualBarPx, scaleBarY);
    ctx.stroke();

    // Scale label
    ctx.fillStyle = '#f1f5f9';
    ctx.font = 'bold 9px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`${niceBlocks} blocks`, scaleBarX + actualBarPx / 2, scaleBarY - 7);
    ctx.restore();

    // 10. Compass Rose in bottom right
    ctx.save();
    const compassX = width - 40;
    const compassY = height - 40;
    ctx.fillStyle = 'rgba(15, 23, 42, 0.7)';
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(compassX, compassY, 20, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // North arrow
    ctx.fillStyle = '#ef4444'; // Red for North
    ctx.beginPath();
    ctx.moveTo(compassX, compassY - 16);
    ctx.lineTo(compassX - 5, compassY - 2);
    ctx.lineTo(compassX + 5, compassY - 2);
    ctx.closePath();
    ctx.fill();

    // South arrow
    ctx.fillStyle = '#94a3b8';
    ctx.beginPath();
    ctx.moveTo(compassX, compassY + 16);
    ctx.lineTo(compassX - 5, compassY + 2);
    ctx.lineTo(compassX + 5, compassY + 2);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 8px monospace';
    ctx.fillText('N', compassX - 3, compassY - 18);
    ctx.restore();
  }, [
    candidate,
    dimension,
    offset,
    zoom,
    showBorders,
    showBiomes,
    showGrid,
    showRavines,
    showCaves,
    showDistanceRings,
    labelMode,
    elevationFilter,
    hoveredStructure,
    hoveredRavine,
    hoveredCave,
    pinnedFeature,
    screenToWorld,
    worldToScreen,
    ravinesList,
    cavesList,
    biomeGrid, profile, gridCenterX, gridCenterZ,
  ]);

  // Mouse pan and zoom handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    mouseDownPosRef.current = { x: e.clientX, y: e.clientY };
  };

  // Throttled hit-testing collision math
  const performHitTest = useCallback(() => {
    hoverRafRef.current = null;
    const canvas = canvasRef.current;
    if (!canvas || !latestMousePosRef.current || !candidate) return;

    const { clientX, clientY } = latestMousePosRef.current;

    // 1. Hit test structures (Generous radius ~24px for larger pins & abbr tags)
    const activeStructures = candidate.structures.filter((s) => s.dimension === dimension);
    const hitStruct = activeStructures.find((s) => {
      const sPos = worldToScreen(s.x, s.z, canvas.width, canvas.height);
      const dx = clientX - sPos.x;
      const dy = clientY - sPos.y;
      return dx * dx + dy * dy < 24 * 24;
    }) || null;

    const nextStructId = hitStruct?.id ?? null;
    if (nextStructId !== hoveredStructureIdRef.current) {
      hoveredStructureIdRef.current = nextStructId;
      setHoveredStructure(hitStruct);
    }

    // 2. Hit test cave clusters (Overworld)
    let hitC: CaveClusterMarker | null = null;
    if (dimension === 'overworld' && showCaves && cavesList.length > 0) {
      hitC = cavesList.find((c) => {
        const cPos = worldToScreen(c.x, c.z, canvas.width, canvas.height);
        const dx = clientX - cPos.x;
        const dy = clientY - cPos.y;
        return dx * dx + dy * dy < 26 * 26;
      }) || null;
    }

    const nextCaveId = hitC?.id ?? null;
    if (nextCaveId !== hoveredCaveIdRef.current) {
      hoveredCaveIdRef.current = nextCaveId;
      setHoveredCave(hitC);
    }

    // 3. Hit test ravines (Overworld)
    let hitR: RavineMarker | null = null;
    if (dimension === 'overworld' && showRavines && ravinesList.length > 0) {
      hitR = ravinesList.find((r) => {
        const halfLen = (r.length || 100) / 2;
        const cosA = Math.cos(r.yaw);
        const sinA = Math.sin(r.yaw);
        const s = worldToScreen(
          r.x - cosA * halfLen,
          r.z - sinA * halfLen,
          canvas.width,
          canvas.height
        );
        const e = worldToScreen(
          r.x + cosA * halfLen,
          r.z + sinA * halfLen,
          canvas.width,
          canvas.height
        );
        const l2 = (e.x - s.x) * (e.x - s.x) + (e.y - s.y) * (e.y - s.y);
        if (l2 === 0) return false;
        let t = ((clientX - s.x) * (e.x - s.x) + (clientY - s.y) * (e.y - s.y)) / l2;
        t = Math.max(0, Math.min(1, t));
        const px = s.x + t * (e.x - s.x);
        const py = s.y + t * (e.y - s.y);
        const distSq = (clientX - px) * (clientX - px) + (clientY - py) * (clientY - py);
        return distSq < 16 * 16;
      }) || null;
    }

    const nextRavineId = hitR?.id ?? null;
    if (nextRavineId !== hoveredRavineIdRef.current) {
      hoveredRavineIdRef.current = nextRavineId;
      setHoveredRavine(hitR);
    }
  }, [candidate, dimension, showCaves, cavesList, showRavines, ravinesList, worldToScreen]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;

    const world = screenToWorld(clientX, clientY, canvas.width, canvas.height);
    cursorWorldRef.current = world;
    if (cursorCoordXRef.current) cursorCoordXRef.current.textContent = String(world.x);
    if (cursorCoordZRef.current) cursorCoordZRef.current.textContent = String(world.z);
    if (cursorCoordDistRef.current) {
      const dist = Math.round(Math.sqrt(world.x * world.x + world.z * world.z));
      cursorCoordDistRef.current.textContent = `(${dist} blocks from origin)`;
    }
    if (cursorCoordBiomeRef.current && biomeGrid && String(biomeGrid.seed) === String(candidate?.seed) && biomeGrid.dimension === dimension) {
      const { bounds, grid, names } = biomeGrid;
      const col = Math.floor((world.x - bounds.x0) / bounds.step);
      const row = Math.floor((world.z - bounds.z0) / bounds.step);
      if (row >= 0 && row < bounds.nz && col >= 0 && col < bounds.nx) {
        const bId = grid[row][col];
        const rawName = names[String(bId)] || 'unknown';
        cursorCoordBiomeRef.current.textContent = rawName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      }
    }

    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
      return;
    }

    if (!candidate) return;

    latestMousePosRef.current = { clientX, clientY };
    if (hoverRafRef.current == null) {
      hoverRafRef.current = requestAnimationFrame(performHitTest);
    }
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(false);
    if (hoverRafRef.current != null) {
      cancelAnimationFrame(hoverRafRef.current);
      performHitTest();
    }
    const dx = e.clientX - mouseDownPosRef.current.x;
    const dy = e.clientY - mouseDownPosRef.current.y;
    const isClick = Math.sqrt(dx * dx + dy * dy) < 6;
    if (isClick && candidate) {
      if (hoveredCave) {
        jumpToLocation(hoveredCave.x, hoveredCave.z, hoveredCave);
      } else if (hoveredRavine) {
        jumpToLocation(hoveredRavine.x, hoveredRavine.z, hoveredRavine);
      } else if (hoveredStructure) {
        jumpToLocation(hoveredStructure.x, hoveredStructure.z, hoveredStructure);
      }
    }
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
    if (hoverRafRef.current != null) {
      cancelAnimationFrame(hoverRafRef.current);
      hoverRafRef.current = null;
    }
    latestMousePosRef.current = null;
    if (hoveredStructureIdRef.current !== null) {
      hoveredStructureIdRef.current = null;
      setHoveredStructure(null);
    }
    if (hoveredCaveIdRef.current !== null) {
      hoveredCaveIdRef.current = null;
      setHoveredCave(null);
    }
    if (hoveredRavineIdRef.current !== null) {
      hoveredRavineIdRef.current = null;
      setHoveredRavine(null);
    }
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
    setZoom((prev) => Math.min(2.5, Math.max(0.08, prev * zoomFactor)));
  };

  const handleResetView = () => {
    setZoom(0.35);
    const viewCenter = candidate?.evaluationCenter ?? candidate?.strongholdAnchor ?? [0, 0];
    const scale = dimension === 'overworld' ? 1 : 1 / 8;
    setOffset({ x: -(viewCenter[0] * scale) * 0.35, y: -(viewCenter[1] * scale) * 0.35 });
  };

  const activeFeature = pinnedFeature || hoveredStructure || hoveredCave || hoveredRavine;
  const activeFeatureDistance = activeFeature && 'viable' in activeFeature
    ? activeFeature.distanceToHub
    : null;
  const activeFeatureDistanceUnits = activeFeature && 'viable' in activeFeature
    ? activeFeature.distanceUnits ?? 'blocks'
    : 'blocks';

  return (
    <div className="relative flex-1 h-full w-full overflow-hidden bg-slate-950">
      {/* Top Floating Control Bar */}
      <div className="absolute top-3 left-3 right-3 z-30 flex items-center justify-between gap-2 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-xl px-2.5 py-1.5 shadow-2xl">
        {/* Left: Dimension Switcher & Coordinates */}
        <div className="flex items-center gap-2">
          <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-0.5 flex">
            <button
              onClick={() => onDimensionChange('overworld')}
              className={`px-2.5 py-1 rounded text-xs font-bold transition-all flex items-center gap-1 ${
                dimension === 'overworld'
                  ? 'bg-emerald-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <span>🌍</span> Overworld
            </button>
            <button
              onClick={() => onDimensionChange('nether')}
              className={`px-2.5 py-1 rounded text-xs font-bold transition-all flex items-center gap-1 ${
                dimension === 'nether'
                  ? 'bg-red-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <span>🔥</span> Nether
            </button>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1 text-[11px] font-mono text-slate-300 flex items-center gap-1.5 shadow-inner">
            <span className="text-slate-500">X:</span>
            <span ref={cursorCoordXRef} className="text-white font-bold">0</span>
            <span className="text-slate-500">Z:</span>
            <span ref={cursorCoordZRef} className="text-white font-bold">0</span>
            <span ref={cursorCoordDistRef} className="text-slate-500 text-[10px]">
              (0 blocks from origin)
            </span>
            {showBiomes && (
              <>
                <span className="text-slate-700">|</span>
                <span className="text-slate-400 flex items-center gap-1">
                  <span>🌿</span>
                  <span ref={cursorCoordBiomeRef} className="text-emerald-400 font-bold">
                    Unknown
                  </span>
                </span>
              </>
            )}
          </div>
        </div>

        {/* Center: Quick Jump Anchor Pills */}
        <div className="hidden lg:flex items-center gap-1 overflow-x-auto scrollbar-none max-w-[420px]">
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mr-1 flex items-center gap-0.5">
            <span>🔎</span> Jump:
          </span>
          {quickJumpTargets.map((target, idx) => (
            <button
              key={idx}
              onClick={() => jumpToLocation(target.x, target.z, target.feature)}
              className="px-2 py-0.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/90 text-slate-200 border border-slate-700/60 text-[11px] font-medium transition-all flex items-center gap-1 hover:border-slate-500 active:scale-95 whitespace-nowrap shadow-sm"
              title={`Jump to ${target.label} at (${target.x}, ${target.z})`}
            >
              <span>{target.icon}</span>
              <span>{target.label}</span>
            </button>
          ))}
        </div>

        {/* Right: Layers, Elevation Filter, and Label LOD */}
        <div className="flex items-center gap-1.5">
          {/* Elevation Layer Filter */}
          {dimension === 'overworld' && (
            <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-0.5 flex">
              <button
                onClick={() => setElevationFilter('all')}
                className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-all ${
                  elevationFilter === 'all'
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Show all surface and subterranean structures"
              >
                All
              </button>
              <button
                onClick={() => setElevationFilter('surface')}
                className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-all ${
                  elevationFilter === 'surface'
                    ? 'bg-emerald-700 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Focus on surface structures (Villages, Mansions, Monuments)"
              >
                Surface
              </button>
              <button
                onClick={() => setElevationFilter('underground')}
                className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-all ${
                  elevationFilter === 'underground'
                    ? 'bg-purple-700 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Focus on underground chambers (Lush Caves, Ancient Cities, Trial Chambers, Ravines)"
              >
                Underground
              </button>
            </div>
          )}

          {/* Label Mode Toggle */}
          <button
            onClick={() =>
              setLabelMode((prev) =>
                prev === 'smart' ? 'all' : prev === 'all' ? 'minimal' : 'smart'
              )
            }
            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-semibold flex items-center gap-1 border border-slate-700/60 transition-all"
            title="Toggle Label Level-of-Detail: Smart (Clear Abbreviations), All (Full titles), Minimal (Icons only)"
          >
            <span>🏷️</span>
            <span className="capitalize">{labelMode}</span>
          </button>

          {/* Ravines Toggle */}
          {onToggleRavines && dimension === 'overworld' && (
            <button
              onClick={onToggleRavines}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all flex items-center gap-1 ${
                showRavines
                  ? 'bg-amber-600/90 text-white shadow-sm ring-1 ring-amber-400/50'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
              title="Toggle Ravines & Chasms"
            >
              <span>🌋</span>
              <span>{ravinesList.length}</span>
            </button>
          )}

          {/* Caves Toggle */}
          {onToggleCaves && dimension === 'overworld' && (
            <button
              onClick={onToggleCaves}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all flex items-center gap-1 ${
                showCaves
                  ? 'bg-emerald-600/90 text-white shadow-sm ring-1 ring-emerald-400/50'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
              title="Toggle Subterranean Cave Clusters"
            >
              <span>🌿</span>
              <span>{cavesList.length}</span>
            </button>
          )}

          {/* Bounds Toggle */}
          {onToggleBorders && (
            <button
              onClick={onToggleBorders}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all ${
                showBorders ? 'bg-slate-700 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
              title="Toggle the selected playable bounds"
            >
              Bounds
            </button>
          )}

          {/* Terrain Toggle */}
          {onToggleBiomes && (
            <button
              onClick={onToggleBiomes}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all ${
                showBiomes ? 'bg-slate-700 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
              title="Toggle sampled predicted biomes"
            >
              Biomes
            </button>
          )}

          {/* Grid Toggle */}
          {onToggleGrid && (
            <button
              onClick={onToggleGrid}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all ${
                showGrid ? 'bg-slate-700 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
              title="Toggle Coordinate Grid"
            >
              Grid
            </button>
          )}
        </div>
      </div>

      {/* Floating Smart Feature Inspector Card */}
      {activeFeature && (
        <div className="absolute top-16 left-3 z-20 bg-slate-900/95 backdrop-blur-md border border-slate-700/80 rounded-xl p-3 text-xs shadow-2xl text-slate-200 animate-in fade-in duration-100 max-w-sm">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
            <div className="font-bold flex items-center gap-1.5 text-white">
              <span className="text-sm">
                {'icon' in activeFeature ? activeFeature.icon : '🌋'}
              </span>
              <span>
                {'name' in activeFeature
                  ? activeFeature.name
                  : (activeFeature as RavineMarker).giant
                  ? 'Mega Ravine Fissure'
                  : 'Ravine Chasm'}
              </span>
              {'underwater' in activeFeature && (activeFeature as RavineMarker).underwater && (
                <span className="text-[9px] text-cyan-400 px-1 rounded bg-cyan-950 border border-cyan-800">
                  Ocean Trench
                </span>
              )}
            </div>
            <button
              onClick={() => {
                setPinnedFeature(null);
                setHoveredStructure(null);
                setHoveredCave(null);
                setHoveredRavine(null);
              }}
              className="text-slate-400 hover:text-white text-xs px-1 hover:bg-slate-800 rounded"
              title="Close inspection card"
            >
              ✕
            </button>
          </div>

          <div className="pt-2 space-y-1 font-mono text-[11px]">
            <div className="flex items-center justify-between text-slate-300">
              <span className="text-slate-400">Position:</span>
              <span className="text-emerald-400 font-bold">
                X:{activeFeature.x}, Z:{activeFeature.z}
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-300">
              <span className="text-slate-400">Depth:</span>
              <span className="text-cyan-400 font-bold">
                Y={'y' in activeFeature && activeFeature.y != null ? activeFeature.y : 'unknown'}
              </span>
            </div>
            {'x' in activeFeature && 'z' in activeFeature && (
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-400">Dist to (0,0):</span>
                <span className="text-cyan-400 font-bold">
                  {Math.round(('distanceToOrigin' in activeFeature && (activeFeature as StructureMarker).distanceToOrigin != null)
                    ? (activeFeature as StructureMarker).distanceToOrigin!
                    : Math.hypot(activeFeature.x, activeFeature.z))} blocks
                </span>
              </div>
            )}
            {Boolean(candidate?.evaluationCenter && (candidate.evaluationCenter[0] !== 0 || candidate.evaluationCenter[1] !== 0)) && (
              <>
                <div className="flex items-center justify-between text-slate-300">
                  <span className="text-slate-400">Dist to Hub:</span>
                  <span className="text-amber-400 font-bold">
                    {activeFeatureDistance == null
                      ? 'unknown'
                      : `${activeFeatureDistance} ${activeFeatureDistanceUnits}`}
                  </span>
                </div>
                {'distanceToSpawn' in activeFeature && (activeFeature as StructureMarker).distanceToSpawn != null && (
                  <div className="flex items-center justify-between text-slate-300">
                    <span className="text-slate-400">Dist to Spawn:</span>
                    <span className="text-emerald-400 font-bold">
                      {Math.round((activeFeature as StructureMarker).distanceToSpawn!)} blocks
                    </span>
                  </div>
                )}
              </>
            )}

            {'length' in activeFeature && (
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-400">Chasm Dimensions:</span>
                <span className="text-amber-300">
                  {(activeFeature as RavineMarker).length} blocks long · {Math.round((activeFeature as RavineMarker).thick * 10) / 10} blocks wide
                </span>
              </div>
            )}
          </div>

          {'notes' in activeFeature && (activeFeature as any).notes && (
            <div className="text-[10px] text-slate-400 mt-2 p-1.5 rounded bg-slate-950 border border-slate-800">
              {(activeFeature as any).notes}
            </div>
          )}

          <div className="mt-2.5 pt-2 border-t border-slate-800 flex items-center justify-between gap-2">
            <button
              onClick={() => jumpToLocation(activeFeature.x, activeFeature.z, activeFeature)}
              className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-semibold transition-all flex items-center gap-1 shadow"
            >
              <span>🔍</span> Center on Map
            </button>
            <button
              onClick={() => {
                const y = 'y' in activeFeature && activeFeature.y != null ? activeFeature.y : 'unknown';
                const text = `X:${activeFeature.x} Z:${activeFeature.z} Y:${y}`;
                navigator.clipboard.writeText(text);
              }}
              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-semibold transition-all"
            >
              📋 Copy Coords
            </button>
          </div>
        </div>
      )}

      {/* Biome Status Overlay */}
      {showBiomes && candidate && !activeFeature && (
        <div className="absolute top-16 left-3 z-10 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 backdrop-blur-md border border-slate-700/80 text-xs shadow-xl pointer-events-none">
          {isLoadingBiomeGrid ? (
            <>
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              <span className="text-cyan-300 font-mono text-[11px]">Sampling model biomes (2,048×2,048)...</span>
            </>
          ) : biomeGrid ? (
            <>
              <span>🌿</span>
              <span className="text-emerald-300 font-semibold text-[11px]">Predicted Bedrock Biome Map</span>
              <span className="text-[10px] text-slate-400 font-mono">({Object.keys(biomeGrid.names).length} Biomes Active)</span>
            </>
          ) : (
            <>
              <span className="text-slate-400">🗺️</span>
              <span className="text-slate-300 text-[11px]">Biome overlay active</span>
            </>
          )}
        </div>
      )}

      {/* Bottom Left: Zoom, Rings & Reset Controls */}
      <div className="absolute bottom-4 left-4 z-20 flex items-center gap-1.5 bg-slate-900/90 backdrop-blur border border-slate-700/80 rounded-lg p-1 shadow-xl">
        <button
          onClick={() => setZoom((z) => Math.min(2.5, z * 1.25))}
          className="w-7 h-7 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-bold flex items-center justify-center"
          title="Zoom In"
        >
          +
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(0.08, z * 0.8))}
          className="w-7 h-7 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-bold flex items-center justify-center"
          title="Zoom Out"
        >
          -
        </button>
        <button
          onClick={() => setShowDistanceRings((r) => !r)}
          className={`px-2 h-7 rounded text-[11px] font-semibold transition-all ${
            showDistanceRings
              ? 'bg-slate-700 text-cyan-300'
              : 'bg-slate-800 text-slate-400 hover:text-white'
          }`}
          title="Toggle 500 / 1000 block rings from world origin"
        >
          Rings
        </button>
        <button
          onClick={handleResetView}
          className="px-2 h-7 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[11px] font-semibold flex items-center justify-center"
          title="Reset view to supplied anchor, evaluation center, or origin"
        >
          Center (0,0)
        </button>
        <span className="text-[10px] text-slate-500 font-mono px-1">
          {(zoom * 100).toFixed(0)}%
        </span>
      </div>

      {/* Main Canvas */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onWheel={handleWheel}
        className={`w-full h-full block ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
      />
    </div>
  );
};
