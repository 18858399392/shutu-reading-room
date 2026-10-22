(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const books = [...window.BOOKS].sort((a,b) => (a.rank || a.id) - (b.rank || b.id));
  const byId = new Map(books.map(book => [book.id, book]));
  const labels = ['封面','三句话','黑板图解'];
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let saved;
  try { saved = new Set(JSON.parse(localStorage.getItem('onebook-saved-v1') || '[]').map(Number)); } catch { saved = new Set(); }
  let current = books[0], page = 0, savedOnly = false, viewerImages = [], viewerIndex = 0, scrollTimer, toastTimer;
  const track = $('#page-track'), dialogs = $$('dialog');
  const bookImages = book => book.images.slice(0,3);
  function notify(message) { clearTimeout(toastTimer); $('#toast').textContent = message; $('#toast').hidden = false; toastTimer = setTimeout(() => { $('#toast').hidden = true; },2200); }
  function syncSaved() { $('#save').setAttribute('aria-pressed', saved.has(current.id)); $('#save').setAttribute('aria-label',`${saved.has(current.id) ? '取消收藏' : '收藏'}《${current.title}》`); $('#saved-count').textContent = saved.size; }
  function openDialog(dialog) { dialog.showModal(); document.body.classList.add('modal-open'); }
  function closeDialog(dialog) { dialog.close(); if (!dialogs.some(item => item.open)) document.body.classList.remove('modal-open'); }
  dialogs.forEach(dialog => { dialog.addEventListener('close',() => { if (!dialogs.some(item => item.open)) document.body.classList.remove('modal-open'); }); dialog.addEventListener('click',event => { if (event.target !== dialog) return; const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeDialog(dialog); }); });
  $$('[data-close]').forEach(button => button.addEventListener('click',() => closeDialog(document.getElementById(button.dataset.close))));
  function syncPage(index) {
    page = Math.max(0,Math.min(2,index));
    $$('.page-tabs [role=tab]').forEach((tab,i) => { tab.setAttribute('aria-selected', i === page); tab.tabIndex = i === page ? 0 : -1; });
    $$('.page > button').forEach((button,i) => { button.tabIndex = i === page ? 0 : -1; });
    $('#page-position').textContent = `0${page + 1} / 03`;
    $('#swipe-text').textContent = page === 2 ? '向右滑动，回看前页 →' : '向左滑动，翻到下一页 ←';
  }
  function goPage(index, focus = false) { index = Math.max(0,Math.min(2,index)); track.scrollTo({left:track.clientWidth*index,behavior:reduceMotion ? 'instant' : 'smooth'}); syncPage(index); if (focus) $(`#tab-${index}`).focus(); }
  track.addEventListener('scroll',() => { clearTimeout(scrollTimer); scrollTimer = setTimeout(() => syncPage(Math.round(track.scrollLeft / track.clientWidth)),75); },{passive:true});
  track.addEventListener('keydown',event => { if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); if (event.target !== track) track.focus({preventScroll:true}); goPage(page + (event.key === 'ArrowRight' ? 1 : -1)); } });
  $$('.page-tabs [role=tab]').forEach(tab => { tab.addEventListener('click',() => goPage(Number(tab.dataset.page))); tab.addEventListener('keydown',event => { if (['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) { event.preventDefault(); goPage(event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (page + (event.key === 'ArrowRight' ? 1 : 2)) % 3,true); } }); });
  new ResizeObserver(() => { track.scrollTo({left:track.clientWidth*page,behavior:'instant'}); }).observe(track);
  function renderDetails(book) {
    const extras = book.extras || book.images.slice(3);
    $('#detail-content').innerHTML = `<h2>${escape(book.tagline)}</h2><p>${escape(book.intro)}</p>${book.ideas.map(idea => `<section class="idea"><h3>${escape(idea.title)}</h3><p>${escape(idea.text)}</p></section>`).join('')}<h3>为什么排在第 ${book.rank || book.id} 名</h3><p>${escape(book.rankReason || '综合长期影响、读者热度和传播广度进行本站编排。')}</p>${(book.correctionNote || book.note) ? `<p class="detail-note">${escape(book.correctionNote || book.note)}</p>` : ''}${extras.length ? `<h3>其他图卡与原素材对照 · ${extras.length} 张</h3><div class="extras">${extras.map((img,index) => `<button class="extra" data-extra="${index}" aria-label="放大${escape(img.label)}"><img src="${escape(img.thumb || img.src)}" width="${img.width}" height="${img.height}" alt="${escape(book.title + ' · ' + img.label)}" loading="lazy"><span>${escape(img.label)}</span></button>`).join('')}</div>` : ''}<p class="detail-note">简介与补充图卡为本站整理，非原书引语。原图归纳保留原样，宜结合原书阅读。${book.sourceUrl ? ` <a href="${escape(book.sourceUrl)}" target="_blank" rel="noopener noreferrer">${escape(book.sourceLabel || '书目信息参考')} ↗</a>` : ''}</p>`;
    $$('.extra').forEach(button => button.addEventListener('click',() => showViewer([...bookImages(book),...extras],3 + Number(button.dataset.extra))));
  }
  function showBook(book,{hash=true,scroll=true} = {}) {
    current = book; page = 0; clearTimeout(scrollTimer); $('#book-details').open = false;
    $('#rank-label').textContent = `综合阅读榜 · 第 ${book.rank || book.id} 名`;
    $('#book-title').textContent = book.title; $('#byline').textContent = `${book.author} / ${book.category}`;
    document.title = `${book.title} · 一书三图`;
    track.innerHTML = bookImages(book).map((img,index) => `<figure class="page" id="page-${index}" role="tabpanel" aria-labelledby="tab-${index}"><button data-image="${index}" aria-label="放大《${escape(book.title)}》${labels[index]}"><img src="${escape(img.src)}" width="${img.width}" height="${img.height}" alt="${escape(book.title)} · ${labels[index]}" ${index ? 'loading="lazy"' : 'fetchpriority="high"'} decoding="async"></button></figure>`).join('');
    track.scrollTo({left:0,behavior:'instant'}); syncPage(0);
    $$('[data-image]').forEach(button => button.addEventListener('click',() => showViewer(bookImages(current),Number(button.dataset.image))));
    renderDetails(book); syncSaved();
    const index = books.indexOf(book); $('#book-position').textContent = `${index+1} / ${books.length}`;
    $('#book-prev').disabled = index === 0; $('#book-next').disabled = index === books.length-1;
    if (hash && location.hash !== `#book-${book.id}`) history.pushState(null,'',`#book-${book.id}`);
    if (scroll) window.scrollTo({top:0,behavior:'instant'});
  }
  $('#save').addEventListener('click',() => { const remove = saved.has(current.id); remove ? saved.delete(current.id) : saved.add(current.id); try { localStorage.setItem('onebook-saved-v1',JSON.stringify([...saved])); } catch { notify('浏览器未允许保存，收藏将在本次浏览中保留'); } syncSaved(); renderCatalog(); notify(remove ? '已取消收藏' : '已加入我的收藏'); });
  $('#book-prev').addEventListener('click',() => showBook(books[books.indexOf(current)-1]));
  $('#book-next').addEventListener('click',() => showBook(books[books.indexOf(current)+1]));
  $('.brand').addEventListener('click',event => { event.preventDefault(); showBook(books[0]); });
  window.addEventListener('hashchange',() => { const match = location.hash.match(/^#book-(\d+)$/); if (match && byId.has(Number(match[1]))) showBook(byId.get(Number(match[1])),{hash:false}); else if (!location.hash) showBook(books[0],{hash:false}); });
  function renderCatalog() {
    const query = $('#search').value.trim().toLocaleLowerCase(), category = $('#category').value;
    const matches = books.filter(book => (!savedOnly || saved.has(book.id)) && (category === '全部' || category === book.category) && (!query || (/^\d+$/.test(query) ? (book.rank || book.id) === Number(query) : `${book.title} ${book.author} ${book.originalTitle || ''} ${book.category} ${book.tagline}`.toLocaleLowerCase().includes(query))));
    $('#result-count').textContent = `${matches.length} 本${matches.length < books.length ? ' / 全库 100 本' : ' · 按综合排名排列'}`;
    $('#catalog-empty').hidden = matches.length > 0;
    $('#catalog-list').innerHTML = matches.map(book => `<li><button class="catalog-item" data-id="${book.id}" data-rank="${book.rank || book.id}" data-top="${book.rank <= 3}" aria-current="${book.id === current.id}" aria-label="第${book.rank || book.id}名 ${escape(book.title)}，${escape(book.author)}"><span class="catalog-rank">${String(book.rank || book.id).padStart(2,'0')}</span><img src="${escape(book.images[0].thumb)}" width="33" height="44" alt="" loading="lazy"><span><strong>${escape(book.title)}</strong><small>${escape(book.author)} · ${escape(book.category)}</small></span><span class="catalog-arrow" aria-hidden="true">↗</span></button></li>`).join('');
    $$('.catalog-item').forEach(button => button.addEventListener('click',() => { closeDialog($('#catalog')); showBook(byId.get(Number(button.dataset.id))); $('#reader').focus({preventScroll:true}); }));
  }
  [...new Set(books.map(book => book.category))].forEach(category => { const option = document.createElement('option'); option.value = category; option.textContent = category; $('#category').append(option); });
  $$('[data-open-catalog]').forEach(button => button.addEventListener('click',() => { renderCatalog(); openDialog($('#catalog')); }));
  $('#search').addEventListener('input',renderCatalog); $('#category').addEventListener('change',renderCatalog);
  $('#filter-saved').addEventListener('click',() => { savedOnly = !savedOnly; $('#filter-saved').setAttribute('aria-pressed',savedOnly); renderCatalog(); });
  $('#reset-filters').addEventListener('click',() => { savedOnly = false; $('#filter-saved').setAttribute('aria-pressed',false); $('#search').value = ''; $('#category').value = '全部'; renderCatalog(); });
  function showMethod() { if ($('#catalog').open) closeDialog($('#catalog')); openDialog($('#method')); }
  ['#method-open','#rank-method','#catalog-method'].forEach(selector => $(selector).addEventListener('click',showMethod));
  const method = window.RANKING_METHOD || {};
  $('#method-content').innerHTML = `<p>在这 100 本书里，综合考虑作品留下的长期影响、读者热度和传播广度，给出一个便于开始阅读的顺序。</p><div class="weights"><div><strong>50%</strong>长期影响</div><div><strong>35%</strong>读者热度</div><div><strong>15%</strong>传播广度</div></div><p>${escape(method.method || '')}</p><p>${escape(method.editorialDisclaimer || '这是本站编辑编排，不是官方榜单，也不是实时销量排名。不同领域之间不存在公认的唯一顺序，排名不代表一本书对每位读者的价值。')}</p><h3>参考依据</h3><ul>${(method.sources || []).map(source => `<li><a href="${escape(source.url)}" target="_blank" rel="noopener noreferrer">${escape(source.label)} ↗</a><br><span class="detail-note">${escape(source.whatSupports)}</span></li>`).join('')}</ul><p class="method-foot">${escape(method.tieBreak || '')}<br>整理日期：${escape(method.asOf || '2026-10-22')} · 排名仅适用于本站这 100 本书。图片及补写简介为阅读索引，不代替原书。</p>`;
  function renderViewer() { const image = viewerImages[viewerIndex]; $('#full-image').src = image.src; $('#full-image').alt = `${current.title} · ${image.label}`; $('#viewer-title').textContent = current.title; $('#viewer-meta').textContent = `${image.label} · ${viewerIndex+1} / ${viewerImages.length}${image.generated ? ' · 原创补充' : ''}`; $('#image-original').href = image.src; $('#image-original').download = `${current.title}-${image.label}.webp`; $('#viewer-canvas').classList.remove('zoomed'); $('#zoom').textContent = '放大细读'; $('#image-prev').disabled = viewerIndex === 0; $('#image-next').disabled = viewerIndex === viewerImages.length-1; }
  function showViewer(images,index) { viewerImages = images; viewerIndex = index; renderViewer(); openDialog($('#viewer')); }
  function moveViewer(delta) { const next = viewerIndex+delta; if (next >= 0 && next < viewerImages.length) { viewerIndex = next; renderViewer(); } }
  $('#fullscreen').addEventListener('click',() => showViewer(bookImages(current),page));
  $('#image-prev').addEventListener('click',() => moveViewer(-1)); $('#image-next').addEventListener('click',() => moveViewer(1));
  function zoom() { const active = $('#viewer-canvas').classList.toggle('zoomed'); $('#zoom').textContent = active ? '适合屏幕' : '放大细读'; }
  $('#zoom').addEventListener('click',zoom); $('#full-image').addEventListener('click',zoom);
  $('#viewer').addEventListener('keydown',event => { if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); moveViewer(event.key === 'ArrowRight' ? 1 : -1); } });
  let touchStart;
  $('#viewer-canvas').addEventListener('touchstart',event => { if (event.touches.length === 1) touchStart = {x:event.touches[0].clientX,y:event.touches[0].clientY}; },{passive:true});
  $('#viewer-canvas').addEventListener('touchend',event => { if (!touchStart || $('#viewer-canvas').classList.contains('zoomed')) return; const dx = event.changedTouches[0].clientX-touchStart.x, dy = event.changedTouches[0].clientY-touchStart.y; if (Math.abs(dx)>60 && Math.abs(dx)>Math.abs(dy)*1.5) moveViewer(dx<0 ? 1 : -1); touchStart = null; },{passive:true});
  let installPrompt;
  window.addEventListener('beforeinstallprompt',event => { event.preventDefault(); installPrompt = event; $('#install').hidden = false; });
  $('#install').addEventListener('click',async () => { if (installPrompt) { await installPrompt.prompt(); installPrompt = null; $('#install').hidden = true; } });
  const initial = location.hash.match(/^#book-(\d+)$/);
  showBook(initial && byId.has(Number(initial[1])) ? byId.get(Number(initial[1])) : books[0],{hash:false,scroll:false}); renderCatalog();
  if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) navigator.serviceWorker.register('./sw.js').catch(() => {});
})();
