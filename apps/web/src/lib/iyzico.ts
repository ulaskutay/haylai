import crypto from "crypto";
import { CREDIT_PACKS } from "@/lib/types";

type IyzicoInitResult = {
  status: string;
  paymentPageUrl?: string;
  token?: string;
  errorMessage?: string;
  checkoutFormContent?: string;
};

function authHeaders(uriPath: string, body: string) {
  const apiKey = process.env.IYZICO_API_KEY!;
  const secret = process.env.IYZICO_SECRET_KEY!;
  const randomKey = crypto.randomBytes(16).toString("hex");
  const payload = randomKey + uriPath + body;
  const signature = crypto
    .createHmac("sha256", secret)
    .update(payload)
    .digest("hex");
  const authorization = `IYZWSv2 ${Buffer.from(
    `apiKey:${apiKey}&randomKey:${randomKey}&signature:${signature}`,
  ).toString("base64")}`;

  return {
    Authorization: authorization,
    "x-iyzi-rnd": randomKey,
    "Content-Type": "application/json",
  };
}

export function getCreditPack(id: string) {
  return CREDIT_PACKS.find((pack) => pack.id === id) ?? null;
}

export async function initializeCheckout(params: {
  conversationId: string;
  price: number;
  paidPrice: number;
  basketId: string;
  credits: number;
  packLabel: string;
  buyer: {
    id: string;
    name: string;
    surname: string;
    email: string;
    ip: string;
  };
  callbackUrl: string;
}) {
  const base = process.env.IYZICO_BASE_URL ?? "https://sandbox-api.iyzipay.com";
  const uriPath = "/payment/iyzipos/checkoutform/initialize/auth/ecom";
  const price = params.price.toFixed(2);

  const payload = {
    locale: "tr",
    conversationId: params.conversationId,
    price,
    paidPrice: params.paidPrice.toFixed(2),
    currency: "TRY",
    basketId: params.basketId,
    paymentGroup: "PRODUCT",
    callbackUrl: params.callbackUrl,
    enabledInstallments: [1],
    buyer: {
      id: params.buyer.id,
      name: params.buyer.name,
      surname: params.buyer.surname,
      gsmNumber: "+905555555555",
      email: params.buyer.email,
      identityNumber: "11111111111",
      lastLoginDate: "2024-01-01 12:00:00",
      registrationDate: "2024-01-01 12:00:00",
      registrationAddress: "Nidakule Goztepe, Merdivenli Sk.",
      ip: params.buyer.ip,
      city: "Istanbul",
      country: "Turkey",
      zipCode: "34742",
    },
    shippingAddress: {
      contactName: `${params.buyer.name} ${params.buyer.surname}`,
      city: "Istanbul",
      country: "Turkey",
      address: "Nidakule Goztepe, Merdivenli Sk.",
      zipCode: "34742",
    },
    billingAddress: {
      contactName: `${params.buyer.name} ${params.buyer.surname}`,
      city: "Istanbul",
      country: "Turkey",
      address: "Nidakule Goztepe, Merdivenli Sk.",
      zipCode: "34742",
    },
    basketItems: [
      {
        id: params.basketId,
        name: `${params.credits} HAYL kredi (${params.packLabel})`,
        category1: "Credits",
        itemType: "VIRTUAL",
        price,
      },
    ],
  };

  const body = JSON.stringify(payload);
  const res = await fetch(`${base}${uriPath}`, {
    method: "POST",
    headers: authHeaders(uriPath, body),
    body,
  });

  return (await res.json()) as IyzicoInitResult;
}

export async function retrieveCheckout(token: string) {
  const base = process.env.IYZICO_BASE_URL ?? "https://sandbox-api.iyzipay.com";
  const uriPath = "/payment/iyzipos/checkoutform/auth/ecom/detail";
  const body = JSON.stringify({ locale: "tr", token });
  const res = await fetch(`${base}${uriPath}`, {
    method: "POST",
    headers: authHeaders(uriPath, body),
    body,
  });
  return (await res.json()) as {
    status: string;
    paymentStatus?: string;
    conversationId?: string;
    token?: string;
    errorMessage?: string;
  };
}
