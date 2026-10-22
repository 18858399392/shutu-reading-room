const fs = require('fs');
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const assets = path.join(__dirname, '../site/assets');
  const svg = fs.readFileSync(path.join(assets, 'icon.svg'), 'utf8');
  const browser = await chromium.launch({headless: true, ...(process.env.CHROME_PATH ? {executablePath: process.env.CHROME_PATH} : {})});
  try {
    for (const size of [192, 512]) {
      const page = await browser.newPage({viewport: {width: size, height: size}, deviceScaleFactor: 1});
      const sized = svg.replace('width="512" height="512"', `width="${size}" height="${size}"`);
      await page.setContent(`<style>html,body{margin:0}svg{display:block}</style>${sized}`);
      await page.locator('svg').screenshot({path: path.join(assets, `icon-${size}.png`), omitBackground: true});
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
