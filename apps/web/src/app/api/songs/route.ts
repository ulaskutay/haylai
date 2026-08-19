import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { startProcessing } from "@/lib/processing";
import { signedUrl } from "@/lib/storage";
import { isCreditsDisabled } from "@/lib/credits";
import { catalogByIdOrSlug } from "@/lib/instrumentals";
import { creditsForDuration, MAX_DURATION_SECONDS } from "@/lib/types";

export async function GET() {
  const user = await requireUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("songs")
    .select("id, genre, status, pipeline_step, duration_seconds, credits_charged, created_at, processed_path")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(50);

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ songs: data ?? [] });
}

export async function POST(request: Request) {
  const user = await requireUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = (await request.json()) as {
    durationSeconds?: number;
    instrumentalId?: string;
    originalPath?: string;
    contentType?: string;
  };

  const duration = Number(body.durationSeconds ?? 0);
  if (!body.instrumentalId || !body.originalPath) {
    return NextResponse.json({ error: "Eksik alanlar" }, { status: 400 });
  }
  if (!Number.isFinite(duration) || duration <= 0) {
    return NextResponse.json({ error: "Geçersiz süre" }, { status: 400 });
  }
  if (duration > MAX_DURATION_SECONDS) {
    return NextResponse.json(
      { error: `Kayıt en fazla ${MAX_DURATION_SECONDS} saniye olabilir` },
      { status: 400 },
    );
  }

  const admin = createAdminClient();
  let bed: {
    id: string;
    genre: string;
    storage_path: string;
  } | null = null;

  const looksLikeUuid = /^[0-9a-f-]{36}$/i.test(body.instrumentalId);

  if (looksLikeUuid) {
    const { data: dbBed } = await admin
      .from("instrumentals")
      .select("*")
      .eq("id", body.instrumentalId)
      .eq("is_active", true)
      .maybeSingle();
    if (dbBed) bed = dbBed;
  }

  if (!bed) {
    const catalog = catalogByIdOrSlug(body.instrumentalId);
    if (catalog) {
      const { data: upserted, error: upsertError } = await admin
        .from("instrumentals")
        .upsert(
          {
            slug: catalog.slug,
            title: catalog.title,
            genre: catalog.genre,
            bpm: catalog.bpm,
            key: catalog.key,
            storage_path: catalog.storage_path,
            preview_path: catalog.preview_path,
            is_active: true,
          },
          { onConflict: "slug" },
        )
        .select("*")
        .single();
      if (upsertError || !upserted) {
        bed = {
          id: catalog.id,
          genre: catalog.genre,
          storage_path: catalog.storage_path,
        };
      } else {
        bed = upserted;
      }
    }
  }

  if (!bed) {
    return NextResponse.json({ error: "Altyapı bulunamadı" }, { status: 404 });
  }

  const skipCredits = isCreditsDisabled();
  const amount = skipCredits ? 0 : creditsForDuration(duration);
  let remaining: number | null = null;

  if (!skipCredits) {
    const { data, error: creditError } = await admin.rpc("consume_credits", {
      p_user_id: user.id,
      p_amount: amount,
    });
    if (creditError) {
      const insufficient = creditError.message?.includes("INSUFFICIENT_CREDITS");
      return NextResponse.json(
        {
          error: insufficient ? "Yetersiz kredi" : creditError.message,
          code: insufficient ? "INSUFFICIENT_CREDITS" : "CREDIT_ERROR",
        },
        { status: insufficient ? 402 : 400 },
      );
    }
    remaining = typeof data === "number" ? data : null;
  }

  const songId = crypto.randomUUID();
  const instrumentalKey = String(bed.storage_path).replace(/^instrumentals\//, "");
  const processedPath = `${user.id}/${songId}.mp3`;

  const { error: insertError } = await admin.from("songs").insert({
    id: songId,
    user_id: user.id,
    original_path: body.originalPath,
    original_audio_url: signedUrl("originals", body.originalPath, {
      expiresInSec: 60 * 60 * 24,
    }),
    genre: bed.genre,
    instrumental_id: /^[0-9a-f-]{36}$/i.test(bed.id) ? bed.id : null,
    duration_seconds: duration,
    credits_charged: amount,
    status: "pending",
    pipeline_step: "analyzing",
  });

  if (insertError) {
    if (!skipCredits && amount) {
      await admin.rpc("add_credits", { p_user_id: user.id, p_amount: amount });
    }
    return NextResponse.json({ error: insertError.message }, { status: 500 });
  }

  try {
    await startProcessing({
      songId,
      originalPath: body.originalPath,
      processedPath,
      instrumentalPath: instrumentalKey,
      genre: bed.genre,
    });
  } catch (error) {
    if (!skipCredits && amount) {
      await admin.rpc("add_credits", { p_user_id: user.id, p_amount: amount });
    }
    await admin
      .from("songs")
      .update({
        status: "failed",
        error_message:
          error instanceof Error ? error.message : "İşlem başlatılamadı",
      })
      .eq("id", songId);
    return NextResponse.json(
      { error: "İşleme başlatılamadı" },
      { status: 500 },
    );
  }

  return NextResponse.json({
    id: songId,
    creditsCharged: amount,
    creditsRemaining: remaining,
  });
}
