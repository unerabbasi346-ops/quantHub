// Capture a route at a given theme. Usage:
//   node scripts/capture.mjs <route> <out.png> <dark|light> [wait_ms]
import puppeteer from 'puppeteer-core'
import { existsSync } from 'node:fs'
const chrome = ['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'].find(existsSync)
const [route, out, theme = 'dark', wait = '2600'] = process.argv.slice(2)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const b = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--no-sandbox'] })
const p = await b.newPage()
await p.setViewport({ width: 1500, height: 1050 })
await p.evaluateOnNewDocument((t) => {
  try { window.localStorage.setItem('quant-hub-theme', t) } catch {}
}, theme)
await p.goto(`http://localhost:3000${route}`, { waitUntil: 'networkidle0', timeout: 60000 })
await sleep(Number(wait))
await p.screenshot({ path: out, fullPage: true })
await b.close()
console.log('captured', route, theme, '->', out)
