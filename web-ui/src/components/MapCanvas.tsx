import React, { useRef, useState, useEffect, useCallback } from 'react';
import type { SeedCandidate, StructureMarker, Dimension } from '../types';

interface MapCanvasProps {
  candidate: SeedCandidate | null;
  dimension: Dimension;
  onDimensionChange: (dim: Dimension) => void;
  showBorders: boolean;
  showBiomes: boolean;
  showGrid: boolean;
}

export const MapCanvas: React.FC<MapCanvasProps> = ({
  candidate,
  dimension,
  onDimensionChange,
  showBorders,
  showBiomes,
  showGrid,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Pan & Zoom state
  const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState<number>(0.35); // 1 pixel = 1/zoom blocks
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [cursorWorld, setCursorWorld] = useState<{ x: number; z: number }>({ x: 0, z: 0 });
  const [hoveredStructure, setHoveredStructure] = useState<StructureMarker | null>(null);

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

    // Handle high-DPI
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    ctx.clearRect(0, 0, width, height);

    // 1. Background fill
    if (dimension === 'overworld') {
      ctx.fillStyle = '#0b1329'; // Deep Ocean blue
    } else {
      ctx.fillStyle = '#1c0808'; // Nether deep red
    }
    ctx.fillRect(0, 0, width, height);

    // 2. Biome Terrain Render (Procedural Island / Ridge / Nether Wastes)
    if (showBiomes && candidate) {
      ctx.save();
      const centerX = width / 2 + offset.x;
      const centerY = height / 2 + offset.y;

      if (dimension === 'overworld') {
        // Island landmass / crater ring
        const islandRadius = (candidate.terrainMetrics.diameter / 2) * zoom;
        const grad = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, islandRadius * 1.3);

        if (candidate.terrainType === 'V1 Island') {
          // Mushroom / lush center
          grad.addColorStop(0, '#5b3256'); // Mushroom mycelium purple
          grad.addColorStop(0.5, '#2e6f40'); // Jungle green
          grad.addColorStop(0.85, '#d4c28f'); // Sandy beach
          grad.addColorStop(1, 'rgba(11, 19, 41, 0)'); // Ocean blend
        } else {
          // V2 Mountain Valley (circular ring with hollow flat center)
          grad.addColorStop(0, '#3f6212'); // Meadow valley floor
          grad.addColorStop(0.65, '#3f6212');
          grad.addColorStop(0.85, '#e2e8f0'); // Mountain snow peaks
          grad.addColorStop(1, 'rgba(11, 19, 41, 0)');
        }

        ctx.fillStyle = grad;
        ctx.beginPath();
        // Slightly irregular organic polygon
        const points = 24;
        for (let i = 0; i < points; i++) {
          const angle = (i / points) * Math.PI * 2;
          const wobble = 1 + Math.sin(angle * 3 + 1.2) * 0.12 + Math.cos(angle * 5) * 0.08;
          const r = islandRadius * wobble;
          const px = centerX + Math.cos(angle) * r;
          const py = centerY + Math.sin(angle) * r;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fill();

        // Surrounding Shallow Water halo
        ctx.strokeStyle = '#1e3a8a';
        ctx.lineWidth = 12 * zoom;
        ctx.stroke();
      } else {
        // Nether Wastes / Crimson / Warped
        ctx.fillStyle = '#450a0a';
        ctx.beginPath();
        ctx.arc(centerX, centerY, 450 * zoom, 0, Math.PI * 2);
        ctx.fill();

        // Warped Forest patch
        ctx.fillStyle = '#042f2e';
        ctx.beginPath();
        ctx.arc(centerX + 180 * zoom, centerY - 120 * zoom, 160 * zoom, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    // 3. Coordinate Grid
    if (showGrid) {
      ctx.save();
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.12)';
      ctx.lineWidth = 1;
      ctx.fillStyle = 'rgba(148, 163, 184, 0.4)';
      ctx.font = '10px monospace';

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

    // 4. Playable Border Squares
    if (showBorders) {
      ctx.save();
      const centerScreen = worldToScreen(0, 0, width, height);

      if (dimension === 'overworld') {
        // Overworld playable square (2688 x 2688)
        const halfSide = (2688 / 2) * zoom;
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.8)';
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 6]);
        ctx.strokeRect(centerScreen.x - halfSide, centerScreen.y - halfSide, halfSide * 2, halfSide * 2);

        // Core 1200x1200
        const coreHalf = (1200 / 2) * zoom;
        ctx.strokeStyle = 'rgba(14, 165, 233, 0.4)';
        ctx.strokeRect(centerScreen.x - coreHalf, centerScreen.y - coreHalf, coreHalf * 2, coreHalf * 2);

        // Label
        ctx.fillStyle = '#10b981';
        ctx.font = 'bold 11px system-ui';
        ctx.fillText('PLAYABLE OVERWORLD (2688 × 2688)', centerScreen.x - halfSide + 8, centerScreen.y - halfSide + 18);
      } else {
        // Nether playable square (1024 x 1024)
        const netherHalf = (1024 / 2) * zoom;
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.8)';
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 6]);
        ctx.strokeRect(centerScreen.x - netherHalf, centerScreen.y - netherHalf, netherHalf * 2, netherHalf * 2);

        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 11px system-ui';
        ctx.fillText('PLAYABLE NETHER (1024 × 1024)', centerScreen.x - netherHalf + 8, centerScreen.y - netherHalf + 18);
      }
      ctx.restore();
    }

    // 5. World Origin (0, 0)
    const originScreen = worldToScreen(0, 0, width, height);
    ctx.save();
    ctx.fillStyle = '#f8fafc';
    ctx.beginPath();
    ctx.arc(originScreen.x, originScreen.y, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(originScreen.x, originScreen.y, 9, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px monospace';
    ctx.fillText('(0, 0)', originScreen.x + 12, originScreen.y + 4);
    ctx.restore();

    // 6. Structures Rendering
    if (candidate) {
      const activeStructures = candidate.structures.filter((s) => s.dimension === dimension);

      activeStructures.forEach((struct) => {
        const sPos = worldToScreen(struct.x, struct.z, width, height);

        // Check if within visible viewport
        if (sPos.x < -40 || sPos.x > width + 40 || sPos.y < -40 || sPos.y > height + 40) return;

        ctx.save();
        const isHovered = hoveredStructure?.id === struct.id;

        // Glow ring
        ctx.fillStyle = struct.color;
        ctx.shadowColor = struct.color;
        ctx.shadowBlur = isHovered ? 20 : 8;

        // Marker pill
        ctx.beginPath();
        ctx.arc(sPos.x, sPos.y, isHovered ? 12 : 9, 0, Math.PI * 2);
        ctx.fill();

        // White border
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Text label
        ctx.shadowBlur = 0;
        ctx.fillStyle = '#ffffff';
        ctx.font = isHovered ? 'bold 12px system-ui' : '11px system-ui';
        const label = `${struct.icon} ${struct.name}`;
        ctx.fillText(label, sPos.x + 14, sPos.y + 4);

        // Coordinates subtitle
        ctx.fillStyle = 'rgba(203, 213, 225, 0.7)';
        ctx.font = '9px monospace';
        ctx.fillText(`X:${struct.x} Z:${struct.z}`, sPos.x + 14, sPos.y + 16);

        ctx.restore();
      });
    }
  }, [
    candidate,
    dimension,
    offset,
    zoom,
    showBorders,
    showBiomes,
    showGrid,
    hoveredStructure,
    screenToWorld,
    worldToScreen,
  ]);

  // Mouse Handlers for Pan & Zoom
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Update coordinate crosshair
    const worldCoord = screenToWorld(mouseX, mouseY, canvas.width, canvas.height);
    setCursorWorld(worldCoord);

    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    } else if (candidate) {
      // Hover detection on structures
      const activeStructures = candidate.structures.filter((s) => s.dimension === dimension);
      let found: StructureMarker | null = null;
      for (const struct of activeStructures) {
        const sPos = worldToScreen(struct.x, struct.z, canvas.width, canvas.height);
        const dist = Math.hypot(sPos.x - mouseX, sPos.y - mouseY);
        if (dist <= 18) {
          found = struct;
          break;
        }
      }
      setHoveredStructure(found);
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
    setZoom((z) => Math.min(Math.max(z * zoomFactor, 0.04), 3.0));
  };

  return (
    <div ref={containerRef} className="relative flex-1 h-full w-full overflow-hidden select-none bg-slate-950">
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        className="w-full h-full cursor-crosshair block"
      />

      {/* Floating Map Controls HUD */}
      <div className="absolute top-4 left-4 flex flex-col gap-2 z-20">
        {/* Dimension Switcher */}
        <div className="flex bg-slate-900/90 backdrop-blur border border-slate-700 rounded-lg p-1 shadow-xl">
          <button
            onClick={() => onDimensionChange('overworld')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
              dimension === 'overworld'
                ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            🌍 Overworld
          </button>
          <button
            onClick={() => onDimensionChange('nether')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
              dimension === 'nether'
                ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            🔥 Nether
          </button>
        </div>

        {/* Selected Seed Info Pill */}
        {candidate && (
          <div className="bg-slate-900/90 backdrop-blur border border-slate-700/80 rounded-lg px-3 py-2 text-xs shadow-xl text-slate-300">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white">Seed:</span>
              <span className="font-mono text-emerald-400 font-bold">{candidate.seed}</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold text-[10px]">
                {candidate.score} / 100
              </span>
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5 flex gap-3">
              <span>{candidate.terrainType}</span>
              <span>•</span>
              <span>Ø {candidate.terrainMetrics.diameter}m</span>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Right Zoom & Reset Buttons */}
      <div className="absolute bottom-6 right-6 flex flex-col gap-2 z-20">
        <button
          onClick={() => setZoom((z) => Math.min(z * 1.25, 3.0))}
          className="w-9 h-9 bg-slate-900/90 hover:bg-slate-800 border border-slate-700 text-white rounded-lg flex items-center justify-center font-bold text-lg shadow-xl"
          title="Zoom In"
        >
          +
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(z * 0.8, 0.04))}
          className="w-9 h-9 bg-slate-900/90 hover:bg-slate-800 border border-slate-700 text-white rounded-lg flex items-center justify-center font-bold text-lg shadow-xl"
          title="Zoom Out"
        >
          −
        </button>
        <button
          onClick={() => {
            setOffset({ x: 0, y: 0 });
            setZoom(0.35);
          }}
          className="w-9 h-9 bg-slate-900/90 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg flex items-center justify-center text-xs shadow-xl font-mono"
          title="Reset View to (0,0)"
        >
          (0,0)
        </button>
      </div>

      {/* Bottom Left Coordinate Readout */}
      <div className="absolute bottom-6 left-6 bg-slate-900/90 backdrop-blur border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-300 shadow-xl flex items-center gap-4 z-20">
        <div>
          <span className="text-slate-500">Cursor: </span>
          <span className="text-white font-bold">
            X: {cursorWorld.x.toLocaleString()}, Z: {cursorWorld.z.toLocaleString()}
          </span>
        </div>
        <div className="text-slate-500">|</div>
        <div>
          <span className="text-slate-500">Scale: </span>
          <span className="text-slate-400">{(1 / zoom).toFixed(1)} blk/px</span>
        </div>
      </div>

      {/* Structure Hover Tooltip Card */}
      {hoveredStructure && (
        <div
          className="absolute z-30 pointer-events-none bg-slate-900/95 border border-slate-700 rounded-lg p-3 shadow-2xl backdrop-blur-md text-xs w-64"
          style={{
            left: Math.min(window.innerWidth - 300, 20),
            top: 140,
          }}
        >
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-lg">{hoveredStructure.icon}</span>
            <span className="font-bold text-white text-sm">{hoveredStructure.name}</span>
          </div>
          <div className="space-y-1 text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-400">World Coords:</span>
              <span className="font-mono text-emerald-400">
                X:{hoveredStructure.x}, Z:{hoveredStructure.z}
                {hoveredStructure.y !== undefined && `, Y:${hoveredStructure.y}`}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Dimension:</span>
              <span className="capitalize">{hoveredStructure.dimension}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Viability:</span>
              <span className="text-emerald-400 font-semibold">100% PREDICTED</span>
            </div>
            {hoveredStructure.notes && (
              <div className="mt-2 pt-2 border-t border-slate-800 text-slate-400 italic">
                "{hoveredStructure.notes}"
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
