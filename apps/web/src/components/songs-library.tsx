"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Song } from "@/lib/types";
import { toast } from "sonner";

const STATUS_LABEL: Record<string, string> = {
  pending: "Kuyrukta",
  processing: "İşleniyor",
  completed: "Hazır",
  failed: "Hata",
};

export function SongsLibrary() {
  const [songs, setSongs] = useState<Song[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function regenerate(id: string) {
    setBusyId(id);
    try {
      const res = await fetch(`/api/songs/${id}/retry`, { method: "POST" });
      const json = await res.json();
      if (!res.ok) {
        toast.error(json.error ?? "Yeniden oluşturma başarısız");
        return;
      }
      setSongs((prev) =>
        prev.map((song) =>
          song.id === id
            ? {
                ...song,
                status: "processing",
                pipeline_step: "analyzing",
                error_message: null,
              }
            : song,
        ),
      );
      toast.success("Yeniden oluşturuluyor");
    } finally {
      setBusyId(null);
    }
  }

  useEffect(() => {
    fetch("/api/songs")
      .then((r) => r.json())
      .then((json) => setSongs(json.songs ?? []))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="text-sm text-muted-foreground">Yükleniyor...</p>;
  }

  if (!songs.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border p-10 text-center">
        <p className="text-muted-foreground">Henüz şarkın yok.</p>
        <Link href="/create" className={cn(buttonVariants(), "mt-4 inline-flex")}>
          İlk şarkını oluştur
        </Link>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {songs.map((song) => (
        <li key={song.id}>
          <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-3">
            <Link
              href={`/songs/${song.id}`}
              className="flex min-w-0 flex-1 items-center justify-between hover:opacity-90"
            >
              <div>
                <p className="font-medium capitalize">{song.genre ?? "şarkı"}</p>
                <p className="text-sm text-muted-foreground">
                  {new Date(song.created_at).toLocaleString("tr-TR")} ·{" "}
                  {song.credits_charged} kredi
                </p>
              </div>
              <Badge variant={song.status === "completed" ? "default" : "secondary"}>
                {STATUS_LABEL[song.status] ?? song.status}
              </Badge>
            </Link>
            {song.status === "completed" || song.status === "failed" ? (
              <Button
                size="sm"
                variant="outline"
                disabled={busyId === song.id}
                onClick={() => void regenerate(song.id)}
              >
                {busyId === song.id ? "..." : "Yeniden"}
              </Button>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}
