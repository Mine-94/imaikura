from pathlib import Path
import json
import re

root = Path('.')
logo_url = 'https://imaikura.com/assets/logo.svg'
article_image = 'https://imaikura.com/assets/og-default.png'

logo_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-labelledby="title desc">
<title id="title">いまいくら</title><desc id="desc">円の文字を使った、いまいくらのロゴ</desc>
<rect width="512" height="512" rx="112" fill="#14334b"/>
<circle cx="256" cy="256" r="174" fill="#ffffff"/>
<text x="256" y="326" text-anchor="middle" font-family="Noto Sans JP, Hiragino Kaku Gothic ProN, Yu Gothic, sans-serif" font-size="218" font-weight="800" fill="#14334b">円</text>
</svg>'''
(root / 'assets').mkdir(exist_ok=True)
(root / 'assets/logo.svg').write_text(logo_svg, encoding='utf-8')
(root / 'assets/favicon.svg').write_text(logo_svg, encoding='utf-8')

meta_updates = {
    'help/index.html': {
        'title': '計算ツールの使い方・よくある質問｜入力方法と結果の見方｜いまいくら',
        'description': 'いまいくらの計算ツールについて、正しい入力方法、年分・年度・適用月の選び方、概算と確定額の違い、給与明細と結果が異なる理由、入力データの取り扱い、よくある質問をまとめています。',
    },
    'contact/index.html': {
        'title': 'お問い合わせ・計算誤り・制度更新の報告｜いまいくら',
        'description': 'いまいくらへのお問い合わせ窓口です。計算結果や計算式の誤り、制度改正の反映漏れ、公式資料のリンク切れ、文章の修正、スマートフォンやブラウザの表示不具合を報告できます。',
    },
    'retirement-income-guide/index.html': {
        'description': '退職金にかかる所得税・住民税の仕組み、退職所得控除、2分の1課税、勤続年数5年以下の例外、申告書を提出しない場合の扱い、手取りを確認する手順を公的資料に基づいて解説します。',
    },
}

script_re = re.compile(r'(<script[^>]+type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)', re.I | re.S)

def enrich(obj):
    if isinstance(obj, dict):
        typ = obj.get('@type')
        types = typ if isinstance(typ, list) else [typ]
        if 'Organization' in types:
            obj.setdefault('logo', {
                '@type': 'ImageObject',
                'url': logo_url,
                'contentUrl': logo_url,
                'width': 512,
                'height': 512,
            })
        if any(item in types for item in ('Article', 'NewsArticle', 'BlogPosting')):
            obj.setdefault('image', {
                '@type': 'ImageObject',
                'url': article_image,
                'contentUrl': article_image,
                'width': 1200,
                'height': 630,
            })
            obj.setdefault('thumbnailUrl', article_image)
        for value in obj.values():
            enrich(value)
    elif isinstance(obj, list):
        for value in obj:
            enrich(value)

for path in sorted(root.rglob('index.html')):
    text = path.read_text(encoding='utf-8')
    rel = path.as_posix()
    prefix = '' if path.parent == root else '../'

    if rel in meta_updates:
        update = meta_updates[rel]
        if update.get('title'):
            text = re.sub(r'<title>.*?</title>', f'<title>{update["title"]}</title>', text, count=1, flags=re.I | re.S)
        if update.get('description'):
            description = update['description']
            text = re.sub(
                r'(<meta[^>]+name=["\']description["\'][^>]+content=["\'])(.*?)(["\'][^>]*>)',
                lambda match: match.group(1) + description + match.group(3),
                text,
                count=1,
                flags=re.I | re.S,
            )

    if not re.search(r'<link[^>]+rel=["\'][^"\']*\bicon\b[^"\']*["\']', text, re.I):
        icon = f'<link rel="icon" type="image/svg+xml" href="{prefix}assets/favicon.svg">\n'
        match = re.search(r'(<link[^>]+rel=["\']canonical["\'][^>]*>)', text, re.I)
        if match:
            text = text[:match.end()] + '\n' + icon + text[match.end():]
        else:
            text = text.replace('</head>', icon + '</head>', 1)

    def replace_jsonld(match):
        try:
            obj = json.loads(match.group(2).strip())
        except Exception:
            return match.group(0)
        enrich(obj)
        return match.group(1) + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + match.group(3)

    text = script_re.sub(replace_jsonld, text)
    path.write_text(text, encoding='utf-8')

print('patched', len(list(root.rglob('index.html'))), 'HTML pages')
