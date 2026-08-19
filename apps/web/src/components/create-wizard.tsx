"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AudioCapture } from "@/components/audio-capture";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  const [selected, setSelected] = useState<string | null>(null);
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
  const selectedBed = beds.find((bed) => bed.id === selected);

  async function playPreview(bed: Instrumental) {
    const url =
      previewUrls[bed.id] ??
      bed.preview_url ??
      `/demo/${bed.slug}.wav`;
    setPreviewUrls((prev) => ({ ...prev, [bed.id]: url }));
    void new Audio(url).play();
  }

  async function submit() {
    if (!file || !selectedBed) return;
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
          instrumentalId: selectedBed.id,
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
        <span className={step === 2 ? "text-foreground" : ""}>2. Altyapı</span>
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
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            {beds.map((bed) => (
              <div
                key={bed.id}
                role="button"
                tabIndex={0}
                onClick={() => setSelected(bed.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelected(bed.id);
                  }
                }}
                className={`cursor-pointer rounded-2xl border p-4 text-left transition ${
                  selected === bed.id
                    ? "border-primary bg-primary/10"
                    : "border-border bg-card hover:border-primary/50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <p className="font-medium">{bed.title}</p>
                  <Badge variant="secondary">{bed.genre}</Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {bed.bpm ? `${bed.bpm} BPM` : "BPM"} {bed.key ? `· ${bed.key}` : ""}
                </p>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="mt-3 px-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    void playPreview(bed);
                  }}
                >
                  Önizle
                </Button>
              </div>
            ))}
          </div>
          {beds.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Altyapı listesi boş. Supabase migration uygulandıktan sonra kartlar görünür.
            </p>
          ) : null}
          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setStep(1)}>
              Geri
            </Button>
            <Button disabled={!selected} onClick={() => setStep(3)}>
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
              Altyapı: <strong>{selectedBed?.title}</strong>
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
