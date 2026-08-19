import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { recoverStaleSong } from "@/lib/processing";
import { signedUrl } from "@/lib/storage";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const user = await requireUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("songs")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (error || !data) {
    return NextResponse.json({ error: "Şarkı bulunamadı" }, { status: 404 });
  }

  const recovered = await recoverStaleSong({
    id: data.id as string,
    status: data.status as string,
    processed_path: (data.processed_path as string | null) ?? null,
    updated_at: data.updated_at as string | undefined,
  });

  const song = { ...data, ...recovered };

  const processedUrl =
    song.status === "completed" && song.processed_path
      ? signedUrl("processed", song.processed_path as string, {
          expiresInSec: 60 * 60,
        })
      : (song.processed_audio_url as string | null);

  const originalUrl = song.original_path
    ? signedUrl("originals", song.original_path as string, {
        expiresInSec: 60 * 60,
      })
    : (song.original_audio_url as string | null);

  return NextResponse.json({
    song: {
      ...song,
      processed_audio_url: processedUrl,
      original_audio_url: originalUrl,
    },
  });
}
