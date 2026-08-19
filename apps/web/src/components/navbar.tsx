"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AudioLines, Coins, LogOut } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { CreditsModal } from "@/components/credits-modal";
import { isCreditsUiDisabled } from "@/lib/credits";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";

const authEnabled = process.env.NEXT_PUBLIC_AUTH_DISABLED === "false";
const creditsEnabled = !isCreditsUiDisabled();

export function Navbar() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [credits, setCredits] = useState<number | null>(null);
  const [buyOpen, setBuyOpen] = useState(false);

  useEffect(() => {
    fetch("/api/me")
      .then((r) => (r.ok ? r.json() : null))
      .then((json) => {
        if (!json) return;
        if (typeof json.credits === "number") setCredits(json.credits);
        if (json.user) {
          setEmail(json.user.email ?? "Misafir");
        }
      })
      .catch(() => undefined);
  }, []);

  async function logout() {
    if (!authEnabled || !isSupabaseConfigured()) return;
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/");
    router.refresh();
  }

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-border/80 bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <AudioLines className="size-5 text-primary" />
            HAYL AI
          </Link>
          <nav className="flex items-center gap-2">
            {email ? (
              <>
                <Link href="/create" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}>
                  Oluştur
                </Link>
                <Link href="/songs" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}>
                  Şarkılarım
                </Link>
                {creditsEnabled ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setBuyOpen(true)}
                  >
                    <Coins className="size-4" />
                    {credits ?? "—"} kredi
                  </Button>
                ) : (
                  <span className="text-xs text-muted-foreground">Demo</span>
                )}
                {authEnabled ? (
                  <Button variant="ghost" size="icon-sm" onClick={logout} aria-label="Çıkış">
                    <LogOut className="size-4" />
                  </Button>
                ) : null}
              </>
            ) : (
              <Link href={authEnabled ? "/login" : "/create"} className={cn(buttonVariants({ size: "sm" }))}>
                {authEnabled ? "Giriş" : "Başla"}
              </Link>
            )}
          </nav>
        </div>
      </header>
      {creditsEnabled ? (
        <CreditsModal open={buyOpen} onOpenChange={setBuyOpen} />
      ) : null}
    </>
  );
}
