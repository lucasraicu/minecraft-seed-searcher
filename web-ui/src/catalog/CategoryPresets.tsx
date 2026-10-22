import type { CatalogPreset } from './types';

interface CategoryPresetsProps {
  presets: CatalogPreset[];
  activePresetId: string | null;
  onSelectPreset: (preset: CatalogPreset) => void;
}

export function CategoryPresets({
  presets,
  activePresetId,
  onSelectPreset,
}: CategoryPresetsProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Category Presets
        </label>
        <span className="text-[11px] text-slate-400">8 quick templates</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {presets.map(p => {
          const isActive = activePresetId === p.id;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onSelectPreset(p)}
              className={`flex flex-col items-start p-2.5 rounded-lg border text-left transition-all ${
                isActive
                  ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300 shadow-sm'
                  : 'bg-slate-900/90 border-slate-800 hover:border-slate-700 text-slate-300 hover:bg-slate-850'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <span className="font-medium text-xs truncate">{p.label}</span>
                {isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0 ml-1"></span>
                )}
              </div>
              <div className="flex items-center gap-1.5 mt-1 text-[10px] text-slate-400">
                <span>{p.rows.length} {p.rows.length === 1 ? 'rule' : 'rules'}</span>
                <span>&bull;</span>
                <span className="truncate max-w-[80px]" title={p.fallback_profile}>
                  {p.fallback_profile.replace('_', ' ')}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
