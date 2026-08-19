# HAYL AI

Amatör vokal → temizlik / pitch / (opsiyonel RVC) → altyapı mix.

## RunPod Serverless

Image’ı GitHub’dan kurarken:

- **Dockerfile:** `apps/worker/Dockerfile`
- **Build context:** `apps/worker` (repo kökü değil)
- GPU: RTX 4090, max workers 1, active workers 0
- Env: `PIPELINE_MODE=gpu`

Web uygulaması `apps/web`. Ortam değişkenleri: `apps/web/.env.example` (`.env.local` commit edilmez).
