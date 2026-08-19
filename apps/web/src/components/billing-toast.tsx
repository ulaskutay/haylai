"use client";

import { useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

export function BillingToast() {
  const params = useSearchParams();

  useEffect(() => {
    const billing = params.get("billing");
    if (billing === "success") toast.success("Ödeme alındı, kredilerin yüklendi.");
    if (billing === "failed") toast.error("Ödeme tamamlanamadı.");
  }, [params]);

  return null;
}
