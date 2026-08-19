"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Square, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MAX_DURATION_SECONDS, MAX_UPLOAD_BYTES } from "@/lib/types";
import { WaveformPlayer } from "@/components/waveform-player";

type Props = {
  file: File | null;
  objectUrl: string | null;
  duration: number;
  onFile: (file: File, duration: number) => void;
};

function pickMimeType() {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ];
  return types.find((type) => MediaRecorder.isTypeSupported(type)) ?? "";
}

function extensionFor(mime: string) {
  if (mime.includes("mp4")) return "m4a";
  if (mime.includes("ogg")) return "ogg";
  return "webm";
}

async function readDuration(file: File, fallbackSeconds?: number) {
  try {
    const ctx = new AudioContext();
    const buffer = await ctx.decodeAudioData(await file.arrayBuffer());
    await ctx.close();
    if (Number.isFinite(buffer.duration) && buffer.duration > 0) {
      return buffer.duration;
    }
  } catch {
    // Fall through to HTMLAudioElement / wall-clock.
  }

  const url = URL.createObjectURL(file);
  try {
    const audio = new Audio();
    audio.preload = "metadata";
    const seconds = await new Promise<number>((resolve, reject) => {
      audio.addEventListener(
        "loadedmetadata",
        () => resolve(audio.duration),
        { once: true },
      );
      audio.addEventListener("error", () => reject(new Error("Ses okunamadı")), {
        once: true,
      });
      audio.src = url;
    });
    if (Number.isFinite(seconds) && seconds > 0) return seconds;
  } finally {
    URL.revokeObjectURL(url);
  }

  if (fallbackSeconds && fallbackSeconds > 0.4) return fallbackSeconds;
  throw new Error("Süre okunamadı");
}

export function AudioCapture({ file, objectUrl, duration, onFile }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAtRef = useRef(0);
  const maxTimerRef = useRef<number | null>(null);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    return () => {
      if (maxTimerRef.current) window.clearTimeout(maxTimerRef.current);
      recorderRef.current?.stream.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function accept(next: File, fallbackSeconds?: number) {
    setError(null);
    if (next.size > MAX_UPLOAD_BYTES) {
      setError("Dosya 20 MB sınırını aşıyor");
      return;
    }
    if (next.size < 256) {
      setError("Kayıt boş geldi. Mikrofon iznini kontrol et.");
      return;
    }
    try {
      const seconds = await readDuration(next, fallbackSeconds);
      if (!Number.isFinite(seconds) || seconds <= 0.4) {
        setError("Ses çok kısa — biraz daha uzun söyle.");
        return;
      }
      if (seconds > MAX_DURATION_SECONDS + 2) {
        setError(`En fazla ${MAX_DURATION_SECONDS} saniye kaydedebilirsin`);
        return;
      }
      onFile(next, Math.min(seconds, MAX_DURATION_SECONDS));
    } catch {
      if (fallbackSeconds && fallbackSeconds > 0.4) {
        onFile(next, Math.min(fallbackSeconds, MAX_DURATION_SECONDS));
        return;
      }
      setError("Bu ses işlenemedi. WAV/MP3 yüklemeyi dene.");
    }
  }

  async function startRecording() {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Bu tarayıcı mikrofon kaydını desteklemiyor.");
      return;
    }
    if (typeof MediaRecorder === "undefined") {
      setError("MediaRecorder yok. Chrome veya Edge dene.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      const mime = pickMimeType();
      const recorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      chunksRef.current = [];
      startedAtRef.current = Date.now();

      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        setError("Kayıt sırasında hata oluştu.");
        stream.getTracks().forEach((track) => track.stop());
        setRecording(false);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        if (maxTimerRef.current) {
          window.clearTimeout(maxTimerRef.current);
          maxTimerRef.current = null;
        }
        const elapsed = (Date.now() - startedAtRef.current) / 1000;
        const type = recorder.mimeType || mime || "audio/webm";
        const blob = new Blob(chunksRef.current, { type });
        const recorded = new File(
          [blob],
          `recording.${extensionFor(type)}`,
          { type },
        );
        void accept(recorded, elapsed);
      };

      recorderRef.current = recorder;
      recorder.start(250);
      setRecording(true);
      maxTimerRef.current = window.setTimeout(() => {
        if (recorder.state === "recording") recorder.stop();
        setRecording(false);
      }, MAX_DURATION_SECONDS * 1000);
    } catch (err) {
      const name = err instanceof DOMException ? err.name : "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        setError("Mikrofon izni reddedildi. Tarayıcı adres çubuğundan izin ver.");
        return;
      }
      if (name === "NotFoundError") {
        setError("Mikrofon bulunamadı.");
        return;
      }
      setError(
        err instanceof Error ? err.message : "Mikrofon başlatılamadı.",
      );
    }
  }

  function stopRecording() {
    const recorder = recorderRef.current;
    if (recorder && recorder.state === "recording") {
      recorder.stop();
    }
    setRecording(false);
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const dropped = e.dataTransfer.files[0];
          if (dropped) void accept(dropped);
        }}
        className={`rounded-2xl border border-dashed p-8 text-center transition ${
          dragOver ? "border-primary bg-primary/5" : "border-border bg-card"
        }`}
      >
        <Upload className="mx-auto mb-3 size-8 text-muted-foreground" />
        <p className="font-medium">Dosya yükle veya sürükle</p>
        <p className="mt-1 text-sm text-muted-foreground">
          MP3, WAV, M4A · en fazla {MAX_DURATION_SECONDS} sn
        </p>
        <Button
          type="button"
          variant="secondary"
          className="mt-4"
          onClick={() => inputRef.current?.click()}
        >
          Dosya seç
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept="audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/m4a,audio/webm,.mp3,.wav,.m4a"
          className="hidden"
          onChange={(e) => {
            const selected = e.target.files?.[0];
            if (selected) void accept(selected);
          }}
        />
      </div>

      <div className="flex justify-center">
        {recording ? (
          <Button type="button" variant="destructive" onClick={stopRecording}>
            <Square className="size-4" />
            Kaydı durdur
          </Button>
        ) : (
          <Button type="button" onClick={() => void startRecording()}>
            <Mic className="size-4" />
            Mikrofonla kaydet
          </Button>
        )}
      </div>

      {recording ? (
        <p className="text-center text-sm text-primary">Kayıt alınıyor… bitince Durdur’a bas.</p>
      ) : null}

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {file && objectUrl ? (
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="mb-3 text-sm text-muted-foreground">
            {file.name} · {duration.toFixed(1)} sn
          </p>
          <WaveformPlayer src={objectUrl} />
        </div>
      ) : null}
    </div>
  );
}
