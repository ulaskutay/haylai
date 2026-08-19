import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth";
import { putObject } from "@/lib/storage";
import { MAX_UPLOAD_BYTES } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  const user = await requireUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const form = await request.formData();
  const file = form.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "Dosya yok" }, { status: 400 });
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return NextResponse.json({ error: "Dosya 20 MB sınırını aşıyor" }, { status: 400 });
  }

  const filename = file.name.replace(/[^\w.\-]+/g, "_");
  const ext = filename.includes(".") ? filename.split(".").pop() : "webm";
  const path = `${user.id}/${crypto.randomUUID()}.${ext}`;
  const bytes = Buffer.from(await file.arrayBuffer());
  await putObject("originals", path, bytes);

  return NextResponse.json({ path, maxBytes: MAX_UPLOAD_BYTES });
}
