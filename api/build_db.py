#!/usr/bin/env python3
"""将 13 篇教材 Markdown（中英双语）+ 下载的 resources.json + 培训视频合并进 SQLite (learning.db)。

双语规则：
- 每篇中文教材 `<x>.md` 可配套英文 `<x>_en.md`，二者共享同一 slug，以 lang 区分。
- materials 表以 (slug, lang) 为唯一键；categories 表增加 name_en / blurb_en。
"""
import os, json, sqlite3, re, glob, hashlib
import markdown as md

ROOT = '/Users/weigan/WorkBuddy/2026-07-15-13-48-58'
MAT = os.path.join(ROOT, '培训教材')
# 输出到 api/data，确保 build 产物与 Vercel serverless 函数同目录
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


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript('''
    DROP TABLE IF EXISTS categories;
    DROP TABLE IF EXISTS materials;
    DROP TABLE IF EXISTS resources;
    CREATE TABLE categories (id INTEGER PRIMARY KEY, key TEXT UNIQUE, name TEXT, name_en TEXT,
        blurb TEXT, blurb_en TEXT, sort INTEGER);
    CREATE TABLE materials (id INTEGER PRIMARY KEY, slug TEXT, lang TEXT, group_key TEXT, group_name TEXT,
        level TEXT, title TEXT, html TEXT, text TEXT, sort INTEGER, source TEXT,
        UNIQUE(slug, lang));
    CREATE TABLE resources (id TEXT PRIMARY KEY, url TEXT, domain TEXT, platform TEXT, category TEXT,
        categories_json TEXT, levels_json TEXT, note TEXT, title TEXT, body TEXT, word_count INTEGER,
        status TEXT, fetched_at TEXT, video_url TEXT);
    ''')
    for k, name, en, bz, be, sort in GROUPS:
        c.execute('INSERT INTO categories (key,name,name_en,blurb,blurb_en,sort) VALUES (?,?,?,?,?,?)',
                  (k, name, en, bz, be, sort))

    # 教材（递归遍历 培训教材/ 下所有 .md；英文版仅作为中文版 companion 处理）
    mats = []
    group_idx = {'通用': 0}
    for i, (_, n, _, _, _, _) in enumerate(GROUPS):
        group_idx[n] = i + 1
    for path in sorted(glob.glob(os.path.join(MAT, '**', '*.md'), recursive=True)):
        f = os.path.basename(path)
        if f.endswith('_en.md'):
            continue  # 英文版在下方作为 companion 处理
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
        mats.append((slug, 'zh', GROUP_KEY.get(grp_name, 'general'), grp_name, level,
                     title, html, md_to_text(html), sort, f))

        # 英文 companion
        en_path = os.path.splitext(path)[0] + '_en.md'
        if os.path.exists(en_path):
            et = open(en_path, encoding='utf-8').read()
            en_title = first_h1(et) or f
            ehtml = md_to_html(et)
            gk = GROUP_KEY.get(grp_name, 'general')
            mats.append((slug, 'en', gk, GROUP_EN.get(gk, 'General'), level,
                         en_title, ehtml, md_to_text(ehtml), sort, os.path.basename(en_path)))

    c.executemany(
        'INSERT INTO materials (slug,lang,group_key,group_name,level,title,html,text,sort,source) '
        'VALUES (?,?,?,?,?,?,?,?,?,?)', mats)

    # 资源
    res = []
    if os.path.exists(RES):
        res = json.load(open(RES, encoding='utf-8'))
    # 培训视频（合并进资源库，platform='培训视频'，video_url 用于前端嵌入播放器）
    if os.path.exists(VID):
        for v in json.load(open(VID, encoding='utf-8')):
            cat = v.get('category', '通用')
            res.append({
                'id': 'vid_' + hashlib.md5(v['url'].encode('utf-8')).hexdigest()[:10],
                'url': v['url'],
                'domain': 'youtube.com' if 'youtube' in v['url'] else ('bilibili.com' if 'bilibili' in v['url'] else ''),
                'platform': '培训视频',
                'category': cat,
                'categories': [cat],
                'levels': v.get('levels', []),
                'note': v.get('note', ''),
                'title': v.get('title', v['url']),
                'body': '',
                'word_count': 0,
                'status': 'video',
                'video_url': v['url'],
            })
    for r in res:
        c.execute('INSERT OR REPLACE INTO resources (id,url,domain,platform,category,categories_json,'
                  'levels_json,note,title,body,word_count,status,fetched_at,video_url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (r['id'], r['url'], r['domain'], r['platform'], r['category'],
                   json.dumps(r.get('categories', []), ensure_ascii=False),
                   json.dumps(r.get('levels', []), ensure_ascii=False),
                   r.get('note', ''), r.get('title', ''), r.get('body', ''),
                   r.get('word_count', 0), r.get('status', ''), '', r.get('video_url', '')))

    conn.commit()
    n_mat = c.execute('SELECT COUNT(*) FROM materials').fetchone()[0]
    n_zh = c.execute("SELECT COUNT(*) FROM materials WHERE lang='zh'").fetchone()[0]
    n_en = c.execute("SELECT COUNT(*) FROM materials WHERE lang='en'").fetchone()[0]
    n_res = c.execute('SELECT COUNT(*) FROM resources').fetchone()[0]
    n_ok = c.execute("SELECT COUNT(*) FROM resources WHERE status='ok'").fetchone()[0]
    n_vid = c.execute("SELECT COUNT(*) FROM resources WHERE status='video'").fetchone()[0]
    print(f'DB built: {DB}')
    print(f'  materials={n_mat} (zh={n_zh}, en={n_en}), resources={n_res} (text ok={n_ok}, videos={n_vid})')
    conn.close()


if __name__ == '__main__':
    main()
