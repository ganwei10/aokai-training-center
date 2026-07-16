#!/usr/bin/env python3
"""将教材 / 外部资源 / 国标 / 公司资料 合并进 SQLite (learning.db)。

四大内容源：
1. 内部教材：培训教材/ 下中英双语 Markdown（按 (slug,lang) 唯一）。
2. 外链资源库：resources.json（抓取的网页）+ videos_candidates.json（培训视频）。
                每条资源新增 `type` 字段，类型细分为：培训视频 / 文章 / 标准 / 文档。
3. 相关国家标准：公司资料/国标/*.md（GB 16798-2023 等 4 个），阅读友好全文。
4. 公司资料：公司简介.md（简介阅读页）+ frontend/assets/*.pdf（可下载原始文档）。

链接处理：
- 教材/国标正文里的裸 URL -> 可点击（已下载则指向 #/resource/{id}，否则指向原站）。
- 教材/国标正文里的「GB xxxx」标准号 -> 指向站内 #/standard/{slug}（离线可读）。
"""
import os, json, sqlite3, re, glob, hashlib
from urllib.parse import urlparse
import markdown as md

ROOT = '/Users/weigan/WorkBuddy/2026-07-15-13-48-58'
MAT = os.path.join(ROOT, '培训教材')
COMPANY = os.path.join(ROOT, '公司资料')
STDDIR = os.path.join(COMPANY, '国标')
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'assets')

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
DB = os.path.join(DATA, 'learning.db')
RES = os.path.join(DATA, 'resources.json')
VID = os.path.join(DATA, 'videos_candidates.json')
os.makedirs(DATA, exist_ok=True)

# (key, 中文名, 英文名, 中文简介, 英文简介, 排序)
GROUPS = [
    ('presale', '售前工程师', 'Pre-sales Engineer', '懂产品 · 懂工艺 · 会写方案 · 会算账',
     'Knows the product, knows the process, writes proposals, does the math', 1),
    ('sales', '销售', 'Sales', '懂客户 · 会讲故事 · 能成交',
     'Knows the customer, tells the story, closes the deal', 2),
    ('service', '售后工程师', 'After-sales Engineer', '懂结构 · 会装机 · 能排障 · 保稳定',
     'Knows the structure, installs, troubleshoots, keeps it stable', 3),
]
GROUP_KEY = {n: k for k, n, en, bz, be, s in GROUPS}
GROUP_EN = {k: en for k, n, en, bz, be, s in GROUPS}
LEVEL_ORDER = {'总览': 0, '初级': 1, '中级': 2, '高阶': 3}
FILE_ORDER = {'00_使用说明': 0, '初级': 1, '中级': 2, '高阶': 3, 'README': 0}

# 资源 platform -> 资源类型
TYPE_MAP = {'培训视频': '培训视频', '标准查询': '标准', '文档资料': '文档'}


def slugify(path):
    rel = os.path.splitext(os.path.relpath(path, MAT))[0]
    return rel.replace('/', '_').replace('\\', '_')


def first_h1(text):
    m = re.search(r'^#\s+(.+)$', text, re.M)
    return m.group(1).strip() if m else None


def md_to_html(text):
    m = md.Markdown(extensions=['tables', 'fenced_code', 'toc', 'nl2br'])
    return m.convert(text)


def md_to_text(text):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text)).strip()


def esc_attr(s):
    return (s.replace('&', '&amp;').replace('"', '&quot;')
             .replace('<', '&lt;').replace('>', '&gt;'))


# ---------- 国标：文件名 -> 标准号 -> 链接 slug ----------
STD_CODE_RE = re.compile(r'^(GB|T)\s*[/]?\s*(\d{4,5})\s*[-.]?\s*(\d{2,4})?', re.I)
STD_PREFIX = {}   # 数字前缀 -> slug


def load_standards():
    """读取 公司资料/国标/*.md（排除 README），返回标准列表。"""
    out = []
    STD_PREFIX.clear()
    for path in sorted(glob.glob(os.path.join(STDDIR, '*.md'))):
        f = os.path.basename(path)
        if f.upper().startswith('README'):
            continue
        slug = os.path.splitext(f)[0]                       # GB16798-2023
        text = open(path, encoding='utf-8').read()
        title = first_h1(text) or slug
        m = STD_CODE_RE.search(title)
        code = title[:0]
        if m:
            code = ('GB/T ' if m.group(1).upper() == 'T' else 'GB ') + m.group(2) + \
                   (('-' + m.group(3)) if m.group(3) else '')
        # 标准号数字前缀用于教材内 GB 编号匹配
        dm = re.search(r'(\d{4,5})', slug)
        if dm:
            STD_PREFIX[dm.group(1)] = slug
        out.append({'slug': slug, 'code': code or slug, 'title': title,
                    'html': md_to_html(text), 'text': md_to_text(text)})
    return out


def load_resources():
    """读取 resources.json（下载的网页）+ 培训视频，合并成统一的资源列表，并打 type 标签。"""
    res = []
    if os.path.exists(RES):
        res = json.load(open(RES, encoding='utf-8'))
    if os.path.exists(VID):
        for v in json.load(open(VID, encoding='utf-8')):
            res.append({
                'id': 'vid_' + hashlib.md5(v['url'].encode('utf-8')).hexdigest()[:10],
                'url': v['url'],
                'domain': 'youtube.com' if 'youtube' in v['url'] else ('bilibili.com' if 'bilibili' in v['url'] else ('v.qq.com' if 'v.qq.com' in v['url'] else '')),
                'platform': '培训视频',
                'category': v.get('category', '通用'),
                'categories': [v.get('category', '通用')],
                'levels': v.get('levels', []),
                'note': v.get('note', ''),
                'title': v.get('title', v['url']),
                'body': '',
                'word_count': 0,
                'status': 'video',
                'video_url': v['url'],
            })
    for r in res:
        if r.get('video_url') or r.get('status') == 'video':
            r['type'] = '培训视频'
        else:
            r['type'] = TYPE_MAP.get(r.get('platform', ''), '文章')
    return res


def build_urlmap(res):
    """url -> (resource_id, is_downloaded_ok)"""
    m = {}
    for r in res:
        m[r['url']] = (r['id'], r.get('status') == 'ok')
    return m


def linkify_and_map(html, urlmap, std_prefix):
    """把正文里的裸 URL 包成可点击链接，并把 GB 标准号指向站内国标页。"""
    def repl_url(match):
        raw = match.group(0)
        url = raw.replace('&amp;', '&')
        if url in urlmap:
            rid, ok = urlmap[url]
            if ok:
                return '<a href="#/resource/%s" class="ext-local">📄 本地缓存</a>' % rid
        domain = urlparse(url).netloc or url
        return '<a href="%s" target="_blank" rel="noopener" class="ext">↗ %s</a>' % (esc_attr(url), esc_attr(domain))

    html = re.sub(r'https?://[^\s<>"\'），。、；：）]+', repl_url, html)

    # GB 标准号 -> 站内国标页
    def repl_gb(match):
        prefix = match.group(1)
        slug = std_prefix.get(prefix)
        if not slug:
            return match.group(0)
        return '<a href="#/standard/%s" class="ext-local">%s</a>' % (slug, esc_attr(match.group(0)))
    html = re.sub(r'GB\s*/?T?\s*(\d{4,5})(?:[-\.]\d{2,4})?', repl_gb, html)
    return html


def load_company():
    """公司简介（阅读页）+ frontend/assets 下的原始 PDF（可下载）。"""
    docs = []
    intro_path = os.path.join(COMPANY, '公司简介.md')
    if os.path.exists(intro_path):
        t = open(intro_path, encoding='utf-8').read()
        docs.append({'kind': 'intro', 'slug': 'intro', 'title': first_h1(t) or '公司简介',
                     'html': md_to_html(t), 'asset': '', 'desc': '奥楷公司定位、产品方案与资料清单'})
    # 扫描静态资源里的 PDF
    if os.path.isdir(ASSETS):
        for p in sorted(glob.glob(os.path.join(ASSETS, '*.pdf'))):
            name = os.path.splitext(os.path.basename(p))[0]
            title = re.sub(r'^\d+_', '', name).replace('_', ' ')
            docs.append({'kind': 'file', 'slug': name, 'title': title,
                         'html': '', 'asset': '/assets/' + os.path.basename(p),
                         'desc': '奥楷官方原始文档（PDF）'})
    return docs


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript('''
    DROP TABLE IF EXISTS categories;
    DROP TABLE IF EXISTS materials;
    DROP TABLE IF EXISTS resources;
    DROP TABLE IF EXISTS standards;
    DROP TABLE IF EXISTS company;
    CREATE TABLE categories (id INTEGER PRIMARY KEY, key TEXT UNIQUE, name TEXT, name_en TEXT,
        blurb TEXT, blurb_en TEXT, sort INTEGER);
    CREATE TABLE materials (id INTEGER PRIMARY KEY, slug TEXT, lang TEXT, group_key TEXT, group_name TEXT,
        level TEXT, title TEXT, html TEXT, text TEXT, sort INTEGER, source TEXT,
        UNIQUE(slug, lang));
    CREATE TABLE resources (id TEXT PRIMARY KEY, url TEXT, domain TEXT, platform TEXT, type TEXT,
        category TEXT, categories_json TEXT, levels_json TEXT, note TEXT, title TEXT, body TEXT,
        word_count INTEGER, status TEXT, fetched_at TEXT, video_url TEXT);
    CREATE TABLE standards (id TEXT PRIMARY KEY, code TEXT, title TEXT, html TEXT, text TEXT,
        sort INTEGER);
    CREATE TABLE company (id INTEGER PRIMARY KEY, kind TEXT, slug TEXT UNIQUE, title TEXT,
        html TEXT, asset TEXT, desc TEXT, sort INTEGER);
    ''')
    for k, name, en, bz, be, sort in GROUPS:
        c.execute('INSERT INTO categories (key,name,name_en,blurb,blurb_en,sort) VALUES (?,?,?,?,?,?)',
                  (k, name, en, bz, be, sort))

    # 1) 资源 + URL 索引
    res = load_resources()
    urlmap = build_urlmap(res)

    # 2) 国标索引（供教材 GB 编号链接）
    stds = load_standards()

    # 3) 教材（递归遍历 培训教材/ 下所有 .md）
    mats = []
    group_idx = {'通用': 0}
    for i, (_, n, _, _, _, _) in enumerate(GROUPS):
        group_idx[n] = i + 1
    for path in sorted(glob.glob(os.path.join(MAT, '**', '*.md'), recursive=True)):
        f = os.path.basename(path)
        if f.endswith('_en.md'):
            continue
        text = open(path, encoding='utf-8').read()
        is_readme = f == 'README.md'
        grp_name = '通用'
        if not is_readme:
            for _, n, _, _, _, _ in GROUPS:
                if n in path:
                    grp_name = n
                    break
        level = '总览' if is_readme else '初级'
        for lv in LEVEL_ORDER:
            if lv != '总览' and lv in f:
                level = lv
        slug = slugify(path)
        title = first_h1(text) or f
        sort = group_idx.get(grp_name, 9) * 1000 + LEVEL_ORDER.get(level, 5) * 100
        sort += (0 if f.startswith('00_') else 5) * 10
        html = md_to_html(text)
        html = linkify_and_map(html, urlmap, STD_PREFIX)
        mats.append((slug, 'zh', GROUP_KEY.get(grp_name, 'general'), grp_name, level,
                     title, html, md_to_text(html), sort, f))

        en_path = os.path.splitext(path)[0] + '_en.md'
        if os.path.exists(en_path):
            et = open(en_path, encoding='utf-8').read()
            en_title = first_h1(et) or f
            ehtml = md_to_html(et)
            ehtml = linkify_and_map(ehtml, urlmap, STD_PREFIX)
            gk = GROUP_KEY.get(grp_name, 'general')
            mats.append((slug, 'en', gk, GROUP_EN.get(gk, 'General'), level,
                         en_title, ehtml, md_to_text(ehtml), sort, os.path.basename(en_path)))

    c.executemany(
        'INSERT INTO materials (slug,lang,group_key,group_name,level,title,html,text,sort,source) '
        'VALUES (?,?,?,?,?,?,?,?,?,?)', mats)

    # 4) 资源（含视频 + type）
    for r in res:
        c.execute('INSERT OR REPLACE INTO resources (id,url,domain,platform,type,category,categories_json,'
                  'levels_json,note,title,body,word_count,status,fetched_at,video_url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (r['id'], r['url'], r['domain'], r['platform'], r.get('type', '文章'), r['category'],
                   json.dumps(r.get('categories', []), ensure_ascii=False),
                   json.dumps(r.get('levels', []), ensure_ascii=False),
                   r.get('note', ''), r.get('title', ''), r.get('body', ''),
                   r.get('word_count', 0), r.get('status', ''), '', r.get('video_url', '')))

    # 5) 国标
    for i, s in enumerate(stds):
        c.execute('INSERT OR REPLACE INTO standards (id,code,title,html,text,sort) VALUES (?,?,?,?,?,?)',
                  (s['slug'], s['code'], s['title'], s['html'], s['text'], i))

    # 6) 公司资料
    comp = load_company()
    for i, d in enumerate(comp):
        c.execute('INSERT OR REPLACE INTO company (kind,slug,title,html,asset,desc,sort) VALUES (?,?,?,?,?,?,?)',
                  (d['kind'], d['slug'], d['title'], d['html'], d['asset'], d['desc'], i))

    conn.commit()
    n_mat = c.execute('SELECT COUNT(*) FROM materials').fetchone()[0]
    n_zh = c.execute("SELECT COUNT(*) FROM materials WHERE lang='zh'").fetchone()[0]
    n_en = c.execute("SELECT COUNT(*) FROM materials WHERE lang='en'").fetchone()[0]
    n_res = c.execute('SELECT COUNT(*) FROM resources').fetchone()[0]
    n_ok = c.execute("SELECT COUNT(*) FROM resources WHERE status='ok'").fetchone()[0]
    n_vid = c.execute("SELECT COUNT(*) FROM resources WHERE status='video'").fetchone()[0]
    from collections import Counter
    types = Counter(c.execute('SELECT type, COUNT(*) FROM resources GROUP BY type').fetchall())
    n_std = c.execute('SELECT COUNT(*) FROM standards').fetchone()[0]
    n_comp = c.execute('SELECT COUNT(*) FROM company').fetchone()[0]
    n_local = c.execute("SELECT COUNT(*) FROM materials WHERE html LIKE '%ext-local%'").fetchone()[0]
    print(f'DB built: {DB}')
    print(f'  materials={n_mat} (zh={n_zh}, en={n_en})')
    print(f'  resources={n_res} (text ok={n_ok}, videos={n_vid})  types={dict(types)}')
    print(f'  standards={n_std}  company_docs={n_comp}')
    print(f'  material links: local-cache={n_local} rows')
    conn.close()


if __name__ == '__main__':
    main()
