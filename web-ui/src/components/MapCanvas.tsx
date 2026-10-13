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

const getFallbackRavines = (): RavineMarker[] => [
  { id: 'rav-f1', x: 120, z: -180, y: 44, yaw: 0.62, length: 110, thick: 4.8, giant: true, underwater: false },
  { id: 'rav-f2', x: -340, z: -120, y: 38, yaw: 2.15, length: 112, thick: 5.2, giant: true, underwater: false },
  { id: 'rav-f3', x: 260, z: 280, y: 52, yaw: 1.28, length: 94, thick: 3.2, giant: false, underwater: false },
  { id: 'rav-f4', x: -160, z: 380, y: 48, yaw: 2.85, length: 98, thick: 3.4, giant: false, underwater: false },
  { id: 'rav-f5', x: 420, z: -360, y: 56, yaw: 0.94, length: 88, thick: 2.8, giant: false, underwater: false },
  { id: 'rav-f6', x: -520, z: 140, y: 42, yaw: 1.85, length: 104, thick: 3.4, giant: false, underwater: false },
  { id: 'rav-f7', x: -740, z: -40, y: 28, yaw: 0.45, length: 106, thick: 3.8, giant: false, underwater: true },
];

const getFallbackCaves = (): CaveClusterMarker[] => [
  { id: 'cave-f1', type: 'lush_caves', name: 'Lush Caves Cavern', x: 160, z: -220, y: -48, icon: '🌿', color: '#10b981', notes: 'Glow berries & spore blossom cavern' },
  { id: 'cave-f2', type: 'dripstone_caves', name: 'Dripstone Cavern', x: -240, z: 180, y: -32, icon: '🪨', color: '#f59e0b', notes: 'Massive stalactites & infinite lava source' },
  { id: 'cave-f3', type: 'deep_dark', name: 'Deep Dark Cavern', x: 256, z: 80, y: -52, icon: '🌌', color: '#06b6d4', notes: 'Surrounds Ancient City' },
];

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
  if (type === 'stronghold') return 'HUB';
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

export const MapCanvas: React.FC<MapCanvasProps> = ({
  candidate,
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
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [cursorWorld, setCursorWorld] = useState<{ x: number; z: number }>({ x: 0, z: 0 });
  const [hoveredStructure, setHoveredStructure] = useState<StructureMarker | null>(null);
  const [hoveredRavine, setHoveredRavine] = useState<RavineMarker | null>(null);
  const [hoveredCave, setHoveredCave] = useState<CaveClusterMarker | null>(null);
  const [pinnedFeature, setPinnedFeature] = useState<
    StructureMarker | RavineMarker | CaveClusterMarker | null
  >(null);
  const [showDistanceRings, setShowDistanceRings] = useState<boolean>(true);

  // Smart Level-of-Detail & Layer Filters
  const [labelMode, setLabelMode] = useState<MapLabelMode>('smart');
  const [elevationFilter, setElevationFilter] = useState<MapElevationFilter>('all');

  // Memoized ravines and subterranean cave clusters
  const ravinesList: RavineMarker[] = useMemo(() => {
    if (!candidate) return [];
    if (candidate.ravines && candidate.ravines.length > 0) return candidate.ravines;
    return getFallbackRavines();
  }, [candidate]);

  const cavesList: CaveClusterMarker[] = useMemo(() => {
    if (!candidate) return [];
    if (candidate.caveClusters && candidate.caveClusters.length > 0) return candidate.caveClusters;
    return getFallbackCaves();
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
      const targets: { label: string; icon: string; x: number; z: number; y?: number; feature: any }[] =
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
        targets.push({ label: 'Stronghold Hub', icon: '🏰', x: sh.x, z: sh.z, y: sh.y, feature: sh });

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
      const targets: { label: string; icon: string; x: number; z: number; y?: number; feature: any }[] =
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

  // Auto-center on candidate when candidate changes
  useEffect(() => {
    if (candidate) {
      if (dimension === 'overworld') {
        setOffset({
          x: -candidate.strongholdAnchor[0] * zoom,
          y: -candidate.strongholdAnchor[1] * zoom,
        });
      } else {
        setOffset({
          x: -(candidate.strongholdAnchor[0] / 8) * zoom,
          y: -(candidate.strongholdAnchor[1] / 8) * zoom,
        });
      }
    }
  }, [candidate?.id, dimension]);

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

    // 2. Concentric Distance Rings (500m, 1000m)
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
      ctx.fillText('500m Hub Radius', originScreen.x + 500 * zoom + 5, originScreen.y - 4);
      ctx.fillText('1000m Hub Radius', originScreen.x + 1000 * zoom + 5, originScreen.y - 4);
      ctx.restore();
    }

    // 3. Biome Terrain Render: Coastal Continent (70–80%) & River Highway
    if (showBiomes && candidate) {
      ctx.save();

      if (dimension === 'overworld') {
        const continentRadius = 820 * zoom;

        // Main continental landmass gradient
        const landGrad = ctx.createRadialGradient(
          originScreen.x,
          originScreen.y,
          0,
          originScreen.x,
          originScreen.y,
          continentRadius * 1.2
        );
        landGrad.addColorStop(0, '#2d6a4f'); // Lush Plains / Forest center
        landGrad.addColorStop(0.5, '#40916c'); // Meadow / Forest
        landGrad.addColorStop(0.75, '#52b788'); // Coastal lowlands
        landGrad.addColorStop(0.92, '#d4c28f'); // Sandy shoreline / beaches
        landGrad.addColorStop(1, 'rgba(8, 18, 38, 0)'); // Blend into deep ocean

        ctx.fillStyle = landGrad;
        ctx.beginPath();

        const isContinent = candidate.terrainPassed !== false;

        // Organic continent polygon (with 320m West Ocean corridor cutout for certified continent)
        const numPoints = 36;
        for (let i = 0; i < numPoints; i++) {
          const angle = (i / numPoints) * Math.PI * 2;
          let oceanIndent = 1.0;
          if (isContinent && angle > Math.PI * 0.65 && angle < Math.PI * 1.35) {
            // Cutout for 320m ocean edge
            oceanIndent = 0.68 + 0.1 * Math.sin((angle - Math.PI) * 4);
          }
          const wobble =
            (1 + Math.sin(angle * 4 + 0.8) * 0.08 + Math.cos(angle * 6) * 0.05) * oceanIndent;
          const r = continentRadius * wobble;
          const px = originScreen.x + Math.cos(angle) * r;
          const py = originScreen.y + Math.sin(angle) * r;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fill();

        // Shallow Coastal Water halo
        ctx.strokeStyle = '#1e3a8a';
        ctx.lineWidth = 14 * zoom;
        ctx.stroke();

        if (isContinent) {
          // River Highway artery (navigable corridor connecting hub to West Ocean)
          ctx.save();
          ctx.strokeStyle = '#38bdf8';
          ctx.lineWidth = Math.max(3, 10 * zoom);
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';
          ctx.beginPath();
          const rStart = worldToScreen(60, 40, width, height);
          const rMid1 = worldToScreen(-120, -60, width, height);
          const rMid2 = worldToScreen(-380, 20, width, height);
          const rEnd = worldToScreen(-740, 80, width, height);

          ctx.moveTo(rStart.x, rStart.y);
          ctx.quadraticCurveTo(rMid1.x, rMid1.y, rMid2.x, rMid2.y);
          ctx.lineTo(rEnd.x, rEnd.y);
          ctx.stroke();

          ctx.fillStyle = '#7dd3fc';
          ctx.font = 'bold 9px monospace';
          ctx.fillText('〰 RIVER HIGHWAY (≥400m)', rMid1.x - 20, rMid1.y - 12);
          ctx.restore();

          // West Ocean Edge annotation
          const oceanLabelPos = worldToScreen(-780, -40, width, height);
          ctx.fillStyle = '#38bdf8';
          ctx.font = 'bold 10px system-ui';
          ctx.fillText('🌊 320m OPEN OCEAN CORRIDOR', oceanLabelPos.x, oceanLabelPos.y);
        } else {
          // Baseline annotation
          const baselineLabelPos = worldToScreen(-700, -40, width, height);
          ctx.fillStyle = '#fbbf24';
          ctx.font = 'bold 10px monospace';
          ctx.fillText('🏰 BASELINE TERRAIN (UNCONSTRAINED)', baselineLabelPos.x, baselineLabelPos.y);
        }
      } else {
        // Nether Wastes / Crimson / Warped
        ctx.fillStyle = '#450a0a';
        ctx.beginPath();
        ctx.arc(originScreen.x, originScreen.y, 450 * zoom, 0, Math.PI * 2);
        ctx.fill();

        // Warped Forest patch
        ctx.fillStyle = '#042f2e';
        ctx.beginPath();
        ctx.arc(originScreen.x + 180 * zoom, originScreen.y - 120 * zoom, 160 * zoom, 0, Math.PI * 2);
        ctx.fill();

        // Basalt Deltas patch
        ctx.fillStyle = '#292524';
        ctx.beginPath();
        ctx.arc(originScreen.x - 200 * zoom, originScreen.y + 160 * zoom, 140 * zoom, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
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

    // 5. Playable Border Squares
    if (showBorders) {
      ctx.save();
      if (dimension === 'overworld') {
        // Unified Playable Boundary: 2048 x 2048 ([-1024, 1024])
        const halfSide = (2048 / 2) * zoom;
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.85)';
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 6]);
        ctx.strokeRect(originScreen.x - halfSide, originScreen.y - halfSide, halfSide * 2, halfSide * 2);

        // Corner coordinate labels
        ctx.fillStyle = '#10b981';
        ctx.font = 'bold 10px monospace';
        ctx.fillText('OVERWORLD 2048 × 2048 BOUNDARY [X: ±1024, Z: ±1024]', originScreen.x - halfSide + 8, originScreen.y - halfSide + 18);
      } else {
        // Nether playable square (1024 x 1024) ([-512, 512])
        const netherHalf = (1024 / 2) * zoom;
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.85)';
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 6]);
        ctx.strokeRect(originScreen.x - netherHalf, originScreen.y - netherHalf, netherHalf * 2, netherHalf * 2);

        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 10px monospace';
        ctx.fillText('NETHER 1024 × 1024 BOUNDARY [X: ±512, Z: ±512]', originScreen.x - netherHalf + 8, originScreen.y - netherHalf + 18);
      }
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

    // 7. Spawn Point Marker & Vector
    if (candidate && dimension === 'overworld') {
      const sp = candidate.spawnPoint || [0, 0];
      const spawnScreen = worldToScreen(sp[0], sp[1], width, height);
      const spawnDist =
        candidate.spawnDistance ?? Math.round(Math.sqrt(sp[0] * sp[0] + sp[1] * sp[1]));

      ctx.save();
      // Dashed connector line from (0,0) to Spawn Point
      ctx.strokeStyle = 'rgba(234, 179, 8, 0.75)';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(originScreen.x, originScreen.y);
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
      ctx.fillText(`🧭 Spawn (${sp[0]}, ${sp[1]}) • ${spawnDist}m`, spawnScreen.x + 14, spawnScreen.y + 4);
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
              const badgeText = `🌋 Mega Ravine Fissure (${ravine.length}m) • Bed Y=${ravine.y}`;
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
              const badgeText = `🌋 MEGA ${ravine.length}m`;
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
              const badgeText = `🌊 Ocean Trench (${ravine.length}m) • Y=${ravine.y}`;
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
              const badgeText = `🌋 Ravine (${ravine.length}m) • Bed Y=${ravine.y} • Heading ${Math.round((ravine.yaw * 180) / Math.PI)}°`;
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
            const sub = `Subterranean Depth Y=${cave.y} • ${cave.notes || 'Cavern System'}`;
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
            const abbr = cave.type === 'lush_caves' ? 'LSH · Y=-48' : cave.type === 'dripstone_caves' ? 'DRP · Y=-32' : 'DRK · Y=-52';
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
        const dist =
          struct.distanceToHub ?? Math.round(Math.sqrt(struct.x * struct.x + struct.z * struct.z));

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
            const sub = `X:${struct.x} Z:${struct.z} • Depth Y=${struct.y ?? 64} • ${dist}m Hub`;
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
    ctx.fillText(`${niceBlocks}m`, scaleBarX + actualBarPx / 2, scaleBarY - 7);
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
  ]);

  // Mouse pan and zoom handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    mouseDownPosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;

    const world = screenToWorld(clientX, clientY, canvas.width, canvas.height);
    setCursorWorld(world);

    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    } else if (candidate) {
      // 1. Hit test structures (Generous radius ~24px for larger pins & abbr tags)
      const activeStructures = candidate.structures.filter((s) => s.dimension === dimension);
      const hitStruct = activeStructures.find((s) => {
        const sPos = worldToScreen(s.x, s.z, canvas.width, canvas.height);
        const dx = clientX - sPos.x;
        const dy = clientY - sPos.y;
        return Math.sqrt(dx * dx + dy * dy) < 24;
      });
      setHoveredStructure(hitStruct || null);

      // 2. Hit test cave clusters (Overworld)
      if (dimension === 'overworld' && showCaves && cavesList.length > 0) {
        const hitC = cavesList.find((c) => {
          const cPos = worldToScreen(c.x, c.z, canvas.width, canvas.height);
          const dx = clientX - cPos.x;
          const dy = clientY - cPos.y;
          return Math.sqrt(dx * dx + dy * dy) < 26;
        });
        setHoveredCave(hitC || null);
      } else {
        setHoveredCave(null);
      }

      // 3. Hit test ravines (Overworld)
      if (dimension === 'overworld' && showRavines && ravinesList.length > 0) {
        const hitR = ravinesList.find((r) => {
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
          const dist = Math.sqrt((clientX - px) * (clientX - px) + (clientY - py) * (clientY - py));
          return dist < 16;
        });
        setHoveredRavine(hitR || null);
      } else {
        setHoveredRavine(null);
      }
    }
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(false);
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

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
    setZoom((prev) => Math.min(2.5, Math.max(0.08, prev * zoomFactor)));
  };

  const handleResetView = () => {
    setZoom(0.35);
    if (candidate) {
      setOffset({
        x: -candidate.strongholdAnchor[0] * 0.35,
        y: -candidate.strongholdAnchor[1] * 0.35,
      });
    } else {
      setOffset({ x: 0, y: 0 });
    }
  };

  const activeFeature = pinnedFeature || hoveredStructure || hoveredCave || hoveredRavine;

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
            <span className="text-white font-bold">{cursorWorld.x}</span>
            <span className="text-slate-500">Z:</span>
            <span className="text-white font-bold">{cursorWorld.z}</span>
            <span className="text-slate-500 text-[10px]">
              ({Math.round(Math.sqrt(cursorWorld.x * cursorWorld.x + cursorWorld.z * cursorWorld.z))}m)
            </span>
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
              title="Toggle Playable Bounds (2048x2048)"
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
              title="Toggle Continent Terrain Shading"
            >
              Terrain
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
                Y={'y' in activeFeature ? activeFeature.y : 64}
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-300">
              <span className="text-slate-400">Hub Distance:</span>
              <span className="text-amber-400 font-bold">
                {Math.round(Math.sqrt(activeFeature.x * activeFeature.x + activeFeature.z * activeFeature.z))}m
              </span>
            </div>

            {'length' in activeFeature && (
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-400">Chasm Dimensions:</span>
                <span className="text-amber-300">
                  {(activeFeature as RavineMarker).length}m long · {Math.round((activeFeature as RavineMarker).thick * 10) / 10}m wide
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
                const text = `X:${activeFeature.x} Z:${activeFeature.z} Y:${'y' in activeFeature ? activeFeature.y : 64}`;
                navigator.clipboard.writeText(text);
              }}
              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-semibold transition-all"
            >
              📋 Copy Coords
            </button>
          </div>
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
          title="Toggle 500m / 1000m concentric distance rings"
        >
          Rings
        </button>
        <button
          onClick={handleResetView}
          className="px-2 h-7 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[11px] font-semibold flex items-center justify-center"
          title="Reset Center & Zoom to (0,0)"
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
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        className={`w-full h-full block ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
      />
    </div>
  );
};
