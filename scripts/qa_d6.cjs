const {chromium}=require(process.env.CAUSALVERSE_PLAYWRIGHT_MODULE);
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1540,height:1080}});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('http://127.0.0.1:8766');await page.locator('.metrics').waitFor();
 const count=await page.locator('.toolbar select').first().locator('option').count();if(count!==80)throw Error('Missing runs');
 await page.screenshot({path:'artifacts/d6/overview.png',fullPage:true});
 await page.getByRole('button',{name:/播放回放/}).click();await page.waitForTimeout(650);await page.getByRole('button',{name:/暂停回放/}).click();
 const played=await page.locator('.clock span').textContent();
 const visited=[];
 for(let i=0;i<7;i++){
  await page.locator('nav button').nth(i).click();await page.waitForTimeout(170);visited.push(await page.locator('h1').textContent());
 }
 await page.locator('nav button').nth(3).click();
 await page.locator('input[type=range]').evaluate(el=>{el.value='3000';el.dispatchEvent(new Event('input',{bubbles:true}))});
 if(!await page.getByText('观测窗口尚未完整',{exact:true}).isVisible())throw Error('Future diagnosis leakage');
 await page.locator('input[type=range]').evaluate(el=>{el.value='5400';el.dispatchEvent(new Event('input',{bubbles:true}))});
 await page.getByLabel('识别方法').selectOption('logistic');await page.locator('.candidate').first().waitFor();
 await page.getByLabel('观测窗口').selectOption('600');await page.waitForTimeout(250);
 await page.locator('.toolbar select').first().selectOption('test_f00_19');await page.waitForTimeout(450);
 await page.locator('.candidate').first().waitFor();
 await page.locator('nav button').nth(5).click();await page.getByLabel('独立测试种子').selectOption('631019');await page.getByLabel('已执行历史动作').selectOption('5');await page.waitForTimeout(350);
 await page.locator('.plot-container').first().waitFor();await page.screenshot({path:'artifacts/d6/uncertainty.png',fullPage:true});
 let result=await page.request.post('http://127.0.0.1:8766/api/set_control',{data:{value:100}});if(result.status()!==405)throw Error('Writable API');
 await page.locator('nav button').first().click();await page.setViewportSize({width:390,height:844});await page.waitForTimeout(250);await page.screenshot({path:'artifacts/d6/mobile.png',fullPage:true});
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2);if(overflow)throw Error('Mobile overflow');
 await page.route('**/api/trajectory?*',route=>route.fulfill({status:503,body:'{}'}));await page.locator('.toolbar select').first().selectOption('test_f04_00');await page.getByRole('alert').waitFor();await page.unroute('**/api/trajectory?*');await page.getByRole('button',{name:'重新读取'}).click();await page.locator('.metrics').waitFor();
 fs.writeFileSync('artifacts/d6/browser-qa.json',JSON.stringify({visited,runOptions:count,played,errors,mobileOverflow:overflow,writeBlocked:true,errorAndRetryVerified:true,futureDiagnosisBlocked:true},null,2));
 await browser.close();if(errors.length)process.exit(1);
})().catch(e=>{console.error(e);process.exit(1)});
