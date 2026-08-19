# HAYL AI — Yol Haritası

**Ürün:** Amatör vokal kaydı → gürültü temizleme → pitch → RVC → altyapı mix/master → indirilebilir şarkı.

**Şu an:** **Faz 3 — RunPod Serverless GPU**  
`PROCESS_MODE=auto`: `RUNPOD_*` doluysa iş GPU’ya gider (min workers 0, istekte uyanır). Key yoksa lokal worker / ffmpeg. Auth ve iyzico kapalı.

```
Faz 0 ---- Faz 0.5 mix ---- Faz 2 worker ---- [==== Faz 3 GPU ====]-- Faz 1 auth -- Faz 4 ödeme
                                                    ▲ BURADAYIZ
```

---

## Faz özeti

| Faz | Hedef | Durum |
|-----|--------|--------|
| **0** | Repo, Next.js, Shadcn, koyu tema, lokal storage | Tamam |
| **0.5** | Guest ile kayıt → job → player + **vokal/altyapı mix** | Tamam |
| **1** | Google + magic link, gerçek kullanıcı kredisi | Kod var, kapalı (`AUTH_DISABLED=true`) |
| **2** | Lokal FastAPI worker (pitch/mix); auto fallback | Tamam |
| **3** | RunPod GPU: Demucs + RVC v2 | **Aktif — endpoint/key + lisanslı .pth sende** |
| **4** | iyzico kredi paketleri | API iskeleti var, key yok |
| **5** | Hetzner Object Storage | Adapter notu var, kullanılmıyor |
| **6** | Prod: gerçek altyapı WAV, lisanslı RVC modeli, polish | Başlanmadı |

---

## Faz 0 — İskelet (tamam)

- [x] Next.js App Router + Tailwind + Shadcn + Lucide
- [x] Landing, `/create` wizard, `/songs` listesi, işlem/player sayfası
- [x] Supabase Postgres şeması (`users`, `songs`, `instrumentals`, `payments`, kredi RPC)
- [x] Lokal disk: `data/audio/{originals,processed,instrumentals}/`
- [x] Stream/download (`/api/songs/[id]/stream`)

---

## Faz 0.5 — Mock MVP + mix (tamam)

**Ne çalışıyor**

- [x] Login yok → `guest@hayl.local` + 2 kredi
- [x] Mikrofon kaydı / dosya yükleme
- [x] Altyapı döngüleri (`data/audio/instrumentals/*.wav`)
- [x] ffmpeg-static ile vokal + bed mix → MP3
- [x] `PROCESS_MODE=auto` (worker yoksa mix, varsa FastAPI)
- [x] Player + indirme

**Bilinçli eksik (Faz 0.5 fallback)**

- Worker kapalıyken sadece ffmpeg mix; pitch yok
- Auth kapalı

**Kapanış kriteri:** Player’da vokal + altyapı birlikte duyulur.

---

## Faz 1 — Auth (sonraya bırakıldı)

`AUTH_DISABLED=false` ve `NEXT_PUBLIC_AUTH_DISABLED=false` yapılınca açılır.

- [ ] Google OAuth (Supabase Auth providers)
- [ ] Magic link e-posta
- [ ] Redirect URL: `{APP_URL}/auth/callback`
- [ ] Middleware koruması (`/create`, `/songs`)
- [ ] Guest’i kapat; her kullanıcı kendi kredisi
- [ ] `/login` sayfasını tekrar CTA yapmak

Kod: `apps/web/src/lib/auth.ts`, `middleware.ts`, `app/login`.

---

## Faz 2 — Lokal gerçek pipeline

`PROCESS_MODE=auto|local` + `apps/worker` FastAPI.

- [x] Worker API + mix (bed loop) + ffmpeg decode (`imageio-ffmpeg`)
- [x] `npm run worker` / `npm run worker:install` (venv: librosa, pedalboard)
- [x] Pitch: PyWorld varsa harvest; yoksa librosa `pyin` + `pitch_shift` (`PIPELINE_MODE=cpu`)
- [x] Pedalboard: highpass, compressor, delay, reverb; numpy fallback
- [x] Demucs/RVC yokken bile düzeltilmiş vokal + bed (RVC passthrough)

Kod: `apps/worker/pipeline/*`, `PROCESS_MODE` in `apps/web/src/lib/processing.ts`.

---

## Faz 3 — RunPod GPU (asıl ürün kalitesi)

Kod hazır; canlı GPU senin RunPod hesabın + public URL + (isteğe) lisanslı RVC `.pth`.

- [x] CUDA image (`apps/worker/Dockerfile`, `PIPELINE_MODE=gpu`, Demucs warmup)
- [x] Demucs (CUDA varsa); yoksa spektral temizlik
- [x] RVC: `RVC_MODEL_PATH` + `RVC_INFER_PY` (ünlü tınısı yok; model yoksa passthrough)
- [x] Serverless handler `rp_handler.py` — scale to zero
- [x] `POST /run` + RunPod webhook + 15 dk status poll
- [x] `PROCESS_MODE=auto` → RunPod (key varsa) → lokal → ffmpeg
- [x] Fail olunca kredi iadesi (kredi açıksa)

**Deploy (senin yapman gereken)**

1. RunPod → Serverless endpoint, GPU (ör. 24GB), **min workers = 0**, idle kısa, max 1–2
2. Image: `apps/worker` Dockerfile’ı registry’ye push, endpoint’e bağla
3. Network volume (opsiyonel): lisanslı `hayl.pth` + `infer.py` → env `RVC_MODEL_PATH` / `RVC_INFER_PY`
4. `apps/web/.env.local`: `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID`
5. `NEXT_PUBLIC_APP_URL` RunPod’un göreceği adres (prod domain veya Cloudflare Tunnel). `localhost` GPU’dan dosya çekemez.

Cold start: ilk şarkı yavaş olabilir (worker + Demucs). İstek yokken GPU ücreti yok.

---

## Faz 4 — Ödeme (iyzico)

- [ ] Sandbox API key
- [ ] Paket modalı (10 / 30 / 100 kredi) — UI var
- [ ] Checkout + webhook E2E
- [ ] Auth açıkken kullanıcıya kredi yükleme

---

## Faz 5 — Hetzner storage

- [ ] `STORAGE_DRIVER=hetzner` + S3 credential
- [ ] `apps/web/src/lib/storage-hetzner.ts` implementasyonu
- [ ] `originals` / `processed` / `instrumentals` bucket migrate

---

## Faz 6 — Prod cilası

- [ ] Gerçek Pop / Trap / Rock / Lo-Fi / Slow WAV (lisanslı)
- [ ] Landing önce/sonra örnekleri gerçek kayıt
- [ ] Max süre, rate limit, orijinal dosyayı N gün sonra sil
- [ ] Hata izleme, basit admin (altyapı yükleme)

---

## Kararlar (sabit)

| Konu | Seçim |
|------|--------|
| Auth/DB | Supabase (şimdilik guest) |
| Ses dosyası | Lokal disk → sonra Hetzner |
| GPU | RunPod Serverless (min 0) |
| Ödeme | iyzico (kapalı, `CREDITS_DISABLED=true`) |
| Pipeline şimdi | `PROCESS_MODE=auto` (key varsa RunPod) |

Auth: `AUTH_DISABLED=false`. Ödeme: `CREDITS_DISABLED=false`.

---

## Önerilen sıra (bundan sonra)

1. **RunPod endpoint** — image + `RUNPOD_*` + public `APP_URL`
2. **Lisanslı RVC .pth** — volume’a koy (ünlü modeli yok)
3. **Faz 1** — Login
4. **Faz 4** — iyzico
5. **Faz 5** — Hetzner

Login ve ödemeyi ses kalitesinden sonraya bırakmak bilinçli: ürün hissi pipeline’dan gelir.
