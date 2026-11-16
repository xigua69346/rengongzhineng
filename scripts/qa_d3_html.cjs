const {chromium}=require(process.env.CAUSALVERSE_PLAYWRIGHT_MODULE);
const fs=require('fs');
const path=require('path');
(async()=>{
  const browser=await chromium.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto('file:///'+path.resolve('artifacts/d3/detection/experiment.html').replace(/\\/g,'/'));
  await page.waitForFunction(()=>document.querySelector('#labels .plot-container'));
  const initial=await page.locator('#run option').count();
  await page.selectOption('#run','test_f14_19');
  await page.selectOption('#detector','SPE');
  await page.waitForFunction(()=>document.getElementById('summary').textContent.includes('IDV=14'));
  await page.screenshot({path:'artifacts/d3/detection/visual-qa.png',fullPage:true});
  fs.writeFileSync('artifacts/d3/detection/browser-qa.json',JSON.stringify({runOptions:initial,errors,selectedRun:await page.inputValue('#run'),selectedDetector:await page.inputValue('#detector')},null,2));
  await browser.close();
  if(errors.length||initial!==80)process.exit(1);
})();
