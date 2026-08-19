"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export function LoginForm() {
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/create";
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  async function magicLink(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const supabase = createClient();
    const origin = window.location.origin;
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${origin}/auth/callback?next=${encodeURIComponent(next)}`,
      },
    });
    setLoading(false);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success("Giriş bağlantısı e-postana gönderildi");
  }

  async function google() {
    const supabase = createClient();
    const origin = window.location.origin;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${origin}/auth/callback?next=${encodeURIComponent(next)}`,
      },
    });
    if (error) toast.error(error.message);
  }

  return (
    <div className="mx-auto w-full max-w-sm space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Giriş yap</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Google veya e-posta bağlantısı ile tek tıkla devam et.
        </p>
      </div>
      <Button className="w-full" variant="secondary" onClick={() => void google()}>
        Google ile devam et
      </Button>
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">veya</span>
        </div>
      </div>
      <form className="space-y-3" onSubmit={(e) => void magicLink(e)}>
        <div className="space-y-2">
          <Label htmlFor="email">E-posta</Label>
          <Input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="sen@mail.com"
          />
        </div>
        <Button className="w-full" type="submit" disabled={loading}>
          {loading ? "Gönderiliyor..." : "Magic link gönder"}
        </Button>
      </form>
    </div>
  );
}
