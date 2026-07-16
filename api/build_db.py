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


# ---------- 外链文章正文去噪：只保留有意义的文字 ----------
_NAV_WORDS = {
    '首页','资讯','产品','求购','品牌','技术','标准','展会','联盟','关于我们','联系我们',
    '加入我们','资料下载','视频列表','行业资讯','技术文章','解决方案','产品中心','服务策略',
    '维修网络','网上报修','企业风采','市场分析','产业播报','管理市场','产业建设','信息快车',
    '行业访谈','专家专栏','业界动态','技术应用','标准动态','人才招聘','招商加盟','联系厂商',
    '新闻中心','帮助中心','服务中心','下载中心','会员中心','个人中心','登录','注册','搜索',
    '设备天地','电子期刊','正文','招聘',
}
_MENU_RE = re.compile(r'( - ){2,}|( \| ){2,}|(»){2,}')
_SEP_RE = re.compile(r'^[\s»>\-—|·／/．。、，,]*$')          # 仅含分隔符的空行
_CRUMB_FRAG_RE = re.compile(r'^»\s*.{1,6}$')                # 面包屑残片：» 电子期刊
_PHONE_RE = re.compile(r'1[3-9]\d{9}|400[-]?\d{3,4}[-]?\d{3,4}|\d{3,4}-\d{7,8}')
_EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
_AD_RE = re.compile(
    r'报名|咨询热线|免费领取|限时|招商|加微信|点击咨询|客服(电话|热线)?|微信号|立即(咨询|报名)|'
    r'抢购|特价|优惠(活动|券)?|联系电话|服务热线|联系方式|手机[:：]|招商(加盟|代理)?|'
    r'扫码|二维码|关注(我们|公众号)|长按识别|领取(资料|红包|优惠券)?|免费(咨询|获取|下载|试看|试听|教程|观看|体验)|'
    r'在线(客服|咨询)|广告|推广')
_BREADCRUMB_RE = re.compile(r'(当前位置|您(当前)?的?位置|所在位置|您现在的位置|位置[:：])')
_CONTROL_RE = re.compile(r'\[\s*(打印|投稿|关闭|评论|返回顶部|回到顶部|顶部)\s*\]')
_FEED_RE = re.compile(r'(中标|招聘启事|招贤纳士|项目签约|战略合作|喜报|喜讯|导读|快讯|速递|今日要闻)')
# 高置信样板（子串即可判定，直接整行丢弃）
_HARD_BOILER_RE = re.compile(
    r'当前位置|免责声明|版权声明|下一篇|上一篇|返回顶部|相关推荐|热点推荐|排行榜|备案号|'
    r'ICP备|公安网备|Copyright|All Rights Reserved|Powered by|扫码关注|长按识别')
_TAIL_RE = re.compile(
    r'^(下一篇|上一篇|上篇|下篇|版权声明|免责声明|责任编辑|声明[:：]|'
    r'相关(文章|推荐|阅读|电子期刊|专题|新闻|报道|资料)|热点推荐|热门推荐|推荐阅读|猜你喜欢|'
    r'相关新闻|延伸阅读|大家都在看|本周?排行|上周?排行|本月?排行|今日排行|热门排行|新闻排行|'
    r'点击排行|阅读排行|友情提醒|温馨提示|郑重提示|本文来源|稿件来源|原文链接|更多精彩|'
    r'扫描(二维码|关注)|关注我们|分享到|点赞|收藏|关键词[:：]|备案号?|ICP|公安网备|'
    r'Copyright|©\s*\d|All Rights Reserved|技术支持[:：]|Powered by)', re.I)
_ICON_RE = re.compile(r'[\ue000-\uf8ff\uf000-\uf0ff\x00-\x08\x0b\x0c\x0e-\x1f\ufffd]')
_PREF_RE = re.compile(r'^[\s\*·•▪▸◆›»→\-–—]+')             # 行首项目符号/箭头
_PREF2_RE = re.compile(r'^[①-⑳A-Za-z0-9]{1,3}[.、)）]')    # 1. / 2) 等编号
_CJK_SHORT = re.compile(r'^[一-鿿]{1,6}$')


def _strip_prefix(line):
    s = _PREF_RE.sub('', line)
    s = _PREF2_RE.sub('', s)
    return s.strip()


def clean_body(text):
    """去除导航/广告/版权/排行等样板，仅保留正文；并对重复长块做兜底截断。"""
    if not text:
        return ''
    lines = text.split('\n')
    out = []
    prev = ''
    rep = 0
    for raw in lines:
        line = raw.strip()
        if line == '':
            if out and out[-1] == '':
                continue
            out.append('')
            continue
        line = _ICON_RE.sub('', line).strip()
        if line == '':
            if out and out[-1] == '':
                continue
            out.append('')
            continue
        # 高置信样板（子串）
        if _HARD_BOILER_RE.search(line):
            continue
        # 面包屑 / 纯分隔符 / 面包屑残片
        if _BREADCRUMB_RE.search(line) or _SEP_RE.match(line) or _CRUMB_FRAG_RE.match(line):
            continue
        pl = _strip_prefix(line)
        if pl in _NAV_WORDS:
            continue
        if _MENU_RE.search(line):
            continue
        if _PHONE_RE.search(line) or _EMAIL_RE.search(line):
            continue
        if _AD_RE.search(line):
            continue
        if _CONTROL_RE.search(line):
            continue
        if _FEED_RE.search(line):
            continue
        # 登录/注册类工具条：拆开后全部为导航词
        toks = [t for t in re.split(r'[\s|/·•]+', pl) if t]
        if len(toks) >= 2 and all(t in _NAV_WORDS for t in toks):
            continue
        # 频道/栏目列表：>=3 个纯中文短词（1-6 字）且无疑似标点
        if (len(toks) >= 3 and all(_CJK_SHORT.match(t) for t in toks)
                and not re.search(r'[。，、；：！？（）《》“”]', line)):
            continue
        if line and line == prev:
            rep += 1
            if rep >= 2:
                continue
        else:
            rep = 0
        prev = line
        out.append(line)
    # Pass 2：遇到明确的尾部样板标记即截断（至少已有 6 行正文）
    cut = -1
    content = 0
    for i, l in enumerate(out):
        if l:
            content += 1
        if content >= 6 and _TAIL_RE.match(l):
            cut = i
            break
    kept = out[:cut] if cut >= 0 else out
    # Pass 3：兜底——删除后段中重复出现的长块（间隔 >=12 行）
    seen = {}
    cutoff = -1
    for i, l in enumerate(kept):
        if len(l) >= 25:
            if l in seen and (i - seen[l]) >= 12:
                cutoff = i
                break
            seen[l] = i
    final = kept[:cutoff] if cutoff >= 0 else kept
    # Pass 4：去除开头的导航块（连续的短行/纯导航词，直到出现正文行）
    _NAV_HINT_RE = re.compile(r'邮箱|退出|欢迎来到|我要采购|全网询价|移动端|爱采购|网易|VIP')
    def _is_nav_line(l):
        if not l:
            return False
        if l in _NAV_WORDS:
            return True
        s = _strip_prefix(l)
        if s in _NAV_WORDS:
            return True
        if len(s) <= 12 and not re.search(r'[。！？；：，、（）《》]', s):
            return True
        return False
    def _is_content(l):
        return bool(l) and (len(l) >= 12 or re.search(r'[。！？；]', l))
    while final:
        l = final[0]
        hint = _NAV_HINT_RE.search(l)
        if _is_content(l) and not hint:
            break
        if (not l) or _is_nav_line(l) or hint:
            final.pop(0)
        else:
            break
    while final and final[-1] == '':
        final.pop()
    return '\n'.join(final)


def count_words(text):
    if not text:
        return 0
    return len(re.findall(r'[一-鿿]', text)) + len(re.findall(r'[A-Za-z0-9]+', text))



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
        raw_body = r.get('body', '') or ''
        if r.get('video_url') or r.get('status') == 'video':
            body = ''
            wc = 0
        else:
            body = clean_body(raw_body)
            wc = count_words(body)
        c.execute('INSERT OR REPLACE INTO resources (id,url,domain,platform,type,category,categories_json,'
                  'levels_json,note,title,body,word_count,status,fetched_at,video_url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (r['id'], r['url'], r['domain'], r['platform'], r.get('type', '文章'), r['category'],
                   json.dumps(r.get('categories', []), ensure_ascii=False),
                   json.dumps(r.get('levels', []), ensure_ascii=False),
                   r.get('note', ''), r.get('title', ''), body, wc,
                   r.get('status', ''), '', r.get('video_url', '')))

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
