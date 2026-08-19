"use client";

import { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import { Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = {
  src: string;
  height?: number;
};

export function WaveformPlayer({ src, height = 72 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const waveRef = useRef<WaveSurfer | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [waveFailed, setWaveFailed] = useState(false);

  useEffect(() => {
    setWaveFailed(false);
    setPlaying(false);
    if (!containerRef.current) return;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      height,
      waveColor: "rgba(196, 164, 255, 0.35)",
      progressColor: "oklch(0.72 0.16 305)",
      cursorColor: "transparent",
      barWidth: 2,
      barGap: 2,
      barRadius: 2,
      url: src,
      backend: "MediaElement",
    });
    waveRef.current = ws;
    ws.on("play", () => setPlaying(true));
    ws.on("pause", () => setPlaying(false));
    ws.on("finish", () => setPlaying(false));
    ws.on("error", () => setWaveFailed(true));
    return () => {
      ws.destroy();
      waveRef.current = null;
    };
  }, [src, height]);

  function toggle() {
    if (waveFailed) {
      const audio = audioRef.current;
      if (!audio) return;
      if (audio.paused) void audio.play();
      else audio.pause();
      return;
    }
    void waveRef.current?.playPause();
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Button
          type="button"
          size="icon"
          variant="secondary"
          onClick={toggle}
          aria-label={playing ? "Duraklat" : "Oynat"}
        >
          {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
        </Button>
        <div ref={containerRef} className="min-h-[72px] min-w-0 flex-1" />
      </div>
      <audio
        ref={audioRef}
        src={src}
        controls
        className="w-full"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
      />
    </div>
  );
}
