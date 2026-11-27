// Optional post-extraction check, run from a development checkout with Playwright installed.
import{chromium}from'@playwright/test';import assert from'node:assert/strict';import fs from'node:fs';
const[url,out]=process.argv.slice(2);if(!url||!out)throw new Error('Usage: node scripts/smoke_bundle.mjs <localhost URL> <report.json>');
assert.match(url,/^http:\/\/127\.0\.0\.1:\d+\/?$/);
const browser=await chromium.launch({channel:'chrome',headless:true});const page=await browser.newPage({viewport:{width:1600,height:900}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
const views=['시장 변화','운임·통항 탐색','같은 상태 비교','예측 신뢰도'];const results=[];
try{
 const response=await page.goto(url);assert.equal(response?.status(),200);await page.getByRole('heading',{name:'시장 변화',exact:true}).waitFor();
 for(const name of views){await page.getByRole('navigation').getByRole('button',{name:new RegExp(name)}).click();await page.getByRole('heading',{name,exact:true}).waitFor();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));results.push({view:name,status:'PASS'});}
 assert.match(await page.locator('.stat').first().innerText(),/14\.349/);
 const data=await page.request.get(new URL('/data/market.json',url).href);assert.equal(data.status(),200);const snapshot=await data.json();assert.equal(snapshot.states.length,201);assert.equal(snapshot.runs.length,62);assert.equal(snapshot.transitions.length,53);
 await page.waitForTimeout(250);assert.deepEqual(errors,[]);
 fs.writeFileSync(out,JSON.stringify({status:'PASS',url,views:results,snapshot:'201/62/53',ridge_MAE:'14.349',consoleErrors:errors,scope:'extracted frozen build; 4-view smoke, not the complete source regression suite'},null,2));
 console.log('Extracted build smoke PASS');
}finally{await browser.close();}
