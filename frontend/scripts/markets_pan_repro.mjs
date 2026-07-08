// Repro the real bug: user drags the PRICE axis (disables its autoScale),
// then switches asset -> new asset's candles render off-screen ("empty").
import puppeteer from 'puppeteer-core'
import { existsSync } from 'node:fs'
const chrome = ['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'].find(existsSync)
const OUT = process.argv[2]
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const click = (page, s) => page.evaluate((sym) => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent&&x.textContent.includes(sym)); if(b){b.click();return true} return false }, s)

const b = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--no-sandbox'] })
const p = await b.newPage()
await p.setViewport({ width: 1500, height: 1000 })
await p.goto('http://localhost:3000/markets', { waitUntil: 'networkidle0', timeout: 60000 })
await sleep(2500)
await click(p, 'BTC/USDT'); await sleep(2000)
// Drag the price axis (right edge) vertically to disable price autoScale.
await p.mouse.move(1440, 420); await p.mouse.down(); await p.mouse.move(1440, 600, { steps: 12 }); await p.mouse.up(); await sleep(800)
await p.screenshot({ path: `${OUT}/pan_0_btc_panned.png` })
// Now switch to SOL (~77 vs BTC ~62000).
await click(p, 'SOL/USDT'); await sleep(2200)
await p.screenshot({ path: `${OUT}/pan_1_sol_afterpan.png` })
await b.close()
console.log('done')
