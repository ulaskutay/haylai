import Link from "next/link";
import { ArrowRight, Mic, Sparkles, Wand2 } from "lucide-react";
import { BeforeAfterPlayer } from "@/components/before-after-player";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export default function HomePage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16">
      <section className="grid items-center gap-12 lg:grid-cols-2">
        <div>
          <p className="mb-3 text-sm font-medium text-primary">Voice-to-Song MVP</p>
          <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Amatör kaydını stüdyo vokaline çevir.
          </h1>
          <p className="mt-4 max-w-xl text-lg text-muted-foreground">
            Gürültüyü sil, detoneleri düzelt, kendi sesinin en iyi halini
            çıkar. Tarzına ve enstrümanlara göre altyapı üretilir, mix/master
            hazır olur.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/create" className={cn(buttonVariants({ size: "lg" }))}>
              Şarkını oluştur
              <ArrowRight />
            </Link>
            <Link
              href="/songs"
              className={cn(buttonVariants({ size: "lg", variant: "outline" }))}
            >
              Şarkılarım
            </Link>
          </div>
        </div>
        <BeforeAfterPlayer />
      </section>

      <section className="mt-20 grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <Mic className="size-5 text-primary" />
            <CardTitle>Kaydet veya yükle</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Tarayıcıdan mikrofon kaydı veya MP3/WAV/M4A sürükle-bırak.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Wand2 className="size-5 text-primary" />
            <CardTitle>AI pipeline</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Temizlik, pitch, RVC v2 ve Pedalboard mix tek iş kuyruğunda.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Sparkles className="size-5 text-primary" />
            <CardTitle>Demo</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Şu an kredi ve iyzico kapalı. Kayıt alıp şarkı üretebilirsin.
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
