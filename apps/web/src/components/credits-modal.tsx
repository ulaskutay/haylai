"use client";

import { CREDIT_PACKS } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { useState } from "react";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function CreditsModal({ open, onOpenChange }: Props) {
  const [loading, setLoading] = useState<string | null>(null);

  async function buy(packId: string) {
    setLoading(packId);
    try {
      const res = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ packId }),
      });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.error ?? "Ödeme başlatılamadı");
      }
      if (json.paymentPageUrl) {
        window.location.assign(json.paymentPageUrl);
        return;
      }
      toast.error("Ödeme sayfası alınamadı");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Ödeme hatası");
    } finally {
      setLoading(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Kredi satın al</DialogTitle>
          <DialogDescription>
            Şarkı uzunluğuna göre kredi düşülür. 0–30 sn = 1 kredi.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          {CREDIT_PACKS.map((pack) => (
            <div
              key={pack.id}
              className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-3"
            >
              <div>
                <p className="font-medium">{pack.label}</p>
                <p className="text-sm text-muted-foreground">
                  {pack.credits} kredi · ₺{pack.amountTry}
                </p>
              </div>
              <Button
                size="sm"
                disabled={loading === pack.id}
                onClick={() => buy(pack.id)}
              >
                {loading === pack.id ? "Yönlendiriliyor..." : "Satın al"}
              </Button>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
