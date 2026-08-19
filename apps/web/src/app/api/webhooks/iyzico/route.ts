import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { retrieveCheckout } from "@/lib/iyzico";

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

  const result = await retrieveCheckout(token);
  if (result.status !== "success" || result.paymentStatus !== "SUCCESS") {
    return NextResponse.json({ ok: false }, { status: 400 });
  }

  const admin = createAdminClient();
  const { data: payment } = await admin
    .from("payments")
    .select("*")
    .eq("iyzico_token", token)
    .maybeSingle();

  if (!payment) {
    return NextResponse.json({ error: "Payment not found" }, { status: 404 });
  }

  if (payment.status !== "paid") {
    await admin.rpc("add_credits", {
      p_user_id: payment.user_id,
      p_amount: payment.credits,
    });
    await admin
      .from("payments")
      .update({ status: "paid", raw_payload: result })
      .eq("id", payment.id);
  }

  return NextResponse.json({ ok: true });
}
