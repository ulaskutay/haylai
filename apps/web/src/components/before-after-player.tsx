"use client";

import { useMemo, useState } from "react";
import { WaveformPlayer } from "@/components/waveform-player";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function BeforeAfterPlayer() {
  const [mode, setMode] = useState("before");
  const src = useMemo(
    () => (mode === "before" ? "/demo/before.wav" : "/demo/after.wav"),
    [mode],
  );

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-sm font-medium">Önce / Sonra</p>
        <Tabs value={mode} onValueChange={setMode}>
          <TabsList>
            <TabsTrigger value="before">Önce</TabsTrigger>
            <TabsTrigger value="after">Sonra</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <WaveformPlayer src={src} />
    </div>
  );
}
