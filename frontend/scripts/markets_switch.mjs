// Repro/verify: switch selected asset several times and capture the chart
// after each switch, to confirm the price axis resets to the new asset's data.
import puppeteer from 'puppeteer-core'
import { existsSync } from 'node:fs'
const chrome = ['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'].find(existsSync)
const OUT = process.argv[2]
const seq = process.argv.slice(3) // e.g. BTC/USDT SOL/USDT BTC/USDT
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function clickAsset(page, sym) {
  const ok = await page.evaluate((s) => {
    const btn = [...document.querySelectorAll('button')].find((b) => b.textContent && b.textContent.includes(s))
    if (btn) { btn.click(); return true }
    return false
  }, sym)
  if (!ok) throw new Error('no asset button ' + sym)
}

const b = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--no-sandbox'] })
const p = await b.newPage()
await p.setViewport({ width: 1500, height: 1000 })
await p.goto('http://localhost:3000/markets', { waitUntil: 'networkidle0', timeout: 60000 })
await sleep(2500)
let i = 0
for (const sym of seq) {
  await clickAsset(p, sym)
  await sleep(2200)
  const tag = sym.replace(/[^A-Z]/g, '')
  await p.screenshot({ path: `${OUT}/switch_${i}_${tag}.png` })
  console.log(`captured switch ${i} -> ${sym}`)
  i++
}
await b.close()
