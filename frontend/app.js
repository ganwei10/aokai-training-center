const API = window.API_BASE || '/api';
const LV = {
  '初级': {c:'lv1', t:'初级', en:'Beginner'},
  '中级': {c:'lv2', t:'中级', en:'Intermediate'},
  '高阶': {c:'lv3', t:'高阶', en:'Advanced'},
  '总览': {c:'gen', t:'总览', en:'Overview'},
};
const I18N = {
  zh: {
    brand_sub:'肉类食品加工数字化 · 产品与技术培训平台',
    search_ph:'搜索教材、资源、关键词…',
    tab_materials:'内部教材', tab_resources:'外链资源库',
    drawer_title:'奥楷培训学习中心',
    level_label:'级别', all:'全部', lv1:'初级', lv2:'中级', lv3:'高阶', lv0:'总览',
    res_audience:'适用人群', res_type:'资源类型',
    cat_presale:'售前', cat_sales:'销售', cat_service:'售后', cat_general:'通用',
    note_label:'教材备注：',
    home_title:'欢迎来到奥楷培训学习中心',
    home_intro:'肉类食品加工数字化设备（灌装/扎线/扭结、包装、码垛）产品与技术培训平台。所有外部链接内容已下载归档，可离线学习。',
    home_res_desc:'33 篇全网产品与技术培训资料 + 18 个培训视频，已归档可离线学习',
    prev:'← 上一篇', next:'下一篇 →',
    placeholder_res:'从左侧选择资源查看详情',
    loading:'加载中…', notfound:'未找到该教材', notfound_res:'未找到该资源',
    search_empty:'无匹配结果',
  },
  en: {
    brand_sub:'Meat-Processing Digitalization · Product & Tech Training Platform',
    search_ph:'Search materials, resources, keywords…',
    tab_materials:'Materials', tab_resources:'Resource Library',
    drawer_title:'Aokai Training Center',
    level_label:'Level', all:'All', lv1:'Beginner', lv2:'Intermediate', lv3:'Advanced', lv0:'Overview',
    res_audience:'Audience', res_type:'Type',
    cat_presale:'Pre-sales', cat_sales:'Sales', cat_service:'Service', cat_general:'General',
    note_label:'Note: ',
    home_title:'Welcome to Aokai Training Center',
    home_intro:'A training platform for meat-processing digitalization equipment (filling / linking / twisting, packaging, palletizing) — products & technology. All external links are downloaded and archived for offline learning.',
    home_res_desc:'33 web training resources + 18 training videos, archived for offline learning',
    prev:'← Prev', next:'Next →',
    placeholder_res:'Select a resource from the left',
    loading:'Loading…', notfound:'Material not found', notfound_res:'Resource not found',
    search_empty:'No matches',
  }
};

let STATE = { tab:'materials', level:'', cat:'', plat:'', materials:[], cats:[], lang:'zh' };

const $ = s => document.querySelector(s);
const el = (tag, cls, html) => { const e=document.createElement(tag); if(cls)e.className=cls; if(html!=null)e.innerHTML=html; return e; };

function t(key){ return (I18N[STATE.lang] && I18N[STATE.lang][key]!=null) ? I18N[STATE.lang][key] : (I18N.zh[key]||key); }
function lvLabel(lv){ const o = LV[lv] || {c:'gen', t:lv, en:lv}; return STATE.lang==='en' ? o.en : o.t; }
function withLang(path){
  if(path.indexOf('lang=') !== -1) return path;
  const sep = path.indexOf('?') !== -1 ? '&' : '?';
  return path + sep + 'lang=' + STATE.lang;
}
async function get(path){ const r = await fetch(API + withLang(path)); if(!r.ok) throw new Error(path+' '+r.status); return r.json(); }

/* ---------- 初始化 ---------- */
async function init(){
  try { STATE.lang = localStorage.getItem('aokai_lang') || 'zh'; } catch(e){ STATE.lang='zh'; }
  const lb = $('#langBtn'); if(lb) lb.textContent = STATE.lang==='en' ? '中' : 'EN';
  bindEvents();
  try { STATE.cats = await get('/categories'); } catch(e){ STATE.cats=[]; }
  applyI18n();
  await route();
  window.addEventListener('hashchange', route);
}

function bindEvents(){
  $('#tabMaterials').onclick = () => switchTab('materials');
  $('#tabResources').onclick = () => switchTab('resources');
  $('#menuBtn').onclick = () => { syncStabs(STATE.tab); $('#sidebar').classList.toggle('open'); $('#overlay').classList.toggle('hidden'); };
  $('#overlay').onclick = () => closeDrawer();
  $('#drawerClose').onclick = () => closeDrawer();
  $('#langBtn').onclick = () => setLang(STATE.lang==='zh' ? 'en' : 'zh');
  document.querySelectorAll('.stab').forEach(b => b.onclick = () => switchTab(b.dataset.tab));

  // 级别筛选（教材与资源库共用 STATE.level，两处筛选条同步）
  $('#levelFilter').querySelectorAll('.chip').forEach(c=> c.onclick = () => setLevel(c.dataset.level));
  $('#resLevelFilter').querySelectorAll('.chip').forEach(c=> c.onclick = () => setLevel(c.dataset.level));
  // 资源分类
  $('#resCatFilter').querySelectorAll('.chip').forEach(c=>{
    c.onclick = () => { STATE.cat=c.dataset.cat;
      $('#resCatFilter').querySelectorAll('.chip').forEach(x=>x.classList.remove('active'));
      c.classList.add('active'); loadResources(); };
  });
  // 资源类型（动态填充后绑定在 loadResources 中）

  // 搜索
  const si = $('#searchInput'); let t;
  si.addEventListener('input', ()=>{ clearTimeout(t); t=setTimeout(doSearch, 250); });
  si.addEventListener('blur', ()=> setTimeout(()=> $('#searchResults').classList.add('hidden'), 200));
}

function switchTab(tab){
  STATE.tab = tab;
  $('#tabMaterials').classList.toggle('active', tab==='materials');
  $('#tabResources').classList.toggle('active', tab==='resources');
  syncStabs(tab);
  $('#sideMaterials').classList.toggle('hidden', tab!=='materials');
  $('#sideResources').classList.toggle('hidden', tab!=='resources');
  if(tab==='materials'){ renderCatList(); }
  else { loadResources(); }
  if(location.hash==='#/home' || !location.hash) location.hash = tab==='materials' ? '#/home' : '#/resources';
}
function syncStabs(tab){
  document.querySelectorAll('.stab').forEach(b => b.classList.toggle('active', b.dataset.tab===tab));
}
function closeDrawer(){
  $('#sidebar').classList.remove('open');
  $('#overlay').classList.add('hidden');
}
function applyI18n(){
  document.querySelectorAll('[data-i18n]').forEach(e=>{ const k=e.getAttribute('data-i18n'); if(I18N[STATE.lang] && I18N[STATE.lang][k]!=null) e.textContent = I18N[STATE.lang][k]; });
  document.querySelectorAll('[data-i18n-ph]').forEach(e=>{ const k=e.getAttribute('data-i18n-ph'); if(I18N[STATE.lang] && I18N[STATE.lang][k]!=null) e.setAttribute('placeholder', I18N[STATE.lang][k]); });
  document.title = (I18N[STATE.lang] && I18N[STATE.lang].drawer_title) || 'Aokai Training Center';
  document.documentElement.lang = STATE.lang==='en' ? 'en' : 'zh-CN';
}
function setLevel(level){
  STATE.level = level;
  ['#levelFilter', '#resLevelFilter'].forEach(sel=>{
    $(sel).querySelectorAll('.chip').forEach(x=> x.classList.toggle('active', x.dataset.level===level));
  });
  if(STATE.tab==='materials'){ renderCatList(); }
  else { loadResources(); }
}
function setLang(lang){
  STATE.lang = lang;
  try { localStorage.setItem('aokai_lang', lang); } catch(e){}
  const b = $('#langBtn'); if(b) b.textContent = lang==='en' ? '中' : 'EN';
  applyI18n();
  get('/categories').then(cats=>{ STATE.cats = cats; return route(); }).catch(()=> route());
}

/* ---------- 教材侧栏 ---------- */
async function loadMaterials(){
  STATE.materials = await get('/materials' + (STATE.level?('?level='+STATE.level):''));
}
function renderCatList(){
  const box = $('#catList'); box.innerHTML='';
  const groups = STATE.cats.filter(c=>c.key!=='general').concat(STATE.cats.filter(c=>c.key==='general'));
  groups.forEach(cat=>{
    const items = STATE.materials.filter(m=>m.group_key===cat.key && (!STATE.level || m.level===STATE.level));
    if(!items.length) return;
    const wrap = el('div','cat');
    const head = el('div','cat-head', `<span class="dot"></span>${cat.name}<span class="cnt">${items.length}</span>`);
    const body = el('div','cat-body');
    items.forEach(m=>{
      const lv = LV[m.level]||{c:'gen',t:m.level};
      const a = el('a', '', `${m.title}<span class="badge ${lv.c}">${lvLabel(m.level)}</span>`);
      a.href = '#/material/'+m.slug;
      a.dataset.slug = m.slug;
      a.onclick = () => closeDrawer();
      body.appendChild(a);
    });
    wrap.appendChild(head); wrap.appendChild(body); box.appendChild(wrap);
    head.onclick = ()=> body.classList.toggle('hidden');
  });
  // 高亮当前
  const cur = location.hash.match(/#\/material\/(.+)/);
  if(cur) box.querySelectorAll('a').forEach(a=> a.classList.toggle('active', a.dataset.slug===cur[1]));
}

/* ---------- 资源库 ---------- */
let PLATS = [];
async function loadResources(){
  const q = new URLSearchParams();
  if(STATE.cat) q.set('category', STATE.cat);
  if(STATE.plat) q.set('platform', STATE.plat);
  if(STATE.level) q.set('level', STATE.level);
  const list = await get('/resources' + (q.toString()?'?'+q.toString():''));
  // 收集平台用于筛选
  const plats = [...new Set(list.map(r=>r.platform))].sort();
  if(plats.length!==PLATS.length || plats.some((p,i)=>p!==PLATS[i])){
    PLATS = plats; renderPlatFilter();
  }
  const box = $('#resList'); box.innerHTML='';
  if(!list.length){ box.appendChild(el('div','placeholder','该筛选下暂无资源')); return; }
  list.forEach(r=>{
    const item = el('div','res-item');
    const fail = r.status && r.status!=='ok' && !r.video_url;
    item.innerHTML = `<div class="rt">${r.video_url?'🎬 ':''}${esc(r.title||r.domain)}</div>
      <div class="rmeta">
        <span class="pf">${esc(r.platform)}</span>
        <span>${esc(r.category)}</span>
        ${(r.levels||[]).map(l=>`<span class="badge ${LV[l]?LV[l].c:'gen'}">${lvLabel(l)}</span>`).join('')}
        ${r.video_url?`<span class="st-video">视频</span>`:(r.word_count?`<span>${r.word_count} 字</span>`:'')}
        ${fail?`<span class="st-fail">仅链接</span>`:''}
      </div>`;
    item.onclick = ()=>{ closeDrawer(); location.hash = '#/resource/'+r.id; };
    box.appendChild(item);
  });
}
function renderPlatFilter(){
  const fg = $('#resPlatFilter');
  fg.querySelectorAll('.chip[data-plat]').forEach(c=>c.remove());
  PLATS.forEach(p=>{
    const c = el('button','chip', p); c.dataset.plat=p;
    if(STATE.plat===p) c.classList.add('active');
    c.onclick = ()=>{ STATE.plat=p;
      fg.querySelectorAll('.chip').forEach(x=>x.classList.remove('active')); c.classList.add('active'); loadResources(); };
    fg.appendChild(c);
  });
}

/* ---------- 内容渲染 ---------- */
async function showMaterial(slug){
  const m = await get('/materials/'+slug);
  const lv = LV[m.level]||{c:'gen',t:m.level};
  $('#content').innerHTML = `
    <div class="doc-head"><h1>${esc(m.title)}</h1><span class="badge ${lv.c}">${lvLabel(m.level)}</span></div>
    <div class="doc-meta">${esc(m.group_name)} · ${t('tab_materials')}</div>
    <div class="doc-body">${m.html}</div>
    <div class="pager">
      <a class="${m.prev?'':'disabled'}" href="${m.prev?'#/material/'+m.prev:''}">${m.prev?t('prev'):''}</a>
      <a class="${m.next?'':'disabled'}" href="${m.next?'#/material/'+m.next:''}">${m.next?t('next'):''}</a>
    </div>`;
  // 表格横向滚动容器（移动端友好）；正文外链新标签页打开，站内缓存链接保持 SPA 跳转
  $('#content').querySelectorAll('.doc-body table').forEach(t=>{
    const w = el('div','table-wrap'); t.parentNode.insertBefore(w, t); w.appendChild(t);
  });
  $('#content').querySelectorAll('.doc-body a').forEach(a=>{
    const href = a.getAttribute('href') || '';
    if(href.startsWith('http')){ a.target='_blank'; a.rel='noopener'; }
    if(!a.classList.contains('ext-local')) a.classList.add('ext');
  });
  renderCatList();
}
async function showResource(id){
  const r = await get('/resources/'+id);
  const isVideo = !!r.video_url;
  const mediaHtml = isVideo
    ? `<div class="video-wrap"><iframe src="${toEmbed(r.video_url)}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe></div>`
    : '';
  const fail = r.status && r.status!=='ok' && !isVideo;
  const bodyHtml = fail
    ? `<div class="body">${STATE.lang==='en'
        ? 'The full text of this external resource was not captured. Please visit the original page via the button below.'
        : '该外部资源暂未成功抓取正文，请通过下方按钮访问原页面查看完整内容。'}<br><br>${t('note_label')}${esc(r.note||'')}</div>`
    : (isVideo ? '' : `<div class="body">${linkify(r.body || (STATE.lang==='en'?'（No content）':'（无正文）'))}</div>`);
  $('#content').innerHTML = `
    <div class="res-detail">
      <h1>${esc(r.title||r.domain)}</h1>
      <div class="meta">${STATE.lang==='en'?'Source':'来源'}：${esc(r.domain)} · ${STATE.lang==='en'?'Type':'类型'}：${esc(r.platform)} · ${STATE.lang==='en'?'For':'适用'}：${esc(r.category)}
        ${(r.levels||[]).map(l=>'· '+lvLabel(l)).join('')}${isVideo?' · 🎬 '+(STATE.lang==='en'?'Training video':'培训视频'):''}</div>
      ${r.note?`<div class="note"><strong>${t('note_label')}</strong>${esc(r.note)}</div>`:''}
      ${mediaHtml}
      ${bodyHtml}
      <a class="ext-link" href="${esc(r.url)}" target="_blank" rel="noopener">${isVideo
        ? (STATE.lang==='en' ? 'Open on '+(r.domain||'source')+' ↗' : '在'+(r.domain||'原平台')+'打开 ↗')
        : (STATE.lang==='en' ? 'Open original page ↗' : '访问原页面 ↗')}</a>
    </div>`;
}
// 将视频链接转为可嵌入播放器地址
function toEmbed(url){
  let m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/);
  if(m) return 'https://www.youtube.com/embed/'+m[1];
  m = url.match(/bilibili\.com\/video\/(BV[\w]+)/);
  if(m) return 'https://player.bilibili.com/player.html?bvid='+m[1]+'&autoplay=0&high_quality=1';
  return url;
}
// 资源正文：转义后把 URL 变为可点击链接（换行由 .body 的 white-space:pre-wrap 处理）
function linkify(text){
  if(!text) return '';
  const e = esc(text);
  return e.replace(/(https?:\/\/[^\s<>"'）)，。、；：]+)/g,
    '<a href="$1" target="_blank" rel="noopener">$1</a>');
}
function showHome(){
  const groups = STATE.cats;
  let html = `<h1 style="color:var(--blue);margin-top:0">${t('home_title')}</h1>
    <p style="color:var(--muted)">${t('home_intro')}</p>
    <div class="home-cards">`;
  groups.forEach(c=>{ html += `<div class="home-card" data-go="#/material/${c.key==='general'?'README':firstSlugOf(c.key)}">
      <div class="ic">🎯</div><h3>${esc(c.name)}</h3><p>${esc(c.blurb)} · ${c.material_count} ${STATE.lang==='en'?'items':'篇'}</p></div>`; });
  html += `<div class="home-card" data-go="#/resources"><div class="ic">🔗</div><h3>${t('tab_resources')}</h3><p>${t('home_res_desc')}</p></div>`;
  html += `</div>`;
  $('#content').innerHTML = html;
  $('#content').querySelectorAll('.home-card').forEach(card=> card.onclick=()=> location.hash=card.dataset.go);
}
function firstSlugOf(groupKey){
  const m = STATE.materials.find(x=>x.group_key===groupKey);
  return m? m.slug : 'README';
}

/* ---------- 搜索 ---------- */
async function doSearch(){
  const q = $('#searchInput').value.trim();
  const box = $('#searchResults');
  if(!q){ box.classList.add('hidden'); return; }
  try{
    const r = await get('/search?q='+encodeURIComponent(q));
    box.innerHTML='';
    if(!r.materials.length && !r.resources.length){ box.appendChild(el('div','empty', t('search_empty'))); }
    r.materials.forEach(m=>{ const a=el('a', '', `<span class="sr-kind">教材</span>${esc(m.title)} <small>(${m.group_name}·${m.level})</small>`); a.href='#/material/'+m.slug; box.appendChild(a); });
    r.resources.forEach(res=>{ const a=el('a', '', `<span class="sr-kind res">资源</span>${esc(res.title)} <small>(${esc(res.platform)})</small>`); a.href='#/resource/'+res.id; box.appendChild(a); });
    box.classList.remove('hidden');
  }catch(e){ box.classList.add('hidden'); }
}

/* ---------- 路由 ---------- */
async function route(){
  const h = location.hash || '#/home';
  if(h==='#/home'){ await ensureMaterials(); showHome(); return; }
  if(h==='#/resources'){ switchTab('resources'); await loadResources(); $('#content').innerHTML='<div class="placeholder">'+t('placeholder_res')+'</div>'; return; }
  let m = h.match(/#\/material\/(.+)/);
  if(m){ await ensureMaterials(); if(STATE.tab!=='materials') switchTab('materials'); try{ await showMaterial(m[1]); }catch(e){ $('#content').innerHTML='<div class="placeholder">'+t('notfound')+'</div>'; } return; }
  let r = h.match(/#\/resource\/(.+)/);
  if(r){ switchTab('resources'); try{ await showResource(r[1]); }catch(e){ $('#content').innerHTML='<div class="placeholder">'+t('notfound_res')+'</div>'; } return; }
  showHome();
}
async function ensureMaterials(){ if(!STATE.materials.length) await loadMaterials(); }

function esc(s){ return (s==null?'':String(s)).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

init();
