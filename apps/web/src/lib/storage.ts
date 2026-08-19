import { createHmac, timingSafeEqual } from "crypto";
import { mkdir, readFile, writeFile } from "fs/promises";
import path from "path";

export const BUCKETS = ["originals", "processed", "instrumentals"] as const;
export type Bucket = (typeof BUCKETS)[number];

export function isBucket(value: string): value is Bucket {
  return (BUCKETS as readonly string[]).includes(value);
}

export function storageRoot() {
  if (process.env.STORAGE_ROOT) {
    return path.resolve(process.env.STORAGE_ROOT);
  }
  const cwd = process.cwd();
  if (path.basename(cwd) === "web") {
    return path.resolve(cwd, "../../data/audio");
  }
  return path.resolve(cwd, "data/audio");
}

export function sanitizeKey(key: string) {
  const normalized = key.replace(/^\/+/, "").replace(/\\/g, "/");
  if (!normalized || normalized.includes("..")) {
    throw new Error("Invalid storage key");
  }
  return normalized;
}

function diskPath(bucket: Bucket, key: string) {
  return path.join(storageRoot(), bucket, sanitizeKey(key));
}

function signingSecret() {
  return (
    process.env.STORAGE_SIGNING_SECRET ||
    process.env.WORKER_CALLBACK_SECRET ||
    "dev-storage-secret"
  );
}

function sign(message: string) {
  return createHmac("sha256", signingSecret()).update(message).digest("hex");
}

export function verifySignature(message: string, signature: string) {
  const expected = sign(message);
  try {
    return timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
  } catch {
    return false;
  }
}

export async function putObject(
  bucket: Bucket,
  key: string,
  data: Buffer,
) {
  const filePath = diskPath(bucket, key);
  await mkdir(path.dirname(filePath), { recursive: true });
  await writeFile(filePath, data);
  return sanitizeKey(key);
}

export async function getObject(bucket: Bucket, key: string) {
  return readFile(diskPath(bucket, key));
}

export function signedUrl(
  bucket: Bucket,
  key: string,
  options: {
    method?: "GET" | "PUT";
    expiresInSec?: number;
    download?: string;
    absolute?: boolean;
  } = {},
) {
  const method = options.method ?? "GET";
  const expiresInSec = options.expiresInSec ?? 60 * 60;
  const exp = Math.floor(Date.now() / 1000) + expiresInSec;
  const safeKey = sanitizeKey(key);
  const message = `${method}:${bucket}:${safeKey}:${exp}`;
  const sig = sign(message);
  const params = new URLSearchParams({
    exp: String(exp),
    sig,
    method,
  });
  if (options.download) params.set("download", options.download);
  const path = `/api/media/${bucket}/${safeKey}?${params.toString()}`;
  if (options.absolute) {
    return new URL(path, process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000").toString();
  }
  return path;
}

export function sniffMime(data: Buffer, key: string) {
  if (data.length >= 4) {
    if (data[0] === 0x1a && data[1] === 0x45) return "audio/webm";
    if (data.toString("ascii", 0, 4) === "RIFF") return "audio/wav";
    if (data.toString("ascii", 4, 8) === "ftyp") return "audio/mp4";
    if (data[0] === 0xff && (data[1] & 0xe0) === 0xe0) return "audio/mpeg";
    if (data.toString("ascii", 0, 3) === "ID3") return "audio/mpeg";
    if (data.toString("ascii", 0, 4) === "OggS") return "audio/ogg";
  }
  if (key.endsWith(".mp3")) return "audio/mpeg";
  if (key.endsWith(".wav")) return "audio/wav";
  if (key.endsWith(".m4a") || key.endsWith(".mp4")) return "audio/mp4";
  if (key.endsWith(".webm")) return "audio/webm";
  if (key.endsWith(".ogg")) return "audio/ogg";
  return "application/octet-stream";
}

export function publicMediaPath(bucket: Bucket, key: string) {
  return signedUrl(bucket, sanitizeKey(key), { expiresInSec: 60 * 60 });
}

export function storageDriver() {
  return process.env.STORAGE_DRIVER ?? "local";
}

