/**
 * Entry point for Catalog module.
 * Exports CatalogWorkspace named export and default export.
 */
export { CatalogWorkspace, CatalogWorkspace as default } from './CatalogWorkspace';
export * from './types';
export * from './constants';
export * from './api';
export { SvgMap } from './SvgMap';
export { CandidateCard } from './CandidateCard';
export { DetailModal } from './DetailModal';
export { CompareModal } from './CompareModal';
export { FavoritesDrawer } from './FavoritesDrawer';
export { QueryExportModal } from './QueryExportModal';
export { FilterBuilder } from './FilterBuilder';
export { CategoryPresets } from './CategoryPresets';
export { useCatalogState } from './useCatalogState';
