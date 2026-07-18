import { readFile } from "node:fs/promises";
import path from "node:path";

const MINIMUM_COVERAGE = 60;
const SUMMARY_PATH = path.join(process.cwd(), "coverage", "coverage-summary.json");
const TARGETS = ["app/components/", "app/utils/"];
const METRICS = ["statements", "lines"];

function normalize(filePath) {
  return filePath.replaceAll("\\", "/");
}

function aggregate(entries) {
  return METRICS.reduce((result, metric) => {
    const totals = entries.reduce(
      (sum, [, coverage]) => ({
        covered: sum.covered + coverage[metric].covered,
        total: sum.total + coverage[metric].total,
      }),
      { covered: 0, total: 0 }
    );

    result[metric] = totals.total === 0 ? 0 : (totals.covered / totals.total) * 100;
    return result;
  }, {});
}

let summary;
try {
  summary = JSON.parse(await readFile(SUMMARY_PATH, "utf8"));
} catch (error) {
  console.error(`Could not read ${SUMMARY_PATH}: ${error.message}`);
  process.exit(1);
}

const fileEntries = Object.entries(summary).filter(([filePath]) => filePath !== "total");
let failed = false;

for (const target of TARGETS) {
  const entries = fileEntries.filter(([filePath]) => normalize(filePath).includes(`/${target}`));
  if (entries.length === 0) {
    console.error(`No coverage entries found for ${target}`);
    failed = true;
    continue;
  }

  const coverage = aggregate(entries);
  const result = METRICS.map((metric) => `${metric}=${coverage[metric].toFixed(2)}%`).join(", ");
  console.log(`${target}: ${result}`);

  for (const metric of METRICS) {
    if (coverage[metric] < MINIMUM_COVERAGE) {
      console.error(
        `${target} ${metric} coverage must be at least ${MINIMUM_COVERAGE}%.`
      );
      failed = true;
    }
  }
}

if (failed) process.exit(1);
console.log(`Targeted coverage gate passed (minimum ${MINIMUM_COVERAGE}%).`);
