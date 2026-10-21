const fs = require('fs');
const path = require('path');
const cp = require('child_process');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '../site/assets/supplements');
const scratch = path.resolve(__dirname, 'supplement-render');
const qa = path.resolve(__dirname, 'qa');
const chrome = process.env.CHROME_PATH || undefined;
const assert = (value, message) => { if (!value) throw new Error(message); };

(async () => {
  fs.mkdirSync(scratch, { recursive: true });
  fs.mkdirSync(qa, { recursive: true });
  const allNames = fs.readdirSync(root).filter(n => /^\d+-[a-z]+\.svg$/.test(n)).sort();
  const modeOption = process.argv.find(arg=>arg.startsWith('--modes='));
  const modes = modeOption ? modeOption.slice('--modes='.length).split(',') : [];
  const names = allNames.filter(n=>!modes.length || modes.some(mode=>n.endsWith('-'+mode+'.svg')));
  assert(names.length > 0, 'No supplement SVG files found');
  const hashesBefore = Object.fromEntries(names.map(n => [n, require('crypto').createHash('sha256').update(fs.readFileSync(path.join(root, n))).digest('hex')]));
  const browser = await chromium.launch({ headless: true, executablePath: chrome });
  const context = await browser.newContext({ viewport: { width: 1200, height: 1600 }, deviceScaleFactor: 1 });
  const reportPath = path.join(__dirname, 'supplement-render-report.json');
  const previous = modes.length && fs.existsSync(reportPath) ? JSON.parse(fs.readFileSync(reportPath,'utf8')) : null;
  const report = { count: allNames.length, renderedThisRun:names.length, modes, textIssues: [], renderIssues: [], items: [], representatives: [] };
  let cursor = 0;
  const chosen = ['68-overview.svg', '75-ideas.svg', '100-reflections.svg'];
  try {
    await Promise.all(Array.from({length: 4}, async () => {
      const page = await context.newPage();
      while (cursor < names.length) {
        const name = names[cursor++];
        const svg = fs.readFileSync(path.join(root, name), 'utf8');
        await page.setContent('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:white}svg{display:block}</style></head><body>' + svg + '</body></html>');
        await page.evaluate(() => document.fonts.ready);
        const dimensions = await page.locator('svg').evaluate(el => {
          const r = el.getBoundingClientRect();
          const issues = [];
          for (const text of el.querySelectorAll('text')) {
            const y = Number(text.getAttribute('y'));
            const content = text.textContent;
            const footer = Math.abs(y - 1490) < 0.1 && /本站|原创|补充|整理|非书中|导读/.test(content);
            const b = text.getBBox();
            if (!footer && (y >= 1430 || b.y + b.height > 1430)) issues.push({type:'bottom-overflow', y, bottom:b.y+b.height, text:content});
            if (b.x < 0 || b.x + b.width > 1200) issues.push({type:'horizontal-overflow', left:b.x, right:b.x+b.width, text:content});
          }
          return { width: r.width, height: r.height, issues };
        });
        assert(dimensions.width === 1200 && dimensions.height === 1600, `${name}: unexpected dimensions ${JSON.stringify(dimensions)}`);
        for (const issue of dimensions.issues) report.textIssues.push({file:name, ...issue});
        const png = path.join(scratch, name.replace('.svg', '.png'));
        await page.locator('svg').screenshot({ path: png, type: 'png', animations: 'disabled' });
        if (chosen.includes(name)) {
          const representative = path.join(qa, 'supplement-' + name.replace('.svg', '.png'));
          fs.copyFileSync(png, representative);
          report.representatives.push(representative);
        }
        report.items.push({file:name, png, width:dimensions.width, height:dimensions.height});
        if (report.items.length % 20 === 0) console.log(`Rendered ${report.items.length}/${names.length}`);
      }
      await page.close();
    }));
  } finally {
    await browser.close();
  }
  for (const name of names) {
    const after = require('crypto').createHash('sha256').update(fs.readFileSync(path.join(root, name))).digest('hex');
    assert(after === hashesBefore[name], name + ': source changed during render');
  }
  const converted = cp.spawnSync(process.env.PYTHON || 'python', [path.join(__dirname, 'convert_supplements.py'), root, scratch, modes.join(',')], {encoding:'utf8', windowsHide:true, maxBuffer:4*1024*1024});
  assert(converted.status === 0, converted.stderr || converted.stdout || 'Pillow conversion failed');
  report.conversion = JSON.parse(converted.stdout);
  if (previous) {
    report.items.push(...previous.items.filter(item=>!names.includes(item.file)));
    report.textIssues.push(...previous.textIssues.filter(item=>!names.includes(item.file)));
    report.representatives=[...new Set([...report.representatives,...previous.representatives])];
  }
  report.items.sort((a,b)=>a.file.localeCompare(b.file));
  assert(report.items.length === allNames.length, 'Actual text bounding-box checks do not cover all SVG files');
  fs.writeFileSync(reportPath, JSON.stringify(report,null,2));
  console.log(JSON.stringify({total:report.count,renderedThisRun:report.renderedThisRun, conversion:report.conversion, textIssues:report.textIssues, representatives:report.representatives}, null, 2));
  if (report.textIssues.length || report.conversion.xmlTextIssues.length) process.exitCode = 2;
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
