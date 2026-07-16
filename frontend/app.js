const API = window.API_BASE || '/api';
const LV = { '初级': {c:'lv1',t:'初级'}, '中级': {c:'lv2',t:'中级'}, '高阶': {c:'lv3',t:'高阶'}, '总览': {c:'gen',t:'总览'} };

let STATE = { tab:'materials', level:'', cat:'', plat:'', materials:[], cats:[] };

const $ = s => document.querySelector(s);
const el = (tag, cls, html) => { const e=document.createElement(tag); if(cls)e.className=cls; if(html!=null)e.innerHTML=html; return e; };

async function get(path){ const r = await fetch(API+path); if(!r.ok) throw new Error(path+' '+r.status); return r.json(); }

/* ---------- 初始化 ---------- */
async function init(){
  try { STATE.cats = await get('/categories'); } catch(e){ STATE.cats=[]; }
  bindEvents();
  await route();
  window.addEventListener('hashchange', route);
}

function bindEvents(){
  $('#tabMaterials').onclick = () => switchTab('materials');
  $('#tabResources').onclick = () => switchTab('resources');
  $('#menuBtn').onclick = () => { $('#sidebar').classList.toggle('open'); $('#overlay').classList.toggle('hidden'); };
  $('#overlay').onclick = () => { $('#sidebar').classList.remove('open'); $('#overlay').classList.add('hidden'); };

  // 级别筛选
  $('#levelFilter').querySelectorAll('.chip').forEach(c=>{
    c.onclick = () => { STATE.level=c.dataset.level;
      $('#levelFilter').querySelectorAll('.chip').forEach(x=>x.classList.remove('active'));
      c.classList.add('active'); renderCatList(); };
  });
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
  $('#sideMaterials').classList.toggle('hidden', tab!=='materials');
  $('#sideResources').classList.toggle('hidden', tab!=='resources');
  if(tab==='materials'){ renderCatList(); }
  else { loadResources(); }
  if(location.hash==='#/home' || !location.hash) location.hash = tab==='materials' ? '#/home' : '#/resources';
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
      const a = el('a', '', `${m.title}<span class="badge ${lv.c}">${lv.t}</span>`);
      a.href = '#/material/'+m.slug;
      a.dataset.slug = m.slug;
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
    const fail = r.status && r.status!=='ok';
    item.innerHTML = `<div class="rt">${esc(r.title||r.domain)}</div>
      <div class="rmeta">
        <span class="pf">${esc(r.platform)}</span>
        <span>${esc(r.category)}</span>
        ${(r.levels||[]).map(l=>`<span class="badge ${LV[l]?LV[l].c:'gen'}">${l}</span>`).join('')}
        ${r.word_count?`<span>${r.word_count} 字</span>`:''}
        ${fail?`<span class="st-fail">仅链接</span>`:''}
      </div>`;
    item.onclick = ()=> location.hash = '#/resource/'+r.id;
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
    <div class="doc-head"><h1>${esc(m.title)}</h1><span class="badge ${lv.c}">${lv.t}</span></div>
    <div class="doc-meta">${esc(m.group_name)} · 内部教材</div>
    <div class="doc-body">${m.html}</div>
    <div class="pager">
      <a class="${m.prev?'':'disabled'}" href="${m.prev?'#/material/'+m.prev:''}">← 上一篇</a>
      <a class="${m.next?'':'disabled'}" href="${m.next?'#/material/'+m.next:''}">下一篇 →</a>
    </div>`;
  renderCatList();
}
async function showResource(id){
  const r = await get('/resources/'+id);
  const fail = r.status && r.status!=='ok';
  const bodyHtml = fail
    ? `<div class="body">该外部资源暂未成功抓取正文，请通过下方按钮访问原页面查看完整内容。\n\n备注：${esc(r.note||'')}</div>`
    : `<div class="body">${esc(r.body||'（无正文）')}</div>`;
  $('#content').innerHTML = `
    <div class="res-detail">
      <h1>${esc(r.title||r.domain)}</h1>
      <div class="meta">来源：${esc(r.domain)} · 类型：${esc(r.platform)} · 适用：${esc(r.category)}
        ${(r.levels||[]).map(l=>'· '+l).join('')} · 字数：${r.word_count||0}</div>
      ${r.note?`<div class="note"><strong>教材备注：</strong>${esc(r.note)}</div>`:''}
      ${bodyHtml}
      <a class="ext-link" href="${esc(r.url)}" target="_blank" rel="noopener">访问原页面 ↗</a>
    </div>`;
  // 高亮资源列表
  $('#resList').querySelectorAll('.res-item').forEach((it,i)=>{});
}
function showHome(){
  const cards = [
    {ic:'📘', t:'内部教材', d:'售前 / 销售 / 售后三类人群，初级到高阶系统化讲义', go:'#/material/README'},
    {ic:'🔗', t:'外链资源库', d:'从全网收集的 33 篇产品与技术培训资料，已下载正文', go:'#/resources'},
  ];
  // 加上三类人群入口
  const groups = STATE.cats;
  let html = `<h1 style="color:var(--blue);margin-top:0">欢迎来到奥楷培训学习中心</h1>
    <p style="color:var(--muted)">肉类食品加工数字化设备（灌装/扎线/扭结、包装、码垛）产品与技术培训平台。所有外部链接内容已下载归档，可离线学习。</p>
    <div class="home-cards">`;
  groups.forEach(c=>{ html += `<div class="home-card" data-go="#/material/${c.key==='general'?'README':firstSlugOf(c.key)}">
      <div class="ic">🎯</div><h3>${esc(c.name)}</h3><p>${esc(c.blurb)} · ${c.material_count} 篇</p></div>`; });
  html += `<div class="home-card" data-go="#/resources"><div class="ic">🔗</div><h3>外链资源库</h3><p>33 条全网培训资源（含已下载正文）</p></div>`;
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
    if(!r.materials.length && !r.resources.length){ box.appendChild(el('div','empty','无匹配结果')); }
    r.materials.forEach(m=>{ const a=el('a', '', `<span class="sr-kind">教材</span>${esc(m.title)} <small>(${m.group_name}·${m.level})</small>`); a.href='#/material/'+m.slug; box.appendChild(a); });
    r.resources.forEach(res=>{ const a=el('a', '', `<span class="sr-kind res">资源</span>${esc(res.title)} <small>(${esc(res.platform)})</small>`); a.href='#/resource/'+res.id; box.appendChild(a); });
    box.classList.remove('hidden');
  }catch(e){ box.classList.add('hidden'); }
}

/* ---------- 路由 ---------- */
async function route(){
  const h = location.hash || '#/home';
  if(h==='#/home'){ await ensureMaterials(); showHome(); return; }
  if(h==='#/resources'){ switchTab('resources'); await loadResources(); $('#content').innerHTML='<div class="placeholder">从左侧选择资源查看详情</div>'; return; }
  let m = h.match(/#\/material\/(.+)/);
  if(m){ await ensureMaterials(); if(STATE.tab!=='materials') switchTab('materials'); try{ await showMaterial(m[1]); }catch(e){ $('#content').innerHTML='<div class="placeholder">未找到该教材</div>'; } return; }
  let r = h.match(/#\/resource\/(.+)/);
  if(r){ switchTab('resources'); try{ await showResource(r[1]); }catch(e){ $('#content').innerHTML='<div class="placeholder">未找到该资源</div>'; } return; }
  showHome();
}
async function ensureMaterials(){ if(!STATE.materials.length) await loadMaterials(); }

function esc(s){ return (s==null?'':String(s)).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

init();
