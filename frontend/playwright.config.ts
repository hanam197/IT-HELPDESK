import { defineConfig } from '@playwright/test'
export default defineConfig({testDir:'./tests',use:{launchOptions:{executablePath:process.env.BROWSER_EXECUTABLE},baseURL:process.env.BASE_URL||'http://127.0.0.1:5173',viewport:{width:1440,height:1050},screenshot:'only-on-failure',trace:'retain-on-failure'},workers:1,reporter:'list'})
