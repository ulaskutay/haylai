import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { verifyCallbackSignature } from "@/lib/runpod";
import { signedUrl } from "@/lib/storage";
import type { PipelineStep } from "@/lib/types";

type HaylPayload = {
  song_id: string;
  status: "processing" | "completed" | "failed";
  pipeline_step?: PipelineStep;
  processed_path?: string;
  error_message?: string;
};

async function applyHaylPayload(payload: HaylPayload) {
  const admin = createAdminClient();
  const { data: song } = await admin
    .from("songs")
    .select("id, user_id, credits_charged, status, processed_path")
    .eq("id", payload.song_id)
    .single();

  if (!song) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  if (payload.status === "failed") {
    if (song.status !== "failed" && song.credits_charged) {
      await admin.rpc("add_credits", {
        p_user_id: song.user_id,
        p_amount: song.credits_charged,
      });
    }
    await admin
      .from("songs")
      .update({
        status: "failed",
        error_message: payload.error_message ?? "Worker failed",
        pipeline_step: payload.pipeline_step ?? null,
      })
      .eq("id", payload.song_id);
    return NextResponse.json({ ok: true });
  }

  let processedUrl: string | null = null;
  if (payload.status === "completed") {
    const key = payload.processed_path ?? song.processed_path;
    if (key) {
      processedUrl = signedUrl("processed", key, {
        expiresInSec: 60 * 60 * 24,
      });
    }
  }

  await admin
    .from("songs")
    .update({
      status: payload.status,
      pipeline_step: payload.pipeline_step ?? null,
      processed_path: payload.processed_path ?? undefined,
      processed_audio_url: processedUrl,
      error_message: null,
    })
    .eq("id", payload.song_id);

  return NextResponse.json({ ok: true });
}

export async function POST(request: Request) {
  const secret = process.env.WORKER_CALLBACK_SECRET;
  const raw = await request.text();
  const signature = request.headers.get("x-hayl-signature");

  if (signature) {
    if (!secret || !verifyCallbackSignature(raw, signature, secret)) {
      return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
    }
    const payload = JSON.parse(raw) as HaylPayload;
    if (!payload.song_id) {
      return NextResponse.json({ error: "Missing song_id" }, { status: 400 });
    }
    return applyHaylPayload(payload);
  }

  const native = JSON.parse(raw) as {
    id?: string;
    status?: string;
    output?: { ok?: boolean; song_id?: string; error?: string };
    input?: { song_id?: string };
  };

  const jobId = native.id;
  if (!jobId) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  const admin = createAdminClient();
  const { data: song } = await admin
    .from("songs")
    .select("id, processed_path, status")
    .eq("runpod_job_id", jobId)
    .single();

  if (!song) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const failed = ["FAILED", "CANCELLED", "TIMED_OUT"].includes(
    String(native.status ?? "").toUpperCase(),
  );
  const outputFailed = native.output?.ok === false;

  if (failed || outputFailed) {
    return applyHaylPayload({
      song_id: song.id,
      status: "failed",
      error_message:
        native.output?.error ?? `RunPod ${native.status ?? "failed"}`,
    });
  }

  if (String(native.status ?? "").toUpperCase() === "COMPLETED") {
    return applyHaylPayload({
      song_id: song.id,
      status: "completed",
      pipeline_step: "export",
      processed_path: song.processed_path ?? undefined,
    });
  }

  return NextResponse.json({ ok: true, ignored: native.status });
}
