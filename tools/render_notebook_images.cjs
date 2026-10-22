const fs = require('fs');
const path = require('path');
const cp = require('child_process');
const crypto = require('crypto');
const modules=process.env.CODEX_NODE_MODULES||path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE||path.join(modules,'playwright'));
const args=process.argv.slice(2),option=k=>{const i=args.indexOf(k);return i>=0?args[i+1]:null};
const repo=path.resolve(option('--repo-dir')||(path.basename(__dirname)==='tools'?path.dirname(__dirname):path.join(__dirname,'shutu-repo')));
const base=path.resolve(option('--work-dir')||(path.basename(__dirname)==='tools'?path.join(repo,'.notebook-build'):__dirname));
const dir=path.join(repo,'site/assets/notebook');
const scratch=path.join(base,'notebook-render');
const qa=path.join(base,'notebook-qa');
fs.mkdirSync(scratch,{recursive:true});fs.mkdirSync(qa,{recursive:true});
const report=JSON.parse(fs.readFileSync(path.join(base,'notebook-image-report.json'),'utf8'));
const allSources=report.generated_sources.map(x=>x.file).sort();
const kinds=(option('--kinds')||'').split(',').filter(Boolean);
const sources=allSources.filter(n=>!kinds.length||kinds.some(k=>n.endsWith('-'+k+'.svg')));
const chosen=new Set(['16-cover.svg','22-three-lines.svg','37-blackboard.svg','50-cover.svg','68-three-lines.svg','82-cover.svg','89-blackboard.svg']);
const sourceHashes=Object.fromEntries(sources.map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,n))).digest('hex')]));
const assert=(v,msg)=>{if(!v)throw Error(msg)};
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||process.env.NOTEBOOK_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const context=await browser.newContext({viewport:{width:1200,height:1600},deviceScaleFactor:1});
 const checks=[];const textIssues=[];let cursor=0;
 try{
  await Promise.all(Array.from({length:4},async()=>{
   const page=await context.newPage();
   while(cursor<sources.length){
    const name=sources[cursor++];const svg=fs.readFileSync(path.join(dir,name),'utf8');
    await page.setContent('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0}svg{display:block}</style></head><body>'+svg+'</body></html>');
    await page.evaluate(()=>document.fonts.ready);
    const result=await page.locator('svg').evaluate(svg=>{
     const rect=svg.getBoundingClientRect();const errors=[];const items=[];
     for(const t of svg.querySelectorAll('text')){
      const r=t.getBBox();const limits={left:+t.dataset.left,right:+t.dataset.right,top:+t.dataset.top,bottom:+t.dataset.bottom};
      const item={zone:t.dataset.zone,text:t.textContent,x:r.x,y:r.y,width:r.width,height:r.height,limits};
      items.push(item);
      if(r.x<limits.left-2||r.x+r.width>limits.right+2||r.y<limits.top-2||r.y+r.height>limits.bottom+2)errors.push(item);
     }
     return {width:rect.width,height:rect.height,textCount:items.length,errors};
    });
    assert(result.width===1200&&result.height===1600,name+': invalid viewport');
    if(result.errors.length)textIssues.push({file:name,errors:result.errors});
    const png=path.join(scratch,name.replace('.svg','.png'));
    await page.locator('svg').screenshot({path:png,type:'png',animations:'disabled'});
    if(chosen.has(name))fs.copyFileSync(png,path.join(qa,name.replace('.svg','.png')));
    checks.push({file:name,width:result.width,height:result.height,textCount:result.textCount});
    if(checks.length%20===0)console.log('Rendered '+checks.length+'/'+sources.length);
   }
   await page.close();
  }));
 }finally{await browser.close()}
 for(const name of sources)assert(sourceHashes[name]===crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,name))).digest('hex'),name+': source mutated');
 if(kinds.length&&fs.existsSync(path.join(base,'notebook-previous-report.json'))){
  const previous=JSON.parse(fs.readFileSync(path.join(base,'notebook-previous-report.json'),'utf8'));
  if(previous.text_bbox_checks){
   checks.push(...previous.text_bbox_checks.items.filter(x=>allSources.includes(x.file)&&!sources.includes(x.file)));
   textIssues.push(...previous.text_bbox_checks.issues.filter(x=>allSources.includes(x.file)&&!sources.includes(x.file)));
  }
 }
 assert(checks.length===allSources.length,'Missing bounding-box coverage for current plan');
 report.text_bbox_checks={checked_svg_count:checks.length,checked_text_count:checks.reduce((n,x)=>n+x.textCount,0),issues:textIssues,items:checks};
 fs.writeFileSync(path.join(base,'notebook-image-report.json'),JSON.stringify(report,null,2));
 if(textIssues.length){console.log(JSON.stringify({textIssues},null,2));process.exitCode=2;return;}
 const result=cp.spawnSync(process.env.PYTHON||process.env.NOTEBOOK_PYTHON||'python',[path.join(__dirname,'convert_notebook_images.py'),'--repo-dir',repo,'--work-dir',base],{encoding:'utf8',windowsHide:true,maxBuffer:4*1024*1024});
 assert(result.status===0,result.stderr||result.stdout||'conversion failed');
 console.log(result.stdout);
})().catch(e=>{console.error(e.stack||e);process.exitCode=1});
