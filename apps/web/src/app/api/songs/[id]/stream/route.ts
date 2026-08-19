import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { getObject, sniffMime } from "@/lib/storage";

async function processedFile(id: string, userId: string) {
  const admin = createAdminClient();
  const { data: song } = await admin
    .from("songs")
    .select("processed_path, status, user_id")
    .eq("id", id)
    .single();

  if (!song || song.user_id !== userId || song.status !== "completed" || !song.processed_path) {
    return null;
  }

  const data = await getObject("processed", song.processed_path);
  const mime = sniffMime(data, song.processed_path);
  return { data, mime };
}

export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const user = await requireUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const file = await processedFile(id, user.id);
    if (!file) {
      return NextResponse.json({ error: "İndirme hazır değil" }, { status: 404 });
    }

    const download = new URL(request.url).searchParams.get("download");
    const ext = file.mime.includes("webm")
      ? "webm"
      : file.mime.includes("wav")
        ? "wav"
        : file.mime.includes("mp4")
          ? "m4a"
          : "mp3";
    const headers: Record<string, string> = {
      "Content-Type": file.mime,
      "Cache-Control": "no-store",
    };
    if (download) {
      headers["Content-Disposition"] = `attachment; filename="hayl-${id}.${ext}"`;
    }
    return new NextResponse(new Uint8Array(file.data), { headers });
  } catch {
    return NextResponse.json({ error: "Dosya okunamadı" }, { status: 404 });
  }
}
