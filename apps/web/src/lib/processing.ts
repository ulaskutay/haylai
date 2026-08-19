import { after } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { ffmpegAvailable, mixVocalAndBed } from "@/lib/ffmpeg-mix";
import {
  getRunPodStatus,
  isRunPodConfigured,
  submitRunPodJob,
  type WorkerJobInput,
} from "@/lib/runpod";
import { getObject, putObject, signedUrl } from "@/lib/storage";
import type { PipelineStep } from "@/lib/types";

const STEPS: PipelineStep[] = [
  "analyzing",
  "cleaning",
  "pitch",
  "rvc",
  "mix",
  "export",
];

export async function buildWorkerInput(params: {
  songId: string;
  originalPath: string;
  processedPath: string;
  instrumentalPath: string;
  genre: string;
  localDisk?: boolean;
}): Promise<WorkerJobInput> {
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

  if (params.localDisk) {
    return {
      song_id: params.songId,
      original_url: `local://originals/${params.originalPath}`,
      instrumental_url: `local://instrumentals/${params.instrumentalPath}`,
      upload_url: `local://processed/${params.processedPath}`,
      genre: params.genre,
      callback_url: `${appUrl}/api/webhooks/runpod`,
      callback_secret: process.env.WORKER_CALLBACK_SECRET ?? "",
    };
  }

  return {
    song_id: params.songId,
    original_url: signedUrl("originals", params.originalPath, {
      expiresInSec: 60 * 60,
      absolute: true,
    }),
    instrumental_url: signedUrl("instrumentals", params.instrumentalPath, {
      expiresInSec: 60 * 60,
      absolute: true,
    }),
    upload_url: signedUrl("processed", params.processedPath, {
      method: "PUT",
      expiresInSec: 60 * 60,
      absolute: true,
    }),
    genre: params.genre,
    callback_url: `${appUrl}/api/webhooks/runpod`,
    callback_secret: process.env.WORKER_CALLBACK_SECRET ?? "",
  };
}

async function localWorkerUp() {
  const workerUrl = process.env.WORKER_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${workerUrl}/health`, {
      signal: AbortSignal.timeout(800),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function resolveProcessMode() {
  const configured = process.env.PROCESS_MODE ?? "auto";
  if (configured === "auto") {
    if (isRunPodConfigured()) return "runpod";
    if (await localWorkerUp()) return "local";
    return "mock";
  }
  return configured;
}

async function simulatePipeline(
  songId: string,
  processedPath: string,
  instrumentalPath: string,
) {
  const admin = createAdminClient();
  try {
    for (const step of STEPS) {
      await admin
        .from("songs")
        .update({ status: "processing", pipeline_step: step })
        .eq("id", songId);
      await new Promise((r) => setTimeout(r, 900));
    }

    const { data: song } = await admin
      .from("songs")
      .select("original_path, user_id")
      .eq("id", songId)
      .single();

    if (!song?.original_path) {
      throw new Error("Orijinal kayıt bulunamadı");
    }

    const original = await getObject("originals", song.original_path);
    let output = original;
    try {
      const bed = await getObject("instrumentals", instrumentalPath);
      if (await ffmpegAvailable()) {
        const ext = song.original_path.split(".").pop() ?? "webm";
        output = await mixVocalAndBed(original, bed, ext);
      }
    } catch {
      output = original;
    }

    await putObject("processed", processedPath, output);

    await admin
      .from("songs")
      .update({
        status: "completed",
        pipeline_step: "export",
        processed_path: processedPath,
        processed_audio_url: signedUrl("processed", processedPath, {
          expiresInSec: 60 * 60 * 24,
        }),
      })
      .eq("id", songId);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Pipeline failed";
    const { data: song } = await admin
      .from("songs")
      .select("user_id, credits_charged")
      .eq("id", songId)
      .single();
    if (song?.credits_charged) {
      await admin.rpc("add_credits", {
        p_user_id: song.user_id,
        p_amount: song.credits_charged,
      });
    }
    await admin
      .from("songs")
      .update({ status: "failed", error_message: message })
      .eq("id", songId);
  }
}

async function markComplete(songId: string, processedPath: string) {
  const admin = createAdminClient();
  await admin
    .from("songs")
    .update({
      status: "completed",
      pipeline_step: "export",
      processed_path: processedPath,
      processed_audio_url: signedUrl("processed", processedPath, {
        expiresInSec: 60 * 60 * 24,
      }),
      error_message: null,
    })
    .eq("id", songId);
}

async function runLocalWorkerJob(
  songId: string,
  processedPath: string,
  workerUrl: string,
  input: WorkerJobInput,
) {
  try {
    const res = await fetch(`${workerUrl}/jobs/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      signal: AbortSignal.timeout(180_000),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text.slice(0, 400) || `Worker ${res.status}`);
    }
    await getObject("processed", processedPath);
    await markComplete(songId, processedPath);
  } catch (error) {
    try {
      await getObject("processed", processedPath);
      await markComplete(songId, processedPath);
      return;
    } catch {
      const message =
        error instanceof Error ? error.message : "Lokal worker başarısız";
      await failSong(songId, message);
    }
  }
}

export async function recoverStaleSong(song: {
  id: string;
  status: string;
  processed_path: string | null;
  updated_at?: string;
}) {
  if (song.status !== "processing" && song.status !== "pending") return song;
  const updated = song.updated_at ? Date.parse(song.updated_at) : 0;
  const stale = !updated || Date.now() - updated > 4 * 60 * 1000;
  if (song.processed_path) {
    try {
      await getObject("processed", song.processed_path);
      await markComplete(song.id, song.processed_path);
      return { ...song, status: "completed", pipeline_step: "export" };
    } catch {
      // file not ready
    }
  }
  if (stale) {
    await failSong(
      song.id,
      "İşlem takıldı (worker kayda 403 aldı). Yeniden dene — artık disk üzerinden okunacak.",
    );
    return { ...song, status: "failed" };
  }
  return song;
}

async function failSong(songId: string, message: string) {
  const admin = createAdminClient();
  const { data: song } = await admin
    .from("songs")
    .select("user_id, credits_charged, status")
    .eq("id", songId)
    .single();
  if (song?.status === "completed") return;
  if (song?.status !== "failed" && song?.credits_charged) {
    await admin.rpc("add_credits", {
      p_user_id: song.user_id,
      p_amount: song.credits_charged,
    });
  }
  await admin
    .from("songs")
    .update({ status: "failed", error_message: message })
    .eq("id", songId);
}

async function watchRunPodJob(songId: string, jobId: string, processedPath: string) {
  const admin = createAdminClient();
  const deadline = Date.now() + 15 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 5000));
    const { data: current } = await admin
      .from("songs")
      .select("status")
      .eq("id", songId)
      .single();
    if (current?.status === "completed" || current?.status === "failed") {
      return;
    }
    let status: { status: string; output?: unknown };
    try {
      status = await getRunPodStatus(jobId);
    } catch {
      continue;
    }
    const code = String(status.status ?? "").toUpperCase();
    const output = status.output as
      | { ok?: boolean; error?: string }
      | undefined;
    if (code === "FAILED" || code === "CANCELLED" || code === "TIMED_OUT" || output?.ok === false) {
      await failSong(songId, output?.error ?? `RunPod ${code || "failed"}`);
      return;
    }
    if (code === "COMPLETED") {
      try {
        await getObject("processed", processedPath);
        await admin
          .from("songs")
          .update({
            status: "completed",
            pipeline_step: "export",
            processed_path: processedPath,
            processed_audio_url: signedUrl("processed", processedPath, {
              expiresInSec: 60 * 60 * 24,
            }),
            error_message: null,
          })
          .eq("id", songId);
      } catch {
        await failSong(songId, "RunPod bitti ama işlenmiş dosya yok");
      }
      return;
    }
  }
  await failSong(songId, "RunPod zaman aşımı (cold start + iş > 15 dk)");
}

export async function startProcessing(params: {
  songId: string;
  originalPath: string;
  processedPath: string;
  instrumentalPath: string;
  genre: string;
}) {
  const mode = await resolveProcessMode();
  const admin = createAdminClient();

  await admin
    .from("songs")
    .update({
      status: "processing",
      pipeline_step: "analyzing",
      processed_path: params.processedPath,
    })
    .eq("id", params.songId);

  if (mode === "mock") {
    after(() =>
      simulatePipeline(
        params.songId,
        params.processedPath,
        params.instrumentalPath,
      ),
    );
    return { mode, jobId: null };
  }

  const input = await buildWorkerInput({
    ...params,
    localDisk: mode === "local",
  });

  if (mode === "local") {
    const workerUrl = process.env.WORKER_URL ?? "http://localhost:8000";
    after(() => runLocalWorkerJob(params.songId, params.processedPath, workerUrl, input));
    return { mode, jobId: null };
  }

  if (mode === "runpod") {
    try {
      const jobId = await submitRunPodJob(input);
      await admin
        .from("songs")
        .update({ runpod_job_id: jobId })
        .eq("id", params.songId);
      if (jobId) {
        after(() => watchRunPodJob(params.songId, jobId, params.processedPath));
      }
      return { mode, jobId };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "RunPod işi gönderilemedi";
      await failSong(params.songId, message);
      return { mode, jobId: null };
    }
  }

  await failSong(params.songId, `Bilinmeyen PROCESS_MODE: ${mode}`);
  return { mode, jobId: null };
}
