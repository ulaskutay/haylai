export const INSTRUMENTAL_CATALOG = [
  {
    id: "fallback-pop",
    slug: "pop-night",
    title: "Gece Pop",
    genre: "pop",
    bpm: 102,
    key: "A minor",
    storage_path: "pop-night.wav",
    preview_path: "pop-night.wav",
    is_active: true,
  },
  {
    id: "fallback-trap",
    slug: "trap-pulse",
    title: "Trap Pulse",
    genre: "trap",
    bpm: 140,
    key: "F minor",
    storage_path: "trap-pulse.wav",
    preview_path: "trap-pulse.wav",
    is_active: true,
  },
  {
    id: "fallback-rock",
    slug: "rock-drive",
    title: "Rock Drive",
    genre: "rock",
    bpm: 118,
    key: "E minor",
    storage_path: "rock-drive.wav",
    preview_path: "rock-drive.wav",
    is_active: true,
  },
  {
    id: "fallback-lofi",
    slug: "lofi-dusk",
    title: "Lo-Fi Dusk",
    genre: "lofi",
    bpm: 84,
    key: "C major",
    storage_path: "lofi-dusk.wav",
    preview_path: "lofi-dusk.wav",
    is_active: true,
  },
  {
    id: "fallback-slow",
    slug: "slow-ember",
    title: "Gece Slow",
    genre: "slow",
    bpm: 68,
    key: "D minor",
    storage_path: "slow-ember.wav",
    preview_path: "slow-ember.wav",
    is_active: true,
  },
] as const;

export type CatalogInstrumental = (typeof INSTRUMENTAL_CATALOG)[number];

export function catalogByIdOrSlug(id: string) {
  return (
    INSTRUMENTAL_CATALOG.find((bed) => bed.id === id || bed.slug === id) ?? null
  );
}
