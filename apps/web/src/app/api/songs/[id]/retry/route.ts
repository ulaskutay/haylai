import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { isCreditsDisabled } from "@/lib/credits";
import { normalizeInstruments } from "@/lib/arrangement";
import { catalogByIdOrSlug, INSTRUMENTAL_CATALOG } from "@/lib/instrumentals";
import { startProcessing } from "@/lib/processing";

export async function POST(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const user = await requireUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const admin = createAdminClient();
  const { data: song } = await admin
    .from("songs")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (!song || !["failed", "completed"].includes(song.status as string)) {
    return NextResponse.json(
      { error: "Bu şarkı şu an yeniden oluşturulamaz" },
      { status: 400 },
    );
  }

  const skipCredits = isCreditsDisabled();
  const amount = song.credits_charged as number;
  if (!skipCredits && amount && song.status === "failed") {
    const { error: creditError } = await admin.rpc("consume_credits", {
      p_user_id: user.id,
      p_amount: amount,
    });
    if (creditError) {
      return NextResponse.json({ error: "Yetersiz kredi" }, { status: 402 });
    }
  }

  let bed: { storage_path: string; genre: string } | null = null;
  if (song.instrumental_id) {
    const { data } = await admin
      .from("instrumentals")
      .select("storage_path, genre")
      .eq("id", song.instrumental_id)
      .maybeSingle();
    bed = data;
  }

  if (!bed) {
    const catalog =
      INSTRUMENTAL_CATALOG.find((item) => item.genre === song.genre) ??
      catalogByIdOrSlug(String(song.instrumental_id ?? ""));
    if (catalog) {
      bed = { storage_path: catalog.storage_path, genre: catalog.genre };
    }
  }

  if (!bed || !song.original_path) {
    if (!skipCredits && amount && song.status === "failed") {
      await admin.rpc("add_credits", { p_user_id: user.id, p_amount: amount });
    }
    return NextResponse.json({ error: "Eksik kaynak" }, { status: 400 });
  }

  const genre = (song.genre as string) || bed.genre;
  const processedPath = `${user.id}/${id}.mp3`;

  await admin
    .from("songs")
    .update({
      status: "pending",
      error_message: null,
      pipeline_step: "analyzing",
      processed_path: processedPath,
      processed_audio_url: null,
      runpod_job_id: null,
    })
    .eq("id", id);

  await startProcessing({
    songId: id,
    originalPath: song.original_path,
    processedPath,
    instrumentalPath: String(bed.storage_path).replace(/^instrumentals\//, ""),
    genre,
    instruments: normalizeInstruments(song.instruments, genre),
    rhythm: "follow",
    bpm: 0,
  });

  return NextResponse.json({ ok: true });
}
