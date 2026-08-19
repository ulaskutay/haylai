import { notFound } from "next/navigation";
import { requireUser } from "@/lib/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { SongWorkspace } from "@/components/song-workspace";
import type { Song } from "@/lib/types";

export default async function SongPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const user = await requireUser();
  if (!user) notFound();

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("songs")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (error || !data) notFound();

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <SongWorkspace initial={data as Song} />
    </div>
  );
}
