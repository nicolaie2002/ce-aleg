import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { gzipSync } from "node:zlib";

const nextDirectory = resolve(".next");
const appDirectory = join(nextDirectory, "server", "app");
const limitKb = Number(process.env.BUNDLE_MAX_GZIP_KB || 500);

if (!existsSync(appDirectory)) {
  throw new Error("Build manifest missing. Run `npm run build` first.");
}

function findRouteManifests(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return findRouteManifests(path);
    return entry.name.endsWith("page_client-reference-manifest.js") ? [path] : [];
  });
}

function parseRouteManifest(path) {
  const source = readFileSync(path, "utf8");
  const assignment = source
    .split(/\r?\n/)
    .find((line) => line.startsWith("globalThis.__RSC_MANIFEST["));

  if (!assignment) throw new Error(`Invalid route manifest: ${relative(nextDirectory, path)}`);

  const separator = assignment.indexOf(" = ");
  const leftHandSide = assignment.slice(0, separator);
  const route = JSON.parse(leftHandSide.slice(leftHandSide.indexOf("[") + 1, -1));
  const payload = assignment.slice(separator + 3).replace(/;\s*$/, "");
  return { route, manifest: JSON.parse(payload) };
}

const results = findRouteManifests(appDirectory).map((path) => {
  const { route, manifest } = parseRouteManifest(path);
  const chunks = [...new Set(Object.values(manifest.entryJSFiles || {}).flat())];
  const gzipBytes = chunks.reduce((total, chunk) => {
    const chunkPath = join(nextDirectory, chunk);
    if (!existsSync(chunkPath) || !statSync(chunkPath).isFile()) {
      throw new Error(`Missing client chunk ${chunk} for ${route}`);
    }
    return total + gzipSync(readFileSync(chunkPath), { level: 9 }).length;
  }, 0);

  return { route, chunks: chunks.length, gzipKb: gzipBytes / 1024 };
}).sort((left, right) => right.gzipKb - left.gzipKb);

for (const result of results) {
  console.log(`${result.gzipKb.toFixed(1).padStart(7)} KB  ${result.route} (${result.chunks} chunks)`);
}

const failures = results.filter((result) => result.gzipKb > limitKb);
if (failures.length > 0) {
  throw new Error(
    `Initial JavaScript exceeds ${limitKb} KB gzip: ${failures.map((item) => item.route).join(", ")}`,
  );
}

console.log(`All ${results.length} application routes are below ${limitKb} KB gzip.`);
