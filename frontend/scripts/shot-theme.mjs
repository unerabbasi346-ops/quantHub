// QA helper (not shipped): screenshot a route in a chosen theme by seeding the
// same localStorage key the app's pre-paint theme script reads.
// Usage: node scripts/shot-theme.mjs <route> <out.png> <dark|light> [waitMs]
import puppeteer from "puppeteer-core";
import { existsSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const chrome = [
  process.env.CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
].find((p) => p && existsSync(p));

const [route, out, theme = "dark", waitMs = "2600"] = process.argv.slice(2);
const url = /^https?:/.test(route) ? route : `http://localhost:3000${route}`;

await mkdir(dirname(out), { recursive: true });
const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox", "--disable-gpu"] });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1400, deviceScaleFactor: 1 });
  await page.evaluateOnNewDocument((t) => {
    try { localStorage.setItem("quant-hub-theme", t); } catch {}
  }, theme);
  await page.goto(url, { waitUntil: "networkidle0", timeout: 30000 });
  await new Promise((r) => setTimeout(r, Number(waitMs)));
  await page.screenshot({ path: out, fullPage: true });
  const applied = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  console.log(`saved ${out} (${url}) theme=${applied}`);
} finally {
  await browser.close();
}
