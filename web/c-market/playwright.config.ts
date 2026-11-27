import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir:'tests/browser',fullyParallel:false,workers:1,retries:0,timeout:60000,
  webServer:{command:'npm run dev',url:'http://127.0.0.1:5174',reuseExistingServer:false,timeout:60000},
  reporter:[['list'],['json',{outputFile:process.env.QA_RUN_TAG?'qa/browser-'+process.env.QA_RUN_TAG+'.json':'qa/browser-team.json'}]],
  use:{baseURL:'http://127.0.0.1:5174',channel:'chrome',headless:true,
    viewport:{width:1600,height:900},trace:'retain-on-failure',screenshot:'only-on-failure'}
});
