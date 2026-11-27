import {test,expect} from '@playwright/test';
test('public clone without private data explains the required local import',async({page})=>{
 await page.route('**/data/market.json',r=>r.fulfill({status:404,contentType:'text/plain',body:'Not bundled'}));
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'자료를 불러오지 못했습니다'})).toBeVisible();
 await expect(page.locator('main')).toContainText('팀 내부 연구 스냅샷을 먼저 가져오세요');
 await expect(page.locator('main')).toContainText('data:import');
 await expect(page.getByRole('button',{name:'다시 불러오기'})).toBeVisible();
});
