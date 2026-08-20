import crypto from "crypto";

const RUNPOD_API = "https://api.runpod.ai/v2";

export function isRunPodConfigured() {
  const key = process.env.RUNPOD_API_KEY?.trim();
  const endpoint = process.env.RUNPOD_ENDPOINT_ID?.trim();
  return Boolean(key && endpoint);
}

export type WorkerJobInput = {
  song_id: string;
  original_url: string;
  instrumental_url: string;
  upload_url: string;
  genre: string;
  callback_url: string;
  callback_secret: string;
};

export async function submitRunPodJob(input: WorkerJobInput) {
  const key = process.env.RUNPOD_API_KEY;
  const endpoint = process.env.RUNPOD_ENDPOINT_ID;
  if (!key || !endpoint) {
    throw new Error("RunPod is not configured");
  }

  const res = await fetch(`${RUNPOD_API}/${endpoint}/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      input,
      webhook: input.callback_url || undefined,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`RunPod submit failed: ${res.status} ${text}`);
  }

  const json = (await res.json()) as { id?: string };
  return json.id ?? null;
}

export async function getRunPodStatus(jobId: string) {
  const key = process.env.RUNPOD_API_KEY;
  const endpoint = process.env.RUNPOD_ENDPOINT_ID;
  if (!key || !endpoint) {
    throw new Error("RunPod is not configured");
  }

  const res = await fetch(`${RUNPOD_API}/${endpoint}/status/${jobId}`, {
    headers: { Authorization: `Bearer ${key}` },
  });

  if (!res.ok) {
    throw new Error(`RunPod status failed: ${res.status}`);
  }

  return res.json() as Promise<{ status: string; output?: unknown }>;
}

export function signCallbackBody(body: string, secret: string) {
  return crypto.createHmac("sha256", secret).update(body).digest("hex");
}

export function verifyCallbackSignature(
  body: string,
  signature: string | null,
  secret: string,
) {
  if (!signature) return false;
  const expected = signCallbackBody(body, secret);
  try {
    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expected),
    );
  } catch {
    return false;
  }
}
