import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { INSTRUMENTAL_CATALOG } from "@/lib/instrumentals";
import { signedUrl } from "@/lib/storage";

export async function GET() {
  try {
    const supabase = await createClient();
    const { data, error } = await supabase
      .from("instrumentals")
      .select("*")
      .eq("is_active", true)
      .order("genre");

    if (!error && data?.length) {
      const fromDb = data.map((bed) => {
        const key = String(bed.preview_path ?? bed.storage_path).replace(
          /^instrumentals\//,
          "",
        );
        return {
          ...bed,
          preview_url: signedUrl("instrumentals", key, { expiresInSec: 60 * 10 }),
        };
      });
      const have = new Set(fromDb.map((bed) => String(bed.slug)));
      const extra = INSTRUMENTAL_CATALOG.filter((bed) => !have.has(bed.slug)).map(
        (bed) => ({
          ...bed,
          preview_url: signedUrl("instrumentals", bed.storage_path, {
            expiresInSec: 60 * 10,
          }),
        }),
      );
      return NextResponse.json({ instrumentals: [...fromDb, ...extra] });
    }
  } catch {
    // Supabase not configured — local demo beds.
  }

  const instrumentals = INSTRUMENTAL_CATALOG.map((bed) => ({
    ...bed,
    preview_url: signedUrl("instrumentals", bed.storage_path, {
      expiresInSec: 60 * 10,
    }),
  }));
  return NextResponse.json({ instrumentals });
}
