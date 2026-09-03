from pathlib import Path
import binascii
import json
import re
import struct
import zlib

ROOT = Path('.')
SITE = 'https://imaikura.com'
INDEXNOW_KEY = 'ba7c0e7a8a2f93a3430f16e6994a8c7f'
DATE = '2026-09-03'

share_js = r'''(function () {
  'use strict';
  const cleanTitle = () => document.title.replace(/｜いまいくら.*$/, '').trim();
  const pageUrl = () => document.querySelector('link[rel="canonical"]')?.href || location.href.split('#')[0];
  const track = (method) => {
    if (typeof window.gtag === 'function') {
      window.gtag('event', 'share', { method, content_type: 'article', item_id: location.pathname });
    }
  };
  async function copyUrl(button) {
    const url = pageUrl();
    try {
      await navigator.clipboard.writeText(url);
    } catch (_) {
      const area = document.createElement('textarea');
      area.value = url;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      area.remove();
    }
    const status = button.closest('[data-share-box]')?.querySelector('[data-share-status]');
    if (status) {
      status.textContent = 'URLをコピーしました。';
      window.setTimeout(() => { status.textContent = ''; }, 2500);
    }
    track('copy');
  }
  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-share]');
    if (!button) return;
    const method = button.dataset.share;
    const title = cleanTitle();
    const url = pageUrl();
    if (method === 'native') {
      event.preventDefault();
      if (navigator.share) {
        try { await navigator.share({ title, text: title, url }); track('native'); } catch (_) {}
      } else {
        await copyUrl(button);
      }
    } else if (method === 'copy') {
      event.preventDefault();
      await copyUrl(button);
    } else if (method === 'x') {
      button.href = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url);
      track('x');
    } else if (method === 'line') {
      button.href = 'https://social-plugins.line.me/lineit/share?url=' + encodeURIComponent(url);
      track('line');
    }
  });
})();
'''
(ROOT / 'assets/share.js').write_text(share_js, encoding='utf-8')

css_path = ROOT / 'assets/site.css'
css = css_path.read_text(encoding='utf-8')
if '/* organic-discovery-share */' not in css:
    css += r'''

/* organic-discovery-share */
.share-box{max-width:1120px;margin:34px auto;padding:24px;border:1px solid var(--line);border-radius:var(--radius);background:var(--paper);box-shadow:0 1px 2px rgba(20,47,73,.03)}
.share-box h2{margin:0 0 6px;color:var(--navy);font-size:19px}.share-box p{margin:0;color:var(--muted);font-size:12px;line-height:1.75}
.share-actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:16px}.share-button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;padding:8px 14px;border:1px solid var(--line-strong);border-radius:9px;background:#fff;color:var(--blue-dark);font-size:12px;font-weight:800;cursor:pointer;text-decoration:none}.share-button:hover{border-color:var(--blue);background:#edf6fd}.share-button.primary{background:var(--blue);border-color:var(--blue);color:#fff}.share-button.primary:hover{background:var(--blue-dark)}
.share-status{min-height:1.6em;margin-top:8px!important;color:#096c66!important;font-weight:700}.feed-link{display:inline-flex;align-items:center;margin-top:12px;font-size:12px;font-weight:800;color:var(--blue-dark)}
@media(max-width:620px){.share-box{margin:24px 16px;padding:19px}.share-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.share-button{width:100%}}
'''
    css_path.write_text(css, encoding='utf-8')

# Pure-Python 1200x630 branded PNG. No external image package is required.
W, H = 1200, 630
pixels = bytearray(W * H * 3)
for y in range(H):
    for x in range(W):
        i = (y * W + x) * 3
        t = x / (W - 1)
        pixels[i] = int(13 + 16 * t)
        pixels[i + 1] = int(43 + 34 * t)
        pixels[i + 2] = int(72 + 53 * t)

def rect(x0, y0, x1, y1, rgb):
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    for yy in range(y0, y1):
        start = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = start + (xx - x0) * 3
            pixels[i:i+3] = bytes(rgb)

def circle(cx, cy, radius, rgb):
    r2 = radius * radius
    for yy in range(max(0, cy-radius), min(H, cy+radius+1)):
        dy2 = (yy-cy)*(yy-cy)
        for xx in range(max(0, cx-radius), min(W, cx+radius+1)):
            if (xx-cx)*(xx-cx)+dy2 <= r2:
                i=(yy*W+xx)*3; pixels[i:i+3]=bytes(rgb)

FONT = {
    'I':['11111','00100','00100','00100','00100','00100','11111'],
    'M':['10001','11011','10101','10101','10001','10001','10001'],
    'A':['01110','10001','10001','11111','10001','10001','10001'],
    'K':['10001','10010','10100','11000','10100','10010','10001'],
    'U':['10001','10001','10001','10001','10001','10001','01110'],
    'R':['11110','10001','10001','11110','10100','10010','10001']
}
def text_bitmap(text, x, y, scale, rgb):
    cursor = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph:
            for gy,row in enumerate(glyph):
                for gx,v in enumerate(row):
                    if v == '1': rect(cursor+gx*scale, y+gy*scale, cursor+(gx+1)*scale, y+(gy+1)*scale, rgb)
            cursor += 6*scale
        else:
            cursor += 3*scale

circle(990, 148, 86, (80, 205, 194))
rect(945, 105, 1035, 118, (13,43,72)); rect(945, 145, 1035, 158, (13,43,72))
rect(984, 92, 997, 202, (13,43,72)); rect(953, 118, 984, 131, (13,43,72)); rect(997, 118, 1028, 131, (13,43,72))
text_bitmap('IMAIKURA', 82, 220, 18, (255,255,255))
rect(82, 392, 635, 399, (80,205,194))
rect(82, 435, 520, 448, (218,232,241)); rect(82, 468, 645, 481, (218,232,241)); rect(82, 501, 570, 514, (218,232,241))
rect(905, 438, 1085, 448, (80,205,194)); rect(905, 470, 1115, 480, (218,232,241)); rect(905, 502, 1042, 512, (218,232,241))

raw = bytearray()
stride = W * 3
for y in range(H):
    raw.append(0)
    raw.extend(pixels[y*stride:(y+1)*stride])
def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', binascii.crc32(kind + data) & 0xffffffff)
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')
(ROOT / 'assets/og-default.png').write_bytes(png)

items = [
    ('給与から手取りが決まる仕組み｜何がいくら引かれる？','salary-deductions-guide','額面給与から健康保険、厚生年金、雇用保険、所得税、住民税がどのように差し引かれ、手取りが決まるのかを公的資料に基づいて解説します。','2026-09-03'),
    ('残業代の計算方法｜割増率25・50・35％と深夜労働','overtime-pay-guide','残業代の基礎単価、法定内残業、時間外、月60時間超、深夜、法定休日の割増率を解説します。','2026-09-03'),
    ('標準報酬月額とは？社会保険料が決まる仕組み','standard-remuneration-guide','健康保険料・厚生年金保険料の基準となる標準報酬月額、定時決定、随時改定、賞与との違いを解説します。','2026-09-03'),
    ('住民税はいつから引かれる？前年所得・6月開始の仕組み','resident-tax-guide','住民税が前年所得で決まり、会社員は原則6月から翌年5月まで給与天引きされる仕組みを解説します。','2026-09-03'),
    ('住宅ローン控除 2026年ガイド｜条件・限度額・確定申告','housing-loan-deduction-guide','2026年入居の新築住宅について、0.7％の計算、住宅区分別の借入限度額、床面積、所得、返済期間、初年度申告を解説します。','2026-09-03'),
    ('ボーナスの手取りはどう決まる？社会保険料と所得税','bonus-take-home-guide','賞与から健康保険、厚生年金、雇用保険、源泉所得税が引かれる仕組みを解説します。','2026-09-03'),
    ('年末調整とは？仕組みと還付金のしくみをやさしく解説','year-end-adjustment-guide','年末調整の仕組み、還付・追加徴収、必要書類、確定申告が必要なケースを解説します。','2026-09-02'),
    ('ふるさと納税とは？仕組みと始め方をやさしく解説','furusato-nozei-guide','自己負担2,000円の考え方、ワンストップ特例と確定申告、上限額の考え方を解説します。','2026-09-02')
]
from email.utils import format_datetime
from datetime import datetime, timezone
def xml_escape(value):
    return value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
rss_items = []
for title, slug, description, date in items:
    pub = format_datetime(datetime.fromisoformat(date).replace(tzinfo=timezone.utc))
    url = f'{SITE}/{slug}/'
    rss_items.append(f'<item><title>{xml_escape(title)}</title><link>{url}</link><guid isPermaLink="true">{url}</guid><pubDate>{pub}</pubDate><description>{xml_escape(description)}</description></item>')
feed = f'''<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>いまいくら｜日本のお金・税金・仕事の計算とガイド</title><link>{SITE}/</link><description>日本の給与、税金、社会保険、控除、働き方に関する計算ツールと公的資料ベースのガイド更新情報です。</description><language>ja</language><atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/><lastBuildDate>Thu, 03 Sep 2026 18:30:00 +0000</lastBuildDate>{''.join(rss_items)}</channel></rss>\n'''
(ROOT / 'feed.xml').write_text(feed, encoding='utf-8')
(ROOT / f'{INDEXNOW_KEY}.txt').write_text(INDEXNOW_KEY + '\n', encoding='utf-8')

readme = '''# いまいくら\n\n日本の給与・税金・社会保険・控除・働き方を、公的資料と適用時期を確認しながら計算できる無料サイトです。\n\n- 公開サイト: https://imaikura.com/\n- 計算ツール一覧: https://imaikura.com/site-map/\n- 更新フィード: https://imaikura.com/feed.xml\n- 運営・計算基準: https://imaikura.com/about/\n- 訂正・不具合の連絡: https://imaikura.com/contact/\n\n## 主な分野\n\n給与・年収の手取り、社会保険料、賞与、残業代、勤務時間、年収の壁、住民税、医療費控除、住宅ローン控除、ふるさと納税、消費税。\n\n## 情報方針\n\n日本の法令、国税庁、厚生労働省、日本年金機構、全国健康保険協会、地方公共団体などの公的資料を優先し、適用年・前提条件・結果の性質を各ページに表示します。\n'''
(ROOT / 'README.md').write_text(readme, encoding='utf-8')

utility = {'about/index.html','contact/index.html','privacy/index.html','terms/index.html','site-map/index.html','updates/index.html'}
feed_meta = '<link rel="alternate" type="application/rss+xml" title="いまいくら 更新フィード" href="https://imaikura.com/feed.xml">'
social_meta = '''<meta property="og:site_name" content="いまいくら">\n<meta property="og:image" content="https://imaikura.com/assets/og-default.png">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n<meta property="og:image:alt" content="いまいくら｜日本のお金・税金・仕事の無料計算ツール">\n<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:image" content="https://imaikura.com/assets/og-default.png">'''

def share_box(prefix):
    return f'''\n<section class="content-section share-box" data-share-box aria-labelledby="share-title"><h2 id="share-title">このページを共有</h2><p>あとで見返すための保存や、同じ制度を調べている人への共有にご利用ください。</p><div class="share-actions"><button class="share-button primary" type="button" data-share="native">共有する</button><a class="share-button" href="#" target="_blank" rel="noopener" data-share="x">Xで共有</a><a class="share-button" href="#" target="_blank" rel="noopener" data-share="line">LINEで共有</a><button class="share-button" type="button" data-share="copy">URLをコピー</button></div><p class="share-status" data-share-status aria-live="polite"></p><a class="feed-link" href="{prefix}feed.xml">RSSで新しいガイドを受け取る</a></section>\n'''

for path in sorted(ROOT.rglob('*.html')):
    rel = path.as_posix()
    if rel == '404.html':
        continue
    text = path.read_text(encoding='utf-8')
    if 'type="application/rss+xml"' not in text:
        text = text.replace('</head>', feed_meta + '\n</head>', 1)
    if 'property="og:site_name"' not in text:
        text = text.replace('</head>', social_meta + '\n</head>', 1)
    if rel not in utility and 'data-share-box' not in text:
        prefix = '' if rel == 'index.html' else '../'
        text = text.replace('</main>', share_box(prefix) + '</main>', 1)
        text = text.replace('</body>', f'<script src="{prefix}assets/share.js" defer></script>\n</body>', 1)
    path.write_text(text, encoding='utf-8')

rss_card = '''\n<section class="content-card" data-feed-promo><h2>RSSで更新を受け取る</h2><p>新しい制度ガイドや重要な訂正を、フィードリーダーから確認できます。</p><p><a class="card-link" href="../feed.xml">いまいくらのRSSフィードを開く</a></p></section>\n'''
for rel in ('site-map/index.html','updates/index.html'):
    path = ROOT / rel
    text = path.read_text(encoding='utf-8')
    if 'data-feed-promo' not in text:
        text = text.replace('</main>', rss_card + '</main>', 1)
    path.write_text(text, encoding='utf-8')

updates_path = ROOT / 'updates/index.html'
updates = updates_path.read_text(encoding='utf-8')
if '検索エンジン通知と共有機能を追加' not in updates:
    entry = '<article class="update-entry"><time datetime="2026-09-03">2026年9月3日</time><h2>検索エンジン通知と共有機能を追加</h2><p>更新URLをIndexNowへ通知する仕組み、RSSフィード、X・LINE・端末共有・URLコピー、SNS用プレビュー画像を追加しました。検索エンジンと利用者の双方が新しいガイドを見つけやすい構成へ改善しています。</p></article>'
    updates = updates.replace('<section class="content-card"><div class="update-list">', '<section class="content-card"><div class="update-list">' + entry, 1)
    updates_path.write_text(updates, encoding='utf-8')
