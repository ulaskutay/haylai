import { SongsLibrary } from "@/components/songs-library";

export default function SongsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="mb-8 text-3xl font-semibold tracking-tight">Şarkılarım</h1>
      <SongsLibrary />
    </div>
  );
}
