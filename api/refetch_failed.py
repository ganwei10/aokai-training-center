#!/usr/bin/env python3
"""重新抓取 resources.json 中 status != 'ok' 的外部资源正文，更新 resources.json。

策略：浏览器 UA + 重试 + verify=False 绕过证书问题 + http→https 兜底 + 较长超时。
trafilatura 优先提取正文，失败则 BeautifulSoup + html2text 兜底。
确实不可达（如 404）保持为仅链接。
"""
import os, json, re, warnings
warnings.filterwarnings('ignore')
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import trafilatura
from bs4 import BeautifulSoup
import html2text

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, 'data', 'resources.json')


def make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })
    retry = Retry(total=1, backoff_factor=0.5,
                  status_forcelist=[500, 502, 503, 504])
    s.mount('http://', HTTPAdapter(max_retries=retry))
    s.mount('https://', HTTPAdapter(max_retries=retry))
    return s


def fetch_text(session, url):
    cands = [url]
    if url.startswith('http://'):
        cands.insert(0, 'https://' + url[len('http://'):])
    last_err = 'no attempt'
    for cand in cands:
        try:
            r = session.get(cand, timeout=12, verify=False, allow_redirects=True)
            if r.status_code == 200 and len(r.content) > 500:
                extracted = trafilatura.extract(r.text, url=cand,
                                                 include_comments=False, favor_precision=True)
                if extracted and len(extracted) > 300:
                    return extracted.strip(), 'ok'
                soup = BeautifulSoup(r.text, 'html.parser')
                for t in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg']):
                    t.decompose()
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.body_width = 0
                h.ignore_images = True
                txt = h.handle(str(soup))
                txt = re.sub(r'\n{3,}', '\n\n', txt).strip()
                if len(txt) > 300:
                    return txt, 'ok'
                return txt, 'content too short (%d)' % len(txt)
            last_err = 'HTTP %d' % r.status_code
        except Exception as e:
            last_err = 'ERR %s' % type(e).__name__
    return None, last_err


def main():
    data = json.load(open(RES, encoding='utf-8'))
    changed = 0
    for r in data:
        if r.get('status') == 'ok':
            continue
        print('re-fetch:', r.get('domain'), r.get('url'), flush=True)
        text, st = fetch_text(make_session(), r['url'])
        if st == 'ok' and text:
            r['body'] = text
            r['word_count'] = len(text)
            r['status'] = 'ok'
            changed += 1
            print('   OK len=%d' % len(text), flush=True)
        else:
            r['status'] = st
            print('   STILL FAIL ->', st, flush=True)
        # 增量保存，避免被沙箱中断时丢失进度
        json.dump(data, open(RES, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sum(1 for r in data if r.get('status') == 'ok')
    print('re-downloaded %d, total ok now %d / %d. saved %s' % (changed, ok, len(data), RES), flush=True)


if __name__ == '__main__':
    main()
