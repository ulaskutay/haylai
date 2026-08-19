import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth";
import { createAdminClient } from "@/lib/supabase/admin";

export async function GET() {
  const user = await requireUser();
  if (!user) {
    return NextResponse.json({ user: null, credits: 0 }, { status: 401 });
  }

  const admin = createAdminClient();
  const { data: profile } = await admin
    .from("users")
    .select("credits_remaining, email")
    .eq("id", user.id)
    .single();

  return NextResponse.json({
    user: { id: user.id, email: user.email ?? profile?.email },
    credits: profile?.credits_remaining ?? 0,
  });
}
