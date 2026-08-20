export const STYLES = [
  {
    id: "pop",
    title: "Pop",
    bpm: 92,
    bpmMin: 86,
    bpmMax: 98,
    key: "A minor",
    instruments: ["drums", "bass", "keys", "pad"],
  },
  {
    id: "trap",
    title: "Trap",
    bpm: 140,
    bpmMin: 128,
    bpmMax: 152,
    key: "F minor",
    instruments: ["drums", "bass", "synth", "pad"],
  },
  {
    id: "rock",
    title: "Rock",
    bpm: 118,
    bpmMin: 108,
    bpmMax: 132,
    key: "E minor",
    instruments: ["drums", "bass", "guitar"],
  },
  {
    id: "lofi",
    title: "Lo-Fi",
    bpm: 84,
    bpmMin: 72,
    bpmMax: 96,
    key: "C major",
    instruments: ["drums", "bass", "keys", "pad"],
  },
  {
    id: "slow",
    title: "Slow",
    bpm: 68,
    bpmMin: 56,
    bpmMax: 78,
    key: "D minor",
    instruments: ["pad", "keys", "strings", "bass"],
  },
] as const;

export const INSTRUMENTS = [
  { id: "drums", label: "Davul" },
  { id: "bass", label: "Bas" },
  { id: "keys", label: "Piyano" },
  { id: "guitar", label: "Gitar" },
  { id: "pad", label: "Pad" },
  { id: "synth", label: "Synth" },
  { id: "strings", label: "Yaylı" },
] as const;

export type StyleId = (typeof STYLES)[number]["id"];
export type InstrumentId = (typeof INSTRUMENTS)[number]["id"];
export type RhythmMode = "follow" | "style";

export function normalizeRhythm(raw: unknown): RhythmMode {
  return raw === "style" || raw === "lock" ? "style" : "follow";
}

export function styleById(id: string) {
  return STYLES.find((style) => style.id === id) ?? STYLES[0];
}

export function normalizeInstruments(raw: unknown, styleId: string): InstrumentId[] {
  const allowed = new Set(INSTRUMENTS.map((item) => item.id));
  const fromUser = Array.isArray(raw)
    ? raw.filter((id): id is InstrumentId => allowed.has(id as InstrumentId))
    : typeof raw === "string"
      ? raw
          .split(",")
          .map((part) => part.trim())
          .filter((id): id is InstrumentId => allowed.has(id as InstrumentId))
      : [];
  if (fromUser.length) return [...new Set(fromUser)];
  return [...styleById(styleId).instruments];
}
