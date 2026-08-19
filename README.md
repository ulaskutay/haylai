# HAYL AI

Amatör vokal → temizlik / pitch / (opsiyonel RVC) → altyapı mix.

## RunPod Serverless

Image’ı GitHub’dan kurarken:

- **Dockerfile:** `Dockerfile` (repo kökü; GitHub build context kök olduğu için)
- Alternatif: `apps/worker/Dockerfile` yalnızca context `apps/worker` ise
- GPU: RTX 4090, max workers 1, active workers 0
- Env: `PIPELINE_MODE=gpu`

Web uygulaması `apps/web`. Ortam değişkenleri: `apps/web/.env.example` (`.env.local` commit edilmez).
