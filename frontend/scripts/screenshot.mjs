#!/usr/bin/env node
// Reusable dev-only screenshot tool (T-1 fix, handbook/KNOWN_LIMITATIONS.md).
// Launches the system-installed Chrome headlessly via puppeteer-core (a
// devDependency only — no Chromium download, no production footprint) and
// saves a screenshot of any route on a running dev server.
//
// Usage:
//   npm run screenshot -- <route> [outFile] [options]
//   node scripts/screenshot.mjs <route> [outFile] [options]
//
// Examples:
//   npm run screenshot -- /dashboard
//   npm run screenshot -- /dashboard dashboard.png
//   npm run screenshot -- /portfolio out/portfolio.png --width=1280 --height=900
//   npm run screenshot -- http://localhost:3000/risk risk.png --wait=2000
//
// Arguments:
//   route     Path (resolved against --base, default http://localhost:3000)
//             or a full http(s):// URL. Required.
//   outFile   Output PNG path (default: screenshot.png in cwd).
//
// Options:
//   --base=<url>      Base URL routes are resolved against (default http://localhost:3000)
//   --width=<px>       Viewport width (default 1600)
//   --height=<px>      Viewport height (default 1400)
//   --wait=<ms>        Extra settle time after network-idle before capturing (default 1000)
//   --full-page=false  Capture only the viewport instead of the full scrollable page
//
// Requires: a system-installed Chrome/Chromium. Auto-detects the standard
// Windows/macOS/Linux install paths; override with CHROME_PATH or
// PUPPETEER_EXECUTABLE_PATH if Chrome lives elsewhere.
//
// This assumes the target dev server (e.g. `npm run dev`) is already
// running — it does not start one for you.
//
// Windows/Git Bash note: a route argument starting with "/" (e.g.
// "/dashboard") gets auto-translated into a Windows filesystem path by
// Git Bash's MSYS layer before Node ever sees it. If you hit
// ERR_FILE_NOT_FOUND pointing at something like "C:/Program Files/Git/...",
// prefix the command with MSYS_NO_PATHCONV=1, e.g.:
//   MSYS_NO_PATHCONV=1 npm run screenshot -- /dashboard out.png

import puppeteer from "puppeteer-core";
import { existsSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";

function parseArgs(argv) {
  const positional = [];
  const options = {};
  for (const arg of argv) {
    if (arg.startsWith("--")) {
      const [key, value] = arg.slice(2).split(/=(.*)/s);
      options[key] = value ?? "true";
    } else {
      positional.push(arg);
    }
  }
  return { positional, options };
}

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    process.env.PUPPETEER_EXECUTABLE_PATH,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);

  const found = candidates.find((path) => existsSync(path));
  if (!found) {
    throw new Error(
      "No system Chrome found. Set CHROME_PATH to your Chrome/Chromium executable.",
    );
  }
  return found;
}

async function main() {
  const { positional, options } = parseArgs(process.argv.slice(2));
  const [route, outFileArg] = positional;

  if (!route) {
    console.error("Usage: node scripts/screenshot.mjs <route> [outFile] [options]");
    process.exit(1);
  }

  const base = options.base ?? "http://localhost:3000";
  const url = /^https?:\/\//.test(route) ? route : new URL(route, base).toString();
  const outFile = resolve(outFileArg ?? "screenshot.png");
  const width = Number(options.width ?? 1600);
  const height = Number(options.height ?? 1400);
  const wait = Number(options.wait ?? 1000);
  const fullPage = options["full-page"] !== "false";

  await mkdir(dirname(outFile), { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: findChrome(),
    headless: true,
    args: ["--no-sandbox", "--disable-gpu"],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width, height });
    await page.goto(url, { waitUntil: "networkidle0", timeout: 30000 });
    if (wait > 0) {
      await new Promise((r) => setTimeout(r, wait));
    }
    await page.screenshot({ path: outFile, fullPage });
    console.log(`Screenshot saved: ${outFile} (${url})`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
