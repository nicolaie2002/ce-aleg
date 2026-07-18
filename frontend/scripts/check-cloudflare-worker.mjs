import { spawnSync } from "node:child_process";

const freePlanLimitKiB = 3 * 1024;
const command = process.platform === "win32" ? "npx.cmd" : "npx";
const result = spawnSync(
  command,
  ["wrangler", "deploy", "--dry-run", "--outdir", ".wrangler/bundled"],
  { cwd: process.cwd(), encoding: "utf8" }
);

const output = `${result.stdout || ""}\n${result.stderr || ""}`;
process.stdout.write(output);

if (result.status !== 0) {
  process.exit(result.status || 1);
}

const match = output.match(/gzip:\s*([\d.]+)\s*KiB/i);

if (!match) {
  console.error("Could not read the compressed Worker size from Wrangler.");
  process.exit(1);
}

const compressedKiB = Number(match[1]);

if (!Number.isFinite(compressedKiB) || compressedKiB > freePlanLimitKiB) {
  console.error(
    `Cloudflare Worker is ${compressedKiB.toFixed(2)} KiB gzip; ` +
      `the Free plan limit is ${freePlanLimitKiB} KiB.`
  );
  process.exit(1);
}

console.log(
  `Cloudflare Free size gate passed: ${compressedKiB.toFixed(2)} / ` +
    `${freePlanLimitKiB} KiB gzip.`
);
