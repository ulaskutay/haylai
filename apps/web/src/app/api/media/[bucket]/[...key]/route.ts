import { NextResponse } from "next/server";
import {
  getObject,
  isBucket,
  putObject,
  sanitizeKey,
  sniffMime,
  verifySignature,
} from "@/lib/storage";

export const runtime = "nodejs";

function downloadName(key: string, mime: string) {
  if (mime.includes("webm")) return key.replace(/\.[^.]+$/, ".webm");
  if (mime.includes("wav")) return key.replace(/\.[^.]+$/, ".wav");
  if (mime.includes("mp4")) return key.replace(/\.[^.]+$/, ".m4a");
  return key;
}

export async function GET(
  request: Request,
  context: { params: Promise<{ bucket: string; key: string[] }> },
) {
  const { bucket, key: parts } = await context.params;
  if (!isBucket(bucket)) {
    return NextResponse.json({ error: "Unknown bucket" }, { status: 404 });
  }

  const url = new URL(request.url);
  const exp = url.searchParams.get("exp");
  const sig = url.searchParams.get("sig");
  const method = url.searchParams.get("method") ?? "GET";
  const key = sanitizeKey(parts.join("/"));

  if (!exp || !sig || method !== "GET") {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }
  if (Number(exp) < Math.floor(Date.now() / 1000)) {
    return NextResponse.json({ error: "URL expired" }, { status: 401 });
  }
  if (!verifySignature(`GET:${bucket}:${key}:${exp}`, sig)) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  try {
    const data = await getObject(bucket, key);
    const mime = sniffMime(data, key);
    const download = url.searchParams.get("download");
    const headers: Record<string, string> = {
      "Content-Type": mime,
      "Cache-Control": "private, max-age=60",
    };
    if (download) {
      headers["Content-Disposition"] =
        `attachment; filename="${downloadName(download, mime)}"`;
    }
    return new NextResponse(new Uint8Array(data), { headers });
  } catch {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
}

export async function PUT(
  request: Request,
  context: { params: Promise<{ bucket: string; key: string[] }> },
) {
  const { bucket, key: parts } = await context.params;
  if (!isBucket(bucket)) {
    return NextResponse.json({ error: "Unknown bucket" }, { status: 404 });
  }

  const url = new URL(request.url);
  const exp = url.searchParams.get("exp");
  const sig = url.searchParams.get("sig");
  const method = url.searchParams.get("method") ?? "PUT";
  const key = sanitizeKey(parts.join("/"));

  if (!exp || !sig || method !== "PUT") {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }
  if (Number(exp) < Math.floor(Date.now() / 1000)) {
    return NextResponse.json({ error: "URL expired" }, { status: 401 });
  }
  if (!verifySignature(`PUT:${bucket}:${key}:${exp}`, sig)) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  const buf = Buffer.from(await request.arrayBuffer());
  await putObject(bucket, key, buf);
  return NextResponse.json({ ok: true, path: key });
}
