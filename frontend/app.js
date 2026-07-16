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
    tab_materials:'内部教材', tab_resources:'外链资源库', tab_company:'公司资料',
    drawer_title:'奥楷培训学习中心',
    level_label:'级别', all:'全部', lv1:'初级', lv2:'中级', lv3:'高阶', lv0:'总览',
    res_audience:'适用人群', res_type:'资源类型',
    cat_presale:'售前', cat_sales:'销售', cat_service:'售后', cat_general:'通用',
    comp_docs:'公司文档', comp_std:'相关国家标准',
    note_label:'教材备注：',
    home_title:'欢迎来到奥楷培训学习中心',
    home_intro:'肉类食品加工数字化设备（灌装/扎线/扭结、包装、码垛）产品与技术培训平台。所有外部链接内容已下载归档，可离线学习。',
    home_res_desc:'33 篇全网产品与技术培训资料 + 18 个培训视频，已归档可离线学习',
    home_comp_desc:'奥楷官方原始文档与国家标准合集，可下载 / 在线阅读',
    prev:'← 上一篇', next:'下一篇 →',
    placeholder_res:'从左侧选择资源查看详情',
    loading:'加载中…', notfound:'未找到该教材', notfound_res:'未找到该资源', notfound_std:'未找到该标准',
    search_empty:'无匹配结果',
    std_download:'下载原始文档', std_view:'在线阅读',
  },
  en: {
    brand_sub:'Meat-Processing Digitalization · Product & Tech Training Platform',
    search_ph:'Search materials, resources, keywords…',
    tab_materials:'Materials', tab_resources:'Resource Library', tab_company:'Company',
    drawer_title:'Aokai Training Center',
    level_label:'Level', all:'All', lv1:'Beginner', lv2:'Intermediate', lv3:'Advanced', lv0:'Overview',
    res_audience:'Audience', res_type:'Type',
    cat_presale:'Pre-sales', cat_sales:'Sales', cat_service:'Service', cat_general:'General',
    comp_docs:'Company Docs', comp_std:'National Standards',
    note_label:'Note: ',
    home_title:'Welcome to Aokai Training Center',
    home_intro:'A training platform for meat-processing digitalization equipment (filling / linking / twisting, packaging, palletizing) — products & technology. All external links are downloaded and archived for offline learning.',
    home_res_desc:'33 web training resources + 18 training videos, archived for offline learning',
    home_comp_desc:'Aokai official documents & national standards — download / read online',
    prev:'← Prev', next:'Next →',
    placeholder_res:'Select a resource from the left',
    loading:'Loading…', notfound:'Material not found', notfound_res:'Resource not found', notfound_std:'Standard not found',
    search_empty:'No matches',
    std_download:'Download', std_view:'Read',
  }
};

let STATE = { tab:'materials', level:'', cat:'', plat:'', materials:[], cats:[], lang:'zh', company:null };

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
  $('#tabCompany').onclick = () => switchTab('company');
  $('#menuBtn').onclick = () => { syncStabs(STATE.tab); $('#sidebar').classList.toggle('open'); $('#overlay').classList.toggle('hidden'); };
  $('#overlay').onclick = () => closeDrawer();
  $('#drawerClose').onclick = () => closeDrawer();
  $('#langBtn').onclick = () => setLang(STATE.lang==='zh' ? 'en' : 'zh');
  document.querySelectorAll('.stab').forEach(b => b.onclick = () => switchTab(b.dataset.tab));

  $('#levelFilter').querySelectorAll('.chip').forEach(c=> c.onclick = () => setLevel(c.dataset.level));
  $('#resLevelFilter').querySelectorAll('.chip').forEach(c=> c.onclick = () => setLevel(c.dataset.level));
  $('#resCatFilter').querySelectorAll('.chip').forEach(c=>{
    c.onclick = () => { STATE.cat=c.dataset.cat;
      $('#resCatFilter').querySelectorAll('.chip').forEach(x=>x.classList.remove('active'));
      c.classList.add('active'); loadResources(); };
  });

  const si = $('#searchInput'); let tm;
  si.addEventListener('input', ()=>{ clearTimeout(tm); tm=setTimeout(doSearch, 250); });
  si.addEventListener('blur', ()=> setTimeout(()=> $('#searchResults').classList.add('hidden'), 200));
}

function setTabUI(tab){
  STATE.tab = tab;
  $('#tabMaterials').classList.toggle('active', tab==='materials');
  $('#tabResources').classList.toggle('active', tab==='resources');
  $('#tabCompany').classList.toggle('active', tab==='company');
  syncStabs(tab);
  $('#sideMaterials').classList.toggle('hidden', tab!=='materials');
  $('#sideResources').classList.toggle('hidden', tab!=='resources');
  $('#sideCompany').classList.toggle('hidden', tab!=='company');
}
function switchTab(tab){
  setTabUI(tab);
  if(tab==='materials'){ renderCatList(); }
  else if(tab==='resources'){ loadResources(); }
  else if(tab==='company'){ renderCompanySidebar(STATE.company||{}); ensureCompany().then(renderCompanySidebar).then(showCompany); }
  if(location.hash==='#/home' || !location.hash) location.hash = tab==='materials' ? '#/home' : (tab==='resources'?'#/resources':'#/company');
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
  const cur = location.hash.match(/#\/material\/(.+)/);
  if(cur) box.querySelectorAll('a').forEach(a=> a.classList.toggle('active', a.dataset.slug===cur[1]));
}

/* ---------- 资源库 ---------- */
let PLATS = [];
async function loadResources(){
  const q = new URLSearchParams();
  if(STATE.cat) q.set('category', STATE.cat);
  if(STATE.plat) q.set('type', STATE.plat);
  if(STATE.level) q.set('level', STATE.level);
  const list = await get('/resources' + (q.toString()?'?'+q.toString():''));
  const types = [...new Set(list.map(r=>r.type))].sort();
  if(types.length!==PLATS.length || types.some((p,i)=>p!==PLATS[i])){
    PLATS = types; renderPlatFilter();
  }
  const box = $('#resList'); box.innerHTML='';
  if(!list.length){ box.appendChild(el('div','placeholder','该筛选下暂无资源')); return; }
  list.forEach(r=>{
    const item = el('div','res-item');
    const fail = r.status && r.status!=='ok' && !r.video_url;
    item.innerHTML = `<div class="rt">${r.video_url?'🎬 ':''}${esc(r.title||r.domain)}</div>
      <div class="rmeta">
        <span class="pf">${esc(r.type||r.platform)}</span>
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

/* ---------- 公司资料侧栏 + 页面 ---------- */
async function ensureCompany(){
  if(!STATE.company){ STATE.company = await get('/company'); }
  return STATE.company;
}
function renderCompanySidebar(data){
  const dl = $('#compDocList'); dl.innerHTML='';
  (data.docs||[]).forEach(d=>{
    const item = el('div','res-item');
    item.innerHTML = `<div class="rt">${esc(d.title)}</div><div class="rmeta"><span class="pf">${d.kind==='file'?'PDF':'简介'}</span></div>`;
    item.onclick = ()=>{ closeDrawer(); if(d.kind==='file'){ window.open(d.asset,'_blank'); } else { location.hash='#/company'; } };
    dl.appendChild(item);
  });
  const sl = $('#compStdList'); sl.innerHTML='';
  (data.standards||[]).forEach(s=>{
    const item = el('div','res-item');
    item.innerHTML = `<div class="rt">${esc(s.code)}</div><div class="rmeta"><span>${esc(s.title.replace(/^[^】]*】/,'')).slice(0,18)}</span></div>`;
    item.onclick = ()=>{ closeDrawer(); location.hash='#/standard/'+s.id; };
    sl.appendChild(item);
  });
}
async function showCompany(){
  const data = await ensureCompany();
  let html = `<div class="doc-body company-page">${data.intro_html||''}</div>`;
  // 资料下载
  const files = (data.docs||[]).filter(d=>d.kind==='file');
  if(files.length){
    html += `<h2 class="sec">📎 ${t('comp_docs')}</h2><div class="file-grid">`;
    files.forEach(d=>{
      html += `<div class="file-card">
        <div class="fc-title">${esc(d.title)}</div>
        <div class="fc-actions">
          <a class="ext-link sm" href="${esc(d.asset)}" target="_blank" rel="noopener">${t('std_view')} ↗</a>
          <a class="ext-link sm ghost" href="${esc(d.asset)}" download>${t('std_download')} ↓</a>
        </div></div>`;
    });
    html += `</div>`;
  }
  // 相关国家标准
  if((data.standards||[]).length){
    html += `<h2 class="sec">📐 ${t('comp_std')}</h2><div class="std-grid">`;
    data.standards.forEach(s=>{
      html += `<a class="std-card" href="#/standard/${esc(s.id)}">
        <div class="sc-code">${esc(s.code)}</div>
        <div class="sc-title">${esc(s.title.replace(/^[^】]*】/,''))}</div></a>`;
    });
    html += `</div>`;
  }
  $('#content').innerHTML = html;
  wrapTables();
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
  wrapTables();
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
    : (isVideo ? '' : `<div class="body">${linkify(cleanBody(r.body || (STATE.lang==='en'?'（No content）':'（无正文）')))}</div>`);
  $('#content').innerHTML = `
    <div class="res-detail">
      <h1>${esc(r.title||r.domain)}</h1>
      <div class="meta">${STATE.lang==='en'?'Source':'来源'}：${esc(r.domain)} · ${STATE.lang==='en'?'Type':'类型'}：${esc(r.type||r.platform)} · ${STATE.lang==='en'?'For':'适用'}：${esc(r.category)}
        ${(r.levels||[]).map(l=>'· '+lvLabel(l)).join('')}${isVideo?' · 🎬 '+(STATE.lang==='en'?'Training video':'培训视频'):''}</div>
      ${r.note?`<div class="note"><strong>${t('note_label')}</strong>${esc(r.note)}</div>`:''}
      ${mediaHtml}
      ${bodyHtml}
      <a class="ext-link" href="${esc(r.url)}" target="_blank" rel="noopener">${isVideo
        ? (STATE.lang==='en' ? 'Open on '+(r.domain||'source')+' ↗' : '在'+(r.domain||'原平台')+'打开 ↗')
        : (STATE.lang==='en' ? 'Open original page ↗' : '访问原页面 ↗')}</a>
    </div>`;
}
async function showStandard(code){
  const r = await get('/standards/'+code);
  setTabUI('company');
  ensureCompany().then(renderCompanySidebar);
  $('#content').innerHTML = `
    <div class="doc-head"><h1>${esc(r.title)}</h1><span class="badge gen">${esc(r.code)}</span></div>
    <div class="doc-meta">${t('comp_std')} · ${t('tab_company')}</div>
    <div class="doc-body std-body">${r.html}</div>
    <div class="pager">
      <a class="${r.prev?'':'disabled'}" href="${r.prev?'#/standard/'+r.prev:''}">${r.prev?t('prev'):''}</a>
      <a class="${r.next?'':'disabled'}" href="${r.next?'#/standard/'+r.next:''}">${r.next?t('next'):''}</a>
    </div>`;
  wrapTables();
  $('#content').querySelectorAll('.doc-body a').forEach(a=>{
    const href = a.getAttribute('href') || '';
    if(href.startsWith('http')){ a.target='_blank'; a.rel='noopener'; }
  });
}
function wrapTables(){
  $('#content').querySelectorAll('.doc-body table').forEach(tb=>{
    const w = el('div','table-wrap'); tb.parentNode.insertBefore(w, tb); w.appendChild(tb);
  });
}
// 视频链接 -> 可嵌入播放器
function toEmbed(url){
  let m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/);
  if(m) return 'https://www.youtube.com/embed/'+m[1];
  m = url.match(/bilibili\.com\/video\/(BV[\w]+)/);
  if(m) return 'https://player.bilibili.com/player.html?bvid='+m[1]+'&autoplay=0&high_quality=1';
  return url;
}
// 去广告/噪声：丢弃手机号、报名/咨询等样板行，折叠连续重复行
function cleanBody(text){
  if(!text) return '';
  const lines = text.split('\n');
  const out=[]; let prev=''; let rep=0;
  const phoneRe = /1[3-9]\d{9}|400[-]?\d{3,4}[-]?\d{3,4}/;
  const adRe = /报名|咨询热线|免费领取|限时|招商|加微信|点击咨询|客服(电话|热线)?|微信号|立即(咨询|报名)|抢购|特价|优惠(活动|券)?|联系电话|服务热线|联系方式|手机[:：]|招商(加盟|代理)?/;
  const navRe = /^(首页|关于我们|联系我们|加入我们|资料下载|视频列表|行业资讯|技术文章|解决方案|产品中心|服务策略|维修网络|网上报修|搜索本网站内容)$/;
  for(let raw of lines){
    let line = raw.trim();
    if(phoneRe.test(line) || adRe.test(line) || navRe.test(line)) continue;
    if(line && line===prev){ rep++; if(rep>=2) continue; } else rep=0;
    prev=line;
    out.push(raw);
  }
  return out.join('\n');
}
// 资源正文：转义后把 URL 变为可点击链接
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
  html += `<div class="home-card" data-go="#/company"><div class="ic">🏢</div><h3>${t('tab_company')}</h3><p>${t('home_comp_desc')}</p></div>`;
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
    if(!r.materials.length && !r.resources.length && !(r.standards||[]).length){ box.appendChild(el('div','empty', t('search_empty'))); }
    r.materials.forEach(m=>{ const a=el('a', '', `<span class="sr-kind">教材</span>${esc(m.title)} <small>(${m.group_name}·${m.level})</small>`); a.href='#/material/'+m.slug; box.appendChild(a); });
    r.resources.forEach(res=>{ const a=el('a', '', `<span class="sr-kind res">资源</span>${esc(res.title)} <small>(${esc(res.platform)})</small>`); a.href='#/resource/'+res.id; box.appendChild(a); });
    (r.standards||[]).forEach(s=>{ const a=el('a', '', `<span class="sr-kind std">标准</span>${esc(s.code)} <small>${esc(s.title)}</small>`); a.href='#/standard/'+s.id; box.appendChild(a); });
    box.classList.remove('hidden');
  }catch(e){ box.classList.add('hidden'); }
}

/* ---------- 路由 ---------- */
async function route(){
  const h = location.hash || '#/home';
  if(h==='#/home'){ await ensureMaterials(); showHome(); return; }
  if(h==='#/resources'){ switchTab('resources'); await loadResources(); $('#content').innerHTML='<div class="placeholder">'+t('placeholder_res')+'</div>'; return; }
  if(h==='#/company'){ switchTab('company'); await showCompany(); return; }
  let m = h.match(/#\/material\/(.+)/);
  if(m){ await ensureMaterials(); if(STATE.tab!=='materials') switchTab('materials'); try{ await showMaterial(m[1]); }catch(e){ $('#content').innerHTML='<div class="placeholder">'+t('notfound')+'</div>'; } return; }
  let r = h.match(/#\/resource\/(.+)/);
  if(r){ switchTab('resources'); try{ await showResource(r[1]); }catch(e){ $('#content').innerHTML='<div class="placeholder">'+t('notfound_res')+'</div>'; } return; }
  let s = h.match(/#\/standard\/(.+)/);
  if(s){ switchTab('company'); try{ await showStandard(s[1]); }catch(e){ $('#content').innerHTML='<div class="placeholder">'+t('notfound_std')+'</div>'; } return; }
  showHome();
}
async function ensureMaterials(){ if(!STATE.materials.length) await loadMaterials(); }

function esc(s){ return (s==null?'':String(s)).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

init();
