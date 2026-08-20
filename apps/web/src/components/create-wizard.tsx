"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AudioCapture } from "@/components/audio-capture";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  INSTRUMENTS,
  STYLES,
  styleById,
  type InstrumentId,
  type RhythmMode,
  type StyleId,
} from "@/lib/arrangement";
import { isCreditsUiDisabled } from "@/lib/credits";
import { creditsForDuration, type Instrumental } from "@/lib/types";
import { toast } from "sonner";

export function CreateWizard() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [file, setFile] = useState<File | null>(null);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [beds, setBeds] = useState<Instrumental[]>([]);
  const [genre, setGenre] = useState<StyleId>("pop");
  const [instruments, setInstruments] = useState<InstrumentId[]>([
    ...styleById("pop").instruments,
  ]);
  const [rhythm, setRhythm] = useState<RhythmMode>("follow");
  const [submitting, setSubmitting] = useState(false);
  const [previewUrls, setPreviewUrls] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch("/api/instrumentals")
      .then((r) => r.json())
      .then((json) => setBeds(json.instrumentals ?? []))
      .catch(() => toast.error("Altyapılar yüklenemedi"));
  }, []);

  useEffect(() => {
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [objectUrl]);

  const cost = useMemo(() => creditsForDuration(duration), [duration]);
  const style = styleById(genre);
  const previewBed = beds.find((bed) => bed.genre === genre) ?? beds[0];

  function pickStyle(next: StyleId) {
    setGenre(next);
    setInstruments([...styleById(next).instruments]);
  }

  function toggleInstrument(id: InstrumentId) {
    setInstruments((prev) => {
      if (prev.includes(id)) {
        if (prev.length === 1) return prev;
        return prev.filter((item) => item !== id);
      }
      return [...prev, id];
    });
  }

  async function playPreview() {
    if (!previewBed) return;
    const url =
      previewUrls[previewBed.id] ??
      previewBed.preview_url ??
      `/demo/${previewBed.slug}.wav`;
    setPreviewUrls((prev) => ({ ...prev, [previewBed.id]: url }));
    void new Audio(url).play();
  }

  async function submit() {
    if (!file) return;
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const signRes = await fetch("/api/uploads/original", {
        method: "POST",
        body: form,
      });
      const signJson = await signRes.json();
      if (!signRes.ok) throw new Error(signJson.error);

      const createRes = await fetch("/api/songs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          durationSeconds: duration,
          genre,
          instruments,
          rhythm,
          instrumentalId: previewBed?.id,
          originalPath: signJson.path,
          contentType: file.type,
        }),
      });
      const createJson = await createRes.json();
      if (createRes.status === 402) {
        throw new Error("Yetersiz kredi");
      }
      if (!createRes.ok) throw new Error(createJson.error);
      router.push(`/songs/${createJson.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Oluşturma başarısız");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex gap-2 text-sm text-muted-foreground">
        <span className={step === 1 ? "text-foreground" : ""}>1. Ses</span>
        <span>/</span>
        <span className={step === 2 ? "text-foreground" : ""}>2. Tarz</span>
        <span>/</span>
        <span className={step === 3 ? "text-foreground" : ""}>3. Onay</span>
      </div>

      {step === 1 ? (
        <Card>
          <CardHeader>
            <CardTitle>Sesini kaydet veya yükle</CardTitle>
          </CardHeader>
          <CardContent>
            <AudioCapture
              file={file}
              objectUrl={objectUrl}
              duration={duration}
              onFile={(next, seconds) => {
                if (objectUrl) URL.revokeObjectURL(objectUrl);
                setFile(next);
                setDuration(seconds);
                setObjectUrl(URL.createObjectURL(next));
              }}
            />
            <div className="mt-6 flex justify-end">
              <Button disabled={!file} onClick={() => setStep(2)}>
                Devam
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {step === 2 ? (
        <div className="space-y-6">
          <div>
            <p className="mb-3 text-sm text-muted-foreground">
              Tarzı seç. Altyapı bu tarza ve enstrümanlara göre üretilir. Ritim
              varsayılan olarak kaydına uyar.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {STYLES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => pickStyle(item.id)}
                  className={`rounded-2xl border p-4 text-left transition ${
                    genre === item.id
                      ? "border-primary bg-primary/10"
                      : "border-border bg-card hover:border-primary/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{item.title}</p>
                    <Badge variant="secondary">{item.bpm} BPM</Badge>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{item.key}</p>
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-3 text-sm text-muted-foreground">Enstrümanlar</p>
            <div className="flex flex-wrap gap-2">
              {INSTRUMENTS.map((item) => {
                const on = instruments.includes(item.id);
                return (
                  <Button
                    key={item.id}
                    type="button"
                    size="sm"
                    variant={on ? "default" : "outline"}
                    onClick={() => toggleInstrument(item.id)}
                  >
                    {item.label}
                  </Button>
                );
              })}
            </div>
          </div>

          <div>
            <p className="mb-3 text-sm text-muted-foreground">Ritim</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => setRhythm("follow")}
                className={`rounded-2xl border p-4 text-left transition ${
                  rhythm === "follow"
                    ? "border-primary bg-primary/10"
                    : "border-border bg-card hover:border-primary/50"
                }`}
              >
                <p className="font-medium">Kaydıma uydur</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Söylediğin tempoyu okur, davul yoksa pad seninle nefes alır. Amatör
                  kayıtta en güvenlisi.
                </p>
              </button>
              <button
                type="button"
                onClick={() => setRhythm("style")}
                className={`rounded-2xl border p-4 text-left transition ${
                  rhythm === "style"
                    ? "border-primary bg-primary/10"
                    : "border-border bg-card hover:border-primary/50"
                }`}
              >
                <p className="font-medium">Tarza kilitle</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {style.bpm} BPM ({style.bpmMin}–{style.bpmMax}). Sen biraz önde
                  veya geride kalabilirsin.
                </p>
              </button>
            </div>
          </div>

          <Button type="button" variant="ghost" className="px-0" onClick={() => void playPreview()}>
            Tarz önizlemesi
          </Button>

          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setStep(1)}>
              Geri
            </Button>
            <Button disabled={!instruments.length} onClick={() => setStep(3)}>
              Devam
            </Button>
          </div>
        </div>
      ) : null}

      {step === 3 ? (
        <Card>
          <CardHeader>
            <CardTitle>Onayla ve oluştur</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p>
              Süre: <strong>{duration.toFixed(1)} sn</strong>
            </p>
            <p>
              Tarz: <strong>{style.title}</strong>
            </p>
            <p>
              Enstrüman:{" "}
              <strong>
                {instruments
                  .map((id) => INSTRUMENTS.find((item) => item.id === id)?.label ?? id)
                  .join(", ")}
              </strong>
            </p>
            <p>
              Ritim:{" "}
              <strong>
                {rhythm === "follow" ? "Kaydına uyacak" : `${style.bpm} BPM kilit`}
              </strong>
            </p>
            {isCreditsUiDisabled() ? (
              <p className="text-sm text-muted-foreground">
                Demo modu: kredi düşülmez, ödeme kapalı.
              </p>
            ) : (
              <p>
                Bu işlem <strong>{cost} kredi</strong> düşecek.
              </p>
            )}
            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep(2)}>
                Geri
              </Button>
              <Button disabled={submitting} onClick={() => void submit()}>
                {submitting ? "Yükleniyor..." : "Şarkını oluştur"}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
