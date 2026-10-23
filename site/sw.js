const VERSION='onebook-notebook-47ea6e46f78d',SHELL=VERSION+'-shell',IMAGES=VERSION+'-images';
const FILES=['./','./index.html','./index.htm','./style.css','./app.js','./books.js','./manifest.webmanifest','./assets/icon.svg','./assets/icon-192.png','./assets/icon-512.png',...["./style.css?v=2073e2bc04b1", "./app.js?v=f35d3005d20f", "./books.js?v=8dfdef962e99", "./assets/icon.svg?v=36e54ee1f402", "./assets/icon-192.png?v=5668fd0e0ad0", "./assets/icon-512.png?v=09277242d274"]];
self.addEventListener('install',event=>event.waitUntil(caches.open(SHELL).then(cache=>cache.addAll(FILES.map(url=>new Request(url,{cache:'reload'})))).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('onebook-')&&!key.startsWith(VERSION)).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(url.origin!==location.origin||event.request.method!=='GET')return;
  if(/\.(webp|svg|png)$/.test(url.pathname)){
    event.respondWith(caches.open(IMAGES).then(async cache=>{
      const cached=await cache.match(event.request)||await caches.match(event.request);if(cached)return cached;
      const response=await fetch(event.request);
      if(response.ok){await cache.put(event.request,response.clone());const keys=await cache.keys();if(keys.length>300)await cache.delete(keys[0]);}
      return response;
    }));return;
  }
  event.respondWith(fetch(event.request).then(response=>{
    if(response.ok){const clone=response.clone();caches.open(SHELL).then(cache=>cache.put(event.request,clone));}
    return response;
  }).catch(()=>caches.match(event.request).then(response=>response||(event.request.mode==='navigate'?caches.match('./index.html'):Response.error()))));
});
