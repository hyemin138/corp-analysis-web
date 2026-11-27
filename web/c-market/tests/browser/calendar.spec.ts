import{test,expect}from'@playwright/test';import fs from'node:fs';
test('all time charts render identical month-boundary pixels in UTC and Seoul',async({browser})=>{
 const shots:Record<string,Buffer>={};const labels=['국제운임 흐름','항로 기준100 비교','동기 운임 차트','동기 통항 차트','시장 상태 타임라인','원점별 예측과 실제 변화','선택사례 EUMED 수준'];
 for(const timezoneId of['UTC','Asia/Seoul']){
  const context=await browser.newContext({timezoneId,viewport:{width:1600,height:900},locale:'ko-KR',deviceScaleFactor:1});const page=await context.newPage();await page.goto('/');await expect(page.getByRole('heading',{name:'시장 변화',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>new Date('2026-04-01T00:00:00Z').getTimezoneOffset())).toBe(timezoneId==='UTC'?0:-540);
  for(const label of labels){
   if(label==='동기 운임 차트')await page.getByRole('navigation').getByRole('button',{name:/운임·통항 탐색/}).click();
   if(label==='원점별 예측과 실제 변화')await page.getByRole('navigation').getByRole('button',{name:/예측 신뢰도/}).click();
   if(label==='선택사례 EUMED 수준')await page.getByText('EUMED 실제 수준과 이 원점의 환산예측',{exact:true}).click();
   const chart=page.getByTestId(label);await chart.scrollIntoViewIfNeeded();await page.mouse.move(0,0);await page.waitForTimeout(550);const blob=await chart.locator('canvas').screenshot();
   const id=labels.indexOf(label);fs.mkdirSync('qa/v2/timezone',{recursive:true});fs.writeFileSync(`qa/v2/timezone/${timezoneId==='UTC'?'UTC':'Seoul'}_${id}.png`,blob);
   if(timezoneId==='UTC')shots[label]=blob;else expect(blob.equals(shots[label]),`timezone difference in ${label}`).toBe(true);
  }
  await context.close();
 }
});
test('weekly pointer has real values at all 41 positions rather than empty weekdays',async({page})=>{
 await page.goto('/');await page.getByRole('navigation').getByRole('button',{name:/운임·통항 탐색/}).click();await page.getByLabel('기간 시작일').fill('2026-01-05');await page.getByLabel('기간 종료일').fill('2026-05-04');
 const fare=page.getByTestId('동기 운임 차트'),transit=page.getByTestId('동기 통항 차트');await fare.scrollIntoViewIfNeeded();const b=await fare.boundingBox();
 const actualDates=new Set(JSON.parse(fs.readFileSync('public/data/market.json','utf8')).features.map((x:any)=>x.date));
 for(let i=0;i<41;i++){await page.mouse.move(b!.x+58+(b!.width-84)*(.05+.9*i/40),b!.y+120);const tip=transit.locator('div').filter({hasText:/동기 커서 20/}).last();await expect(tip).toBeVisible();const text=await tip.innerText();expect(text).not.toMatch(/관측 없음|미확보/);const date=text.match(/동기 커서 (\d{4}-\d{2}-\d{2})/)?.[1];expect(date).toBeTruthy();expect(actualDates.has(date)).toBe(true);}
});
