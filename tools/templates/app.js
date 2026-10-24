(() => {
  'use strict';
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const themeColors = {paper:'#f2eee5',white:'#ffffff',black:'#111111'};
  function setTheme(theme) {
    if (!Object.hasOwn(themeColors,theme)) return;
    document.documentElement.dataset.theme=theme;
    document.documentElement.style.colorScheme=theme==='black' ? 'dark' : 'light';
    $('meta[name="theme-color"]').content=themeColors[theme];
    $$('[data-theme-choice]').forEach(button => button.setAttribute('aria-pressed',button.dataset.themeChoice===theme));
  }
  setTheme(document.documentElement.dataset.theme || 'white');
  $$('[data-theme-choice]').forEach(button => button.addEventListener('click',() => {
    const theme=button.dataset.themeChoice; setTheme(theme);
    try { localStorage.setItem('onebook-theme-v1',theme); } catch {}
  }));
  window.addEventListener('storage',event => { if (event.key==='onebook-theme-v1') setTheme(event.newValue || 'white'); });
  const books = [...window.BOOKS].sort((a,b) => (a.rank || a.id)-(b.rank || b.id));
  const byId = new Map(books.map(b => [b.id,b]));
  const labels = ['视觉封面','三句话解读','黑板图解'];
  const bookmark = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4z"/></svg>';
  let saved;
  try { saved = new Set(JSON.parse(localStorage.getItem('onebook-saved-v1') || '[]').map(Number)); } catch { saved = new Set(); }
  let current = books[0], savedOnly = false, toastTimer, scrollFrame;
  const dialogs = $$('dialog'), imagesFor = b => [...b.images.slice(0,3),...(b.extras || b.images.slice(3))];
  function notify(message) { clearTimeout(toastTimer); $('#toast').textContent = message; $('#toast').hidden = false; toastTimer = setTimeout(() => { $('#toast').hidden = true; },2200); }
  function openDialog(d) { d.showModal(); document.body.classList.add('modal-open'); }
  function closeDialog(d) { d.close(); if (!dialogs.some(x => x.open)) document.body.classList.remove('modal-open'); }
  dialogs.forEach(d => {
    d.addEventListener('close',() => { if (!dialogs.some(x => x.open)) document.body.classList.remove('modal-open'); });
    d.addEventListener('click',e => { if (e.target !== d) return; const r=d.getBoundingClientRect(); if (e.clientX<r.left || e.clientX>r.right || e.clientY<r.top || e.clientY>r.bottom) closeDialog(d); });
  });
  $$('[data-close]').forEach(b => b.addEventListener('click',() => closeDialog(document.getElementById(b.dataset.close))));

  // Keep all books in reading order and let the browser load nearby images only.
  $('#reading-list').innerHTML = books.map((book,bookIndex) => {
    return `<article class="book-entry" id="book-${book.id}" aria-labelledby="title-${book.id}" tabindex="-1">
      <header class="book-heading"><div class="book-heading-copy"><p class="rank-label">综合阅读榜 · 第 ${book.rank || book.id} 名</p><h2 class="book-title" id="title-${book.id}">${escape(book.title)}</h2><p class="byline">${escape(book.author)} <span aria-hidden="true">/</span> ${escape(book.category)}</p></div><button class="save-button" data-save="${book.id}" aria-pressed="false" aria-label="收藏《${escape(book.title)}》">${bookmark}</button></header>
      <div class="book-gallery" aria-label="《${escape(book.title)}》三幅图">${book.images.slice(0,3).map((img,index) => `<figure class="book-figure"><figcaption><span class="figure-index">0${index+1}</span><span class="figure-label">${labels[index]}</span><span class="figure-hint">点击放大 ↗</span></figcaption><button class="image-button" data-book="${book.id}" data-image="${index}" aria-label="放大《${escape(book.title)}》${labels[index]}"><img src="${escape(img.src)}" width="${img.width}" height="${img.height}" alt="${escape(book.title)} · ${labels[index]}" ${bookIndex===0 && index===0 ? 'fetchpriority="high"' : 'loading="lazy"'} decoding="async"></button></figure>`).join('')}</div>
      <div class="book-copy"><div class="book-intro"><h3>${escape(book.tagline)}</h3><p>${escape(book.intro)}</p></div><div class="ideas-grid">${book.ideas.map(idea => `<section class="idea"><h3>${escape(idea.title)}</h3><p>${escape(idea.text)}</p></section>`).join('')}</div><p class="rank-reason"><span>排名说明</span>${escape(book.rankReason || '综合长期影响、读者热度和传播广度进行本站编排。')}</p>${(book.correctionNote || book.note) ? `<p class="detail-note">${escape(book.correctionNote || book.note)}</p>` : ''}</div>
      </article>`;
  }).join('');
  const entries = books.map(b => document.getElementById(`book-${b.id}`));
  function syncSaved() {
    $$('[data-save]').forEach(button => { const b=byId.get(Number(button.dataset.save)), active=saved.has(b.id); button.setAttribute('aria-pressed',active); button.setAttribute('aria-label',`${active ? '取消收藏' : '收藏'}《${b.title}》`); });
    $('#saved-count').textContent = saved.size;
  }
  function setCurrent(book,{hash=false}={}) {
    current=book; $('#book-position').textContent=`${books.indexOf(book)+1} / ${books.length}`; $('#current-title').textContent=book.title;
    if (hash && location.hash!==`#book-${book.id}`) history.replaceState(null,'',`#book-${book.id}`);
  }
  function jumpTo(book,{hash=true,focus=true}={}) {
    const entry=document.getElementById(`book-${book.id}`);
    if (hash && location.hash!==`#book-${book.id}`) history.pushState(null,'',`#book-${book.id}`);
    if (focus) entry.focus({preventScroll:true});
    entry.scrollIntoView({block:'start',behavior:'instant'}); setCurrent(book);
  }
  function updateProgress() {
    scrollFrame=null;
    // Binary search avoids scanning every full article on each scroll frame.
    let low=0, high=entries.length-1;
    while (low<high) { const mid=Math.ceil((low+high)/2); if (entries[mid].getBoundingClientRect().top<=100) low=mid; else high=mid-1; }
    if (current!==books[low]) setCurrent(books[low],{hash:true});
  }
  window.addEventListener('scroll',() => { if (!scrollFrame) scrollFrame=requestAnimationFrame(updateProgress); },{passive:true});
  window.addEventListener('resize',() => { if (!scrollFrame) scrollFrame=requestAnimationFrame(updateProgress); });
  window.addEventListener('hashchange',() => { const m=location.hash.match(/^#book-(\d+)$/); if (m && byId.has(Number(m[1]))) jumpTo(byId.get(Number(m[1])),{hash:false}); else if (!location.hash) { window.scrollTo({top:0,behavior:'instant'}); setCurrent(books[0]); } });
  $('.brand').addEventListener('click',e => { e.preventDefault(); history.pushState(null,'',location.pathname+location.search); window.scrollTo({top:0,behavior:'instant'}); setCurrent(books[0]); });
  $('#back-top').addEventListener('click',() => { history.replaceState(null,'',location.pathname+location.search); window.scrollTo({top:0,behavior:'instant'}); setCurrent(books[0]); $('.brand').focus({preventScroll:true}); });
  $('#reading-list').addEventListener('click',e => {
    const button=e.target.closest('[data-save]');
    if (button) { const id=Number(button.dataset.save), remove=saved.has(id); remove ? saved.delete(id) : saved.add(id); try { localStorage.setItem('onebook-saved-v1',JSON.stringify([...saved])); } catch { notify('浏览器未允许保存，收藏将在本次浏览中保留'); } syncSaved(); if ($('#catalog').open) renderCatalog(); notify(remove ? '已取消收藏' : '已加入我的收藏'); return; }
    const image=e.target.closest('[data-image]'); if (image) showViewer(byId.get(Number(image.dataset.book)),Number(image.dataset.image));
  });

  function renderCatalog() {
    const query=$('#search').value.trim().toLocaleLowerCase(), category=$('#category').value;
    const matches=books.filter(b => (!savedOnly || saved.has(b.id)) && (category==='全部' || category===b.category) && (!query || (/^\d+$/.test(query) ? (b.rank || b.id)===Number(query) : `${b.title} ${b.author} ${b.originalTitle || ''} ${b.category} ${b.tagline}`.toLocaleLowerCase().includes(query))));
    $('#result-count').textContent=`${matches.length} 本${matches.length<books.length ? ' / 全库 100 本' : ' · 按综合排名排列'}`; $('#catalog-empty').hidden=matches.length>0;
    $('#catalog-list').innerHTML=matches.map(b => `<li><button class="catalog-item" data-id="${b.id}" data-rank="${b.rank || b.id}" data-top="${b.rank<=3}" aria-current="${b.id===current.id}" aria-label="第${b.rank || b.id}名 ${escape(b.title)}，${escape(b.author)}"><span class="catalog-rank">${String(b.rank || b.id).padStart(2,'0')}</span><img src="${escape(b.images[0].thumb)}" width="33" height="44" alt="" loading="lazy"><span><strong>${escape(b.title)}</strong><small>${escape(b.author)} · ${escape(b.category)}</small></span><span class="catalog-arrow" aria-hidden="true">↘</span></button></li>`).join('');
  }
  $('#catalog-list').addEventListener('click',e => { const b=e.target.closest('[data-id]'); if (b) { closeDialog($('#catalog')); jumpTo(byId.get(Number(b.dataset.id))); } });
  [...new Set(books.map(b => b.category))].forEach(category => { const option=document.createElement('option'); option.value=category; option.textContent=category; $('#category').append(option); });
  $$('[data-open-catalog]').forEach(b => b.addEventListener('click',() => { renderCatalog(); openDialog($('#catalog')); }));
  $('#search').addEventListener('input',renderCatalog); $('#category').addEventListener('change',renderCatalog);
  $('#filter-saved').addEventListener('click',() => { savedOnly=!savedOnly; $('#filter-saved').setAttribute('aria-pressed',savedOnly); renderCatalog(); });
  $('#reset-filters').addEventListener('click',() => { savedOnly=false; $('#filter-saved').setAttribute('aria-pressed',false); $('#search').value=''; $('#category').value='全部'; renderCatalog(); });
  function showMethod() { if ($('#catalog').open) closeDialog($('#catalog')); openDialog($('#method')); }
  ['#method-open','#rank-method','#catalog-method'].forEach(s => $(s).addEventListener('click',showMethod));
  const method=window.RANKING_METHOD || {};
  $('#method-content').innerHTML=`<p>在这 100 本书里，综合考虑作品留下的长期影响、读者热度和传播广度，给出一个便于开始阅读的顺序。</p><div class="weights"><div><strong>50%</strong>长期影响</div><div><strong>35%</strong>读者热度</div><div><strong>15%</strong>传播广度</div></div><p>${escape(method.method || '')}</p><p>${escape(method.editorialDisclaimer || '这是本站编辑编排，不是官方榜单，也不是实时销量排名。不同领域之间不存在公认的唯一顺序，排名不代表一本书对每位读者的价值。')}</p><h3>参考依据</h3><ul>${(method.sources || []).map(s => `<li><a href="${escape(s.url)}" target="_blank" rel="noopener noreferrer">${escape(s.label)} ↗</a><br><span class="detail-note">${escape(s.whatSupports)}</span></li>`).join('')}</ul><p class="method-foot">${escape(method.tieBreak || '')}<br>整理日期：${escape(method.asOf || '2026-10-22')} · 排名仅适用于本站这 100 本书。图片及补写简介为阅读索引，不代替原书。</p>`;
  function showViewer(book,index) {
    const img=imagesFor(book)[index]; $('#full-image').src=img.src; $('#full-image').alt=`${book.title} · ${img.label}`; $('#viewer-title').textContent=book.title;
    $('#viewer-meta').textContent=`${img.label}${img.aiGenerated ? ' · AI 原创图解' : img.generated ? ' · 原创补充' : ''}`;
    $('#image-original').href=img.src; $('#image-original').download=`${book.title}-${img.label}.webp`;
    $('#viewer-canvas').classList.remove('zoomed'); $('#viewer-canvas').scrollTo(0,0); $('#zoom').textContent='放大细读'; openDialog($('#viewer'));
  }
  function zoom() { const active=$('#viewer-canvas').classList.toggle('zoomed'); $('#zoom').textContent=active ? '适合屏幕' : '放大细读'; }
  $('#zoom').addEventListener('click',zoom); $('#full-image').addEventListener('click',zoom);
  let installPrompt;
  window.addEventListener('beforeinstallprompt',e => { e.preventDefault(); installPrompt=e; $('#install').hidden=false; });
  $('#install').addEventListener('click',async () => { if (installPrompt) { await installPrompt.prompt(); installPrompt=null; $('#install').hidden=true; } });
  syncSaved(); setCurrent(books[0]); renderCatalog();
  const initial=location.hash.match(/^#book-(\d+)$/);
  if (initial && byId.has(Number(initial[1]))) requestAnimationFrame(() => jumpTo(byId.get(Number(initial[1])),{hash:false,focus:false}));
  if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) navigator.serviceWorker.register('./sw.js').catch(() => {});
})();
