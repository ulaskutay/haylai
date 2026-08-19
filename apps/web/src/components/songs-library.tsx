"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Song } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  pending: "Kuyrukta",
  processing: "İşleniyor",
  completed: "Hazır",
  failed: "Hata",
};

export function SongsLibrary() {
  const [songs, setSongs] = useState<Song[]>([]);
  const [loading, setLoading] = useState(true);

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
          <Link
            href={`/songs/${song.id}`}
            className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-3 hover:border-primary/50"
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
        </li>
      ))}
    </ul>
  );
}
