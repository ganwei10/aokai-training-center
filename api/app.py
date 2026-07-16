#!/usr/bin/env python3
"""奥楷培训学习中心 —— 后端 API（FastAPI + SQLite）。"""
import os, json, sqlite3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'data', 'learning.db')
FRONTEND = os.path.join(os.path.dirname(BASE), 'frontend')

app = FastAPI(title='奥楷培训学习中心 API')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(r):
    return {k: r[k] for k in r.keys()}


@app.get('/api/health')
def health():
    return {'ok': True}


@app.get('/api/categories')
def categories(lang: str = 'zh'):
    conn = db()
    cats = [row_to_dict(x) for x in conn.execute('SELECT * FROM categories ORDER BY sort').fetchall()]
    for c in cats:
        c['material_count'] = conn.execute(
            'SELECT COUNT(*) FROM materials WHERE group_key=? AND lang=?', (c['key'], lang)).fetchone()[0]
        if lang == 'en':
            c['name'] = c.pop('name_en', c['name'])
            c['blurb'] = c.pop('blurb_en', c['blurb'])
        else:
            c.pop('name_en', None)
            c.pop('blurb_en', None)
    conn.close()
    return cats


@app.get('/api/materials')
def materials(group: str = None, level: str = None, q: str = None, lang: str = 'zh'):
    conn = db()
    sql = 'SELECT slug,group_key,group_name,level,title,sort FROM materials WHERE lang=?'
    args = [lang]
    if group:
        sql += ' AND group_key=?'; args.append(group)
    if level:
        sql += ' AND level=?'; args.append(level)
    if q:
        sql += ' AND (title LIKE ? OR text LIKE ?)'; args += [f'%{q}%', f'%{q}%']
    sql += ' ORDER BY sort'
    rows = [row_to_dict(x) for x in conn.execute(sql, args).fetchall()]
    conn.close()
    return rows


@app.get('/api/materials/{slug}')
def material(slug: str, lang: str = 'zh'):
    conn = db()
    r = conn.execute('SELECT * FROM materials WHERE slug=? AND lang=?', (slug, lang)).fetchone()
    if not r:
        raise HTTPException(404, 'not found')
    d = row_to_dict(r)
    # 上一篇/下一篇（同语言、同排序序列）
    all_slugs = [x['slug'] for x in conn.execute(
        'SELECT slug FROM materials WHERE lang=? ORDER BY sort', (lang,)).fetchall()]
    if slug in all_slugs:
        i = all_slugs.index(slug)
        d['prev'] = all_slugs[i - 1] if i > 0 else None
        d['next'] = all_slugs[i + 1] if i < len(all_slugs) - 1 else None
    conn.close()
    return d


@app.get('/api/resources')
def resources(category: str = None, platform: str = None, type: str = None, status: str = None, level: str = None, q: str = None):
    conn = db()
    sql = ('SELECT id,url,domain,platform,type,category,categories_json,levels_json,note,title,'
           'word_count,status,video_url FROM resources WHERE 1=1')
    args = []
    if category:
        sql += ' AND category=?'; args.append(category)
    if platform:
        sql += ' AND platform=?'; args.append(platform)
    if type:
        sql += ' AND type=?'; args.append(type)
    if status:
        sql += ' AND status=?'; args.append(status)
    if level:
        sql += ' AND levels_json LIKE ?'; args.append(f'%{level}%')
    if q:
        sql += ' AND (title LIKE ? OR body LIKE ? OR note LIKE ?)'
        args += [f'%{q}%', f'%{q}%', f'%{q}%']
    sql += ' ORDER BY category, word_count DESC'
    rows = [row_to_dict(x) for x in conn.execute(sql, args).fetchall()]
    for r in rows:
        r['categories'] = json.loads(r.pop('categories_json') or '[]')
        r['levels'] = json.loads(r.pop('levels_json') or '[]')
    conn.close()
    return rows


@app.get('/api/resources/{rid}')
def resource(rid: str):
    conn = db()
    r = conn.execute('SELECT * FROM resources WHERE id=?', (rid,)).fetchone()
    if not r:
        raise HTTPException(404, 'not found')
    d = row_to_dict(r)
    d['categories'] = json.loads(d.pop('categories_json') or '[]')
    d['levels'] = json.loads(d.pop('levels_json') or '[]')
    conn.close()
    return d


@app.get('/api/standards')
def standards():
    conn = db()
    rows = [row_to_dict(x) for x in conn.execute(
        'SELECT id,code,title FROM standards ORDER BY sort').fetchall()]
    conn.close()
    return rows


@app.get('/api/standards/{code}')
def standard(code: str):
    conn = db()
    r = conn.execute('SELECT * FROM standards WHERE id=?', (code,)).fetchone()
    if not r:
        raise HTTPException(404, 'not found')
    d = row_to_dict(r)
    all_ids = [x['id'] for x in conn.execute('SELECT id FROM standards ORDER BY sort').fetchall()]
    if code in all_ids:
        i = all_ids.index(code)
        d['prev'] = all_ids[i - 1] if i > 0 else None
        d['next'] = all_ids[i + 1] if i < len(all_ids) - 1 else None
    conn.close()
    return d


@app.get('/api/company')
def company():
    conn = db()
    docs = [row_to_dict(x) for x in conn.execute(
        'SELECT kind,slug,title,asset,desc FROM company ORDER BY sort').fetchall()]
    intro = conn.execute("SELECT html FROM company WHERE kind='intro'").fetchone()
    stds = [row_to_dict(x) for x in conn.execute(
        'SELECT id,code,title FROM standards ORDER BY sort').fetchall()]
    conn.close()
    return {'intro_html': intro['html'] if intro else '', 'docs': docs, 'standards': stds}


@app.get('/api/search')
def search(q: str = Query(..., min_length=1), lang: str = 'zh'):
    conn = db()
    mats = [row_to_dict(x) for x in conn.execute(
        'SELECT slug,group_name,level,title,"material" AS kind FROM materials '
        'WHERE lang=? AND (title LIKE ? OR text LIKE ?) ORDER BY sort LIMIT 30',
        (lang, f'%{q}%', f'%{q}%'))]
    res = [row_to_dict(x) for x in conn.execute(
        'SELECT id,title,category,platform,"resource" AS kind FROM resources '
        'WHERE title LIKE ? OR body LIKE ? OR note LIKE ? ORDER BY word_count DESC LIMIT 30',
        (f'%{q}%', f'%{q}%', f'%{q}%'))]
    stds = [row_to_dict(x) for x in conn.execute(
        'SELECT id,code,title,"standard" AS kind FROM standards '
        'WHERE code LIKE ? OR title LIKE ? OR text LIKE ? ORDER BY sort LIMIT 20',
        (f'%{q}%', f'%{q}%', f'%{q}%'))]
    conn.close()
    return {'materials': mats, 'resources': res, 'standards': stds}


# 前端静态资源（本地运行时由后端一并托管；在 Vercel 等平台设为 0，由平台托管静态文件）
if os.path.isdir(FRONTEND) and os.environ.get('SERVE_FRONTEND', '1') != '0':
    app.mount('/', StaticFiles(directory=FRONTEND, html=True), name='frontend')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
