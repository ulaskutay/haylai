import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { retrieveCheckout } from "@/lib/iyzico";

async function fulfill(token: string) {
  const result = await retrieveCheckout(token);
  if (result.status !== "success" || result.paymentStatus !== "SUCCESS") {
    return { ok: false as const, result };
  }

  const admin = createAdminClient();
  const { data: payment } = await admin
    .from("payments")
    .select("*")
    .or(`iyzico_token.eq.${token},conversation_id.eq.${result.conversationId}`)
    .maybeSingle();

  if (!payment) {
    return { ok: false as const, result };
  }

  if (payment.status === "paid") {
    return { ok: true as const, result };
  }

  await admin.rpc("add_credits", {
    p_user_id: payment.user_id,
    p_amount: payment.credits,
  });
  await admin
    .from("payments")
    .update({ status: "paid", raw_payload: result, iyzico_token: token })
    .eq("id", payment.id);

  return { ok: true as const, result };
}

export async function POST(request: Request) {
  const contentType = request.headers.get("content-type") ?? "";
  let token = "";

  if (contentType.includes("application/json")) {
    const body = (await request.json()) as { token?: string };
    token = body.token ?? "";
  } else {
    const form = await request.formData();
    token = String(form.get("token") ?? "");
  }

  if (!token) {
    return NextResponse.json({ error: "Missing token" }, { status: 400 });
  }

  const outcome = await fulfill(token);
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
  if (request.headers.get("accept")?.includes("text/html") || contentType.includes("form")) {
    return NextResponse.redirect(
      `${appUrl}/create?billing=${outcome.ok ? "success" : "failed"}`,
    );
  }
  return NextResponse.json({ ok: outcome.ok });
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const token = url.searchParams.get("token");
  if (!token) {
    return NextResponse.json({ error: "Missing token" }, { status: 400 });
  }
  const outcome = await fulfill(token);
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
  return NextResponse.redirect(
    `${appUrl}/create?billing=${outcome.ok ? "success" : "failed"}`,
  );
}
