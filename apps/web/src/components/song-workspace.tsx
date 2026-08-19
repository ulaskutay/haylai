"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import {
  PIPELINE_COPY,
  type PipelineStep,
  type Song,
} from "@/lib/types";
import { WaveformPlayer } from "@/components/waveform-player";
import { Button, buttonVariants } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const STEPS: PipelineStep[] = [
  "analyzing",
  "cleaning",
  "pitch",
  "rvc",
  "mix",
  "export",
];

export function SongWorkspace({ initial }: { initial: Song }) {
  const [song, setSong] = useState(initial);

  useEffect(() => {
    const supabase = createClient();
    const channel = supabase
      .channel(`song-${initial.id}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "songs",
          filter: `id=eq.${initial.id}`,
        },
        (payload) => {
          const next = payload.new as Song;
          setSong((prev) => ({
            ...prev,
            ...next,
            processed_audio_url: prev.processed_audio_url,
            original_audio_url: prev.original_audio_url,
          }));
        },
      )
      .subscribe();

    const poll = window.setInterval(async () => {
      const res = await fetch(`/api/songs/${initial.id}`);
      if (!res.ok) return;
      const json = await res.json();
      if (json.song) setSong(json.song);
    }, 2500);

    return () => {
      void supabase.removeChannel(channel);
      window.clearInterval(poll);
    };
  }, [initial.id]);

  const stepIndex = Math.max(
    0,
    STEPS.indexOf((song.pipeline_step as PipelineStep) ?? "analyzing"),
  );
  const progress = useMemo(() => {
    if (song.status === "completed") return 100;
    if (song.status === "failed") return 100;
    return Math.round(((stepIndex + 1) / STEPS.length) * 90);
  }, [song.status, stepIndex]);

  const copy =
    PIPELINE_COPY[(song.pipeline_step as PipelineStep) ?? "analyzing"] ??
    "Ses işleniyor...";

  async function retry() {
    const res = await fetch(`/api/songs/${song.id}/retry`, { method: "POST" });
    const json = await res.json();
    if (!res.ok) {
      toast.error(json.error ?? "Yeniden deneme başarısız");
      return;
    }
    toast.success("İşlem yeniden başlatıldı");
  }

  if (song.status === "completed") {
    const src = `/api/songs/${song.id}/stream`;
    return (
      <div className="space-y-6">
        <div>
          <p className="text-sm text-primary">Hazır</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">
            Şarkın tamamlandı
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Vokal ve seçtiğin altyapı harmanlandı. RVC, lisanslı model
            bağlandığında tınıyı değiştirir.
          </p>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5">
          <WaveformPlayer src={src} height={96} />
        </div>
        <a
          href={`/api/songs/${song.id}/download`}
          className={cn(buttonVariants())}
        >
          İndir
        </a>
      </div>
    );
  }

  if (song.status === "failed") {
    return (
      <div className="space-y-4">
        <h1 className="text-3xl font-semibold">İşlem başarısız</h1>
        <p className="text-muted-foreground">
          {song.error_message ?? "Bilinmeyen hata"}
        </p>
        <Button onClick={() => void retry()}>Yeniden dene</Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <Loader2 className="mb-6 size-10 animate-spin text-primary" />
      <h1 className="text-2xl font-semibold tracking-tight">{copy}</h1>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        Yapay zeka vokalini temizliyor, notasını düzeltiyor ve altyapı ile
        harmanlıyor. GPU kapalıysa ilk istek worker’ı uyandırır; bir süre
        sürebilir.
      </p>
      <Progress value={progress} className="mt-8 h-2 w-full max-w-md" />
    </div>
  );
}
