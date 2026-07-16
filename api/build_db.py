#!/usr/bin/env python3
"""将 13 篇教材 Markdown + 下载的 resources.json 组装进 SQLite (learning.db)。"""
import os, json, sqlite3, re, glob
import markdown as md

ROOT = '/Users/weigan/WorkBuddy/2026-07-15-13-48-58'
MAT = os.path.join(ROOT, '培训教材')
# 输出到 api/data，确保 build 产物与 Vercel serverless 函数同目录
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
DB = os.path.join(DATA, 'learning.db')
RES = os.path.join(DATA, 'resources.json')
os.makedirs(DATA, exist_ok=True)

GROUPS = [
    ('presale', '售前工程师', '懂产品 · 懂工艺 · 会写方案 · 会算账', 1),
    ('sales', '销售', '懂客户 · 会讲故事 · 能成交', 2),
    ('service', '售后工程师', '懂结构 · 会装机 · 能排障 · 保稳定', 3),
]
GROUP_KEY = {n: k for k, n, _, _ in GROUPS}
LEVEL_ORDER = {'总览': 0, '初级': 1, '中级': 2, '高阶': 3}
FILE_ORDER = {'00_使用说明': 0, '初级': 1, '中级': 2, '高阶': 3, 'README': 0}


def slugify(path):
    rel = os.path.splitext(os.path.relpath(path, MAT))[0]
    return rel.replace('/', '_').replace('\\', '_')


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
    CREATE TABLE categories (id INTEGER PRIMARY KEY, key TEXT UNIQUE, name TEXT, blurb TEXT, sort INTEGER);
    CREATE TABLE materials (id INTEGER PRIMARY KEY, slug TEXT UNIQUE, group_key TEXT, group_name TEXT,
        level TEXT, title TEXT, html TEXT, text TEXT, sort INTEGER, source TEXT);
    CREATE TABLE resources (id TEXT PRIMARY KEY, url TEXT, domain TEXT, platform TEXT, category TEXT,
        categories_json TEXT, levels_json TEXT, note TEXT, title TEXT, body TEXT, word_count INTEGER,
        status TEXT, fetched_at TEXT);
    ''')
    for k, name, blurb, sort in GROUPS:
        c.execute('INSERT INTO categories (key,name,blurb,sort) VALUES (?,?,?,?)', (k, name, blurb, sort))

    # 教材（递归遍历 培训教材/ 下所有 .md）
    mats = []
    group_idx = {'通用': 0}
    for i, (_, n, _, _) in enumerate(GROUPS):
        group_idx[n] = i + 1
    for path in sorted(glob.glob(os.path.join(MAT, '**', '*.md'), recursive=True)):
        f = os.path.basename(path)
        text = open(path, encoding='utf-8').read()
        is_readme = f == 'README.md'
        grp_name = '通用'
        if not is_readme:
            for _, n, _, _ in GROUPS:
                if n in path:
                    grp_name = n
                    break
        level = '总览' if is_readme else '初级'
        for lv in LEVEL_ORDER:
            if lv != '总览' and lv in f:
                level = lv
        title = re.search(r'^#\s+(.+)$', text, re.M)
        title = title.group(1).strip() if title else f
        slug = slugify(path)
        sort = group_idx.get(grp_name, 9) * 1000 + LEVEL_ORDER.get(level, 5) * 100
        sort += (0 if f.startswith('00_') else 5) * 10
        html = md_to_html(text)
        mats.append((slug, 'general' if is_readme else GROUP_KEY.get(grp_name, 'general'),
                     grp_name, level, title, html, md_to_text(html), sort, f))
    c.executemany('INSERT INTO materials (slug,group_key,group_name,level,title,html,text,sort,source) '
                  'VALUES (?,?,?,?,?,?,?,?,?)', mats)

    # 资源
    if os.path.exists(RES):
        res = json.load(open(RES, encoding='utf-8'))
        for r in res:
            c.execute('INSERT OR REPLACE INTO resources (id,url,domain,platform,category,categories_json,'
                      'levels_json,note,title,body,word_count,status,fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                      (r['id'], r['url'], r['domain'], r['platform'], r['category'],
                       json.dumps(r.get('categories', []), ensure_ascii=False),
                       json.dumps(r.get('levels', []), ensure_ascii=False),
                       r.get('note', ''), r.get('title', ''), r.get('body', ''),
                       r.get('word_count', 0), r.get('status', ''), ''))

    conn.commit()
    n_mat = c.execute('SELECT COUNT(*) FROM materials').fetchone()[0]
    n_res = c.execute('SELECT COUNT(*) FROM resources').fetchone()[0]
    n_ok = c.execute("SELECT COUNT(*) FROM resources WHERE status='ok'").fetchone()[0]
    print(f'DB built: {DB}')
    print(f'  materials={n_mat}, resources={n_res} (downloaded ok={n_ok})')
    conn.close()


if __name__ == '__main__':
    main()
