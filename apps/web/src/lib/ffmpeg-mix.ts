import { spawn } from "child_process";
import { mkdtemp, readFile, rm, writeFile } from "fs/promises";
import os from "os";
import path from "path";
import ffmpegPath from "ffmpeg-static";

function bin() {
  if (ffmpegPath) return ffmpegPath;
  return "ffmpeg";
}

function run(cmd: string, args: string[]) {
  return new Promise<void>((resolve, reject) => {
    const child = spawn(cmd, args, { stdio: ["ignore", "pipe", "pipe"] });
    let err = "";
    child.stderr.on("data", (chunk) => {
      err += String(chunk);
    });
    child.on("error", (error) => reject(error));
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(err.slice(-800) || `ffmpeg exited ${code}`));
    });
  });
}

export async function ffmpegAvailable() {
  try {
    await run(bin(), ["-version"]);
    return true;
  } catch {
    return false;
  }
}

export async function mixVocalAndBed(vocal: Buffer, bed: Buffer, vocalExt: string) {
  const dir = await mkdtemp(path.join(os.tmpdir(), "hayl-mix-"));
  const ext = vocalExt.replace(/^\./, "") || "webm";
  const vocalPath = path.join(dir, `vocal.${ext}`);
  const bedPath = path.join(dir, "bed.wav");
  const outPath = path.join(dir, "out.mp3");

  try {
    await writeFile(vocalPath, vocal);
    await writeFile(bedPath, bed);
    await run(bin(), [
      "-y",
      "-i",
      vocalPath,
      "-stream_loop",
      "-1",
      "-i",
      bedPath,
      "-filter_complex",
      "[0:a]highpass=f=80,volume=1.15[v];[1:a]volume=0.4[b];[v][b]amix=inputs=2:duration=first:dropout_transition=0,volume=0.9[a]",
      "-map",
      "[a]",
      "-c:a",
      "libmp3lame",
      "-b:a",
      "192k",
      outPath,
    ]);
    return await readFile(outPath);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}
