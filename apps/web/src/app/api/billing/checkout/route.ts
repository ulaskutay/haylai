import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { isCreditsDisabled } from "@/lib/credits";
import { getCreditPack, initializeCheckout } from "@/lib/iyzico";

export async function POST(request: Request) {
  const user = await requireUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (isCreditsDisabled() || !process.env.IYZICO_API_KEY || !process.env.IYZICO_SECRET_KEY) {
    return NextResponse.json(
      { error: "Ödeme altyapısı henüz yapılandırılmadı" },
      { status: 503 },
    );
  }

  const { packId } = (await request.json()) as { packId?: string };
  const pack = packId ? getCreditPack(packId) : null;
  if (!pack) {
    return NextResponse.json({ error: "Geçersiz paket" }, { status: 400 });
  }

  const paymentId = crypto.randomUUID();
  const admin = createAdminClient();
  await admin.from("payments").insert({
    id: paymentId,
    user_id: user.id,
    conversation_id: paymentId,
    status: "pending",
    credits: pack.credits,
    amount_try: pack.amountTry,
  });

  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
  const name = user.email?.split("@")[0] ?? "HAYL";
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "127.0.0.1";

  const result = await initializeCheckout({
    conversationId: paymentId,
    price: pack.amountTry,
    paidPrice: pack.amountTry,
    basketId: pack.id,
    credits: pack.credits,
    packLabel: pack.label,
    callbackUrl: `${appUrl}/api/billing/callback`,
    buyer: {
      id: user.id,
      name,
      surname: "User",
      email: user.email ?? "user@hayl.ai",
      ip,
    },
  });

  if (result.status !== "success") {
    await admin
      .from("payments")
      .update({ status: "failed", raw_payload: result })
      .eq("id", paymentId);
    return NextResponse.json(
      { error: result.errorMessage ?? "iyzico başlatılamadı" },
      { status: 400 },
    );
  }

  await admin
    .from("payments")
    .update({ iyzico_token: result.token, raw_payload: result })
    .eq("id", paymentId);

  return NextResponse.json({
    paymentPageUrl: result.paymentPageUrl,
    token: result.token,
    checkoutFormContent: result.checkoutFormContent,
  });
}
