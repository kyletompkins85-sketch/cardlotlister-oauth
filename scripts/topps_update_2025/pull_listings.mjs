// scripts/topps_update_2025/pull_listings.mjs
// Pulls listings from your Worker (which pulls from Supabase) and writes a dataset file into the repo.

import fs from "node:fs";
import path from "node:path";

const BASE = process.env.WORKER_BASE_URL; // e.g. https://...workers.dev
const KEY = process.env.INTERNAL_API_KEY; // secret
const Q = process.env.QUERY || "2025 Topps Update"; // filter
const LIMIT = Number(process.env.LIMIT || 1000);

if (!BASE) throw new Error("Missing WORKER_BASE_URL");
if (!KEY) throw new Error("Missing INTERNAL_API_KEY");

async function fetchPage(offset) {
  const u = new URL("/internal/listings/search", BASE);
  if (Q && Q.trim().length) u.searchParams.set("q", Q.trim());
  u.searchParams.set("limit", String(LIMIT));
  u.searchParams.set("offset", String(offset));

  const resp = await fetch(u.toString(), {
    headers: { "x-internal-key": KEY },
  });

  const text = await resp.text();
  let json;
  try { json = JSON.parse(text); } catch { json = { raw: text }; }

  if (!resp.ok) {
    throw new Error(`Worker request failed ${resp.status}: ${text}`);
  }
  return json;
}

async function main() {
  let offset = 0;
  const all = [];

  while (true) {
    const page = await fetchPage(offset);
    const rows = page.rows || [];
    all.push(...rows);

    if (!page.next_offset) break;
    offset = page.next_offset;
  }

  // write dataset
  const outDir = path.join(process.cwd(), "data", "topps_update_2025");
  fs.mkdirSync(outDir, { recursive: true });

  const safeQ = (Q || "all").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  const outPath = path.join(outDir, `listings_${safeQ}.json`);

  fs.writeFileSync(outPath, JSON.stringify({
    pulled_at: new Date().toISOString(),
    query: Q,
    count: all.length,
    rows: all
  }, null, 2));

  console.log(`Wrote ${all.length} rows to ${outPath}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
