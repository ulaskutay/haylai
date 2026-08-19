/**
 * Hetzner Object Storage (S3-compatible) — not wired yet.
 * When migrating: set STORAGE_DRIVER=hetzner and implement put/get/signedUrl
 * with @aws-sdk/client-s3 against HETZNER_S3_* env vars. Keep the same
 * bucket names: originals, processed, instrumentals.
 */
export function assertHetznerConfigured() {
  const required = [
    "HETZNER_S3_ENDPOINT",
    "HETZNER_S3_BUCKET",
    "HETZNER_S3_ACCESS_KEY",
    "HETZNER_S3_SECRET_KEY",
  ];
  const missing = required.filter((key) => !process.env[key]);
  if (missing.length) {
    throw new Error(
      `Hetzner storage is not configured (missing ${missing.join(", ")}). Keep STORAGE_DRIVER=local for now.`,
    );
  }
}
