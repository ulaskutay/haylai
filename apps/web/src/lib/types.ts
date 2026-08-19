export type SongStatus = "pending" | "processing" | "completed" | "failed";

export type Instrumental = {
  id: string;
  slug: string;
  title: string;
  genre: string;
  bpm: number | null;
  key: string | null;
  storage_path: string;
  preview_path: string | null;
  preview_url?: string;
  is_active: boolean;
};

export type Song = {
  id: string;
  user_id: string;
  original_audio_url: string | null;
  original_path: string | null;
  processed_audio_url: string | null;
  processed_path: string | null;
  genre: string | null;
  instrumental_id: string | null;
  duration_seconds: number | null;
  credits_charged: number;
  status: SongStatus;
  pipeline_step: string | null;
  error_message: string | null;
  runpod_job_id: string | null;
  created_at: string;
  updated_at: string;
};

export type PipelineStep =
  | "analyzing"
  | "cleaning"
  | "pitch"
  | "rvc"
  | "mix"
  | "export";

export const PIPELINE_COPY: Record<PipelineStep, string> = {
  analyzing: "Ses analiz ediliyor...",
  cleaning: "Gürültü temizleniyor...",
  pitch: "Detoneler düzeltiliyor...",
  rvc: "Vokal karakteri dönüştürülüyor...",
  mix: "Vokal harmanlanıyor...",
  export: "Master hazırlanıyor...",
};

export function creditsForDuration(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 30) return 1;
  if (seconds <= 60) return 2;
  if (seconds <= 90) return 3;
  return 4;
}

export const CREDIT_PACKS = [
  { id: "starter", credits: 10, amountTry: 99, label: "Başlangıç" },
  { id: "plus", credits: 30, amountTry: 249, label: "Plus" },
  { id: "pro", credits: 100, amountTry: 699, label: "Pro" },
] as const;

export const MAX_DURATION_SECONDS = 90;
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
