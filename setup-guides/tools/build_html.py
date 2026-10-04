"""setup-guides/*.md をアーティファクト公開用の HTML に変換する。

使い方:
    pip install markdown
    python3 setup-guides/tools/build_html.py [出力先]   # 既定: setup-guides/tools/out

出力された <名前>.html を、DOCS にある URL のアーティファクトへ上書き公開する。
"""
import os, re, sys
import markdown
from markdown.extensions.toc import slugify_unicode

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SRC, 'tools', 'out')
os.makedirs(OUT, exist_ok=True)
DOCS=[('full-build-guide','UQ2CnYtdPN3hYV7owG4wZQ','組む順番'),
      ('dev-environment-map','2rFMQREMuY9xioDRpGfjkE','現況の地図'),
      ('eclipse-spring-setup','Y41hjzjgRYfb6UDYuTBs8J','Java・Spring・DB'),
      ('xcode-claude-setup','Xu6T46zjyfxDUZKq44aS83','Xcode・認証・MCP'),
      ('mac-setup','BG5zw9e2TpgDdwRU4NCV5f','日々の使い方')]
URL={n:'https://claude.ai/artifact/'+i for n,i,_ in DOCS}
CSS=r'''
/* Layout: single reading column with a document switcher on top and a compact section index */
:root{
  --paper:#f7f8fa; --ink:#1d2430; --muted:#5b6575; --rule:#d9dee6; --fill:#eceff4;
  --accent:#2d5d8f; --warn:#9a6a00; --warn-bg:#fbf3df; --stop:#a83a32; --stop-bg:#f9e7e5;
  --f-body:"BIZ UDPGothic","Hiragino Sans","Noto Sans JP",system-ui,sans-serif;
  --f-head:"Zen Kaku Gothic New","BIZ UDPGothic","Hiragino Sans",system-ui,sans-serif;
  --f-mono:"JetBrains Mono","SF Mono",ui-monospace,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#14181e; --ink:#dfe4ec; --muted:#98a2b3; --rule:#2c3440; --fill:#1d232c;
  --accent:#7fb0e0; --warn:#e3b74f; --warn-bg:#2a2414; --stop:#ee8a80; --stop-bg:#2e1b1a; color-scheme:dark}}
:root[data-theme="dark"]{
  --paper:#14181e; --ink:#dfe4ec; --muted:#98a2b3; --rule:#2c3440; --fill:#1d232c;
  --accent:#7fb0e0; --warn:#e3b74f; --warn-bg:#2a2414; --stop:#ee8a80; --stop-bg:#2e1b1a; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font:15px/1.75 var(--f-body);margin:0;padding-inline:16px;padding-block:0 64px}
.wrap{max-width:780px;margin:0 auto}
nav.docs{display:flex;flex-wrap:wrap;gap:4px 6px;padding-block:14px;border-bottom:1px solid var(--rule);margin-bottom:28px}
nav.docs a{font:12px/1.4 var(--f-body);color:var(--muted);text-decoration:none;padding:5px 9px;border:1px solid var(--rule);border-radius:4px;display:flex;flex-direction:column}
nav.docs a b{font:600 12px/1.3 var(--f-mono);color:var(--ink)}
nav.docs a:hover{border-color:var(--accent)}
nav.docs a[aria-current]{border-color:var(--accent);background:var(--fill)}
nav.docs a[aria-current] b{color:var(--accent)}
h1,h2,h3,h4{font-family:var(--f-head);line-height:1.35;text-wrap:balance;margin:0}
h1{font-size:1.75rem;font-weight:700;margin-bottom:12px}
h2{font-size:1.3rem;font-weight:700;margin-top:44px;padding-top:12px;border-top:2px solid var(--ink)}
h3{font-size:1.08rem;font-weight:700;margin-top:28px}
h4{font-size:1rem;margin-top:20px;color:var(--muted)}
p,ul,ol,table,pre,blockquote,.tbl{margin:12px 0}
ul,ol{padding-left:1.4em}
li+li{margin-top:4px}
a{color:var(--accent);text-underline-offset:2px}
a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
strong{font-weight:700}
hr{border:0;margin:0}
code{font:0.86em var(--f-mono);background:var(--fill);padding:1px 4px;border-radius:3px;overflow-wrap:anywhere}
pre{background:var(--fill);border:1px solid var(--rule);border-radius:4px;padding:12px 14px;overflow-x:auto;font:12.5px/1.6 var(--f-mono)}
pre code{background:none;padding:0;font:inherit;overflow-wrap:normal}
pre.mermaid{background:transparent;border:1px dashed var(--rule);text-align:center}
.tbl{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13.5px;font-variant-numeric:tabular-nums;margin:0}
th,td{text-align:left;vertical-align:top;padding:7px 10px;border-bottom:1px solid var(--rule)}
th{font-weight:700;border-bottom:2px solid var(--ink);white-space:nowrap}
td code,th code{background:transparent;padding:0}
blockquote{margin-left:0;padding:10px 14px;border-left:3px solid var(--rule);color:var(--ink);background:transparent}
blockquote>:first-child{margin-top:0} blockquote>:last-child{margin-bottom:0}
blockquote.warn{border-color:var(--warn);background:var(--warn-bg)}
blockquote.stop{border-color:var(--stop);background:var(--stop-bg)}
blockquote.role{border-color:var(--accent);background:var(--fill)}
details.toc{margin:20px 0 8px;border:1px solid var(--rule);border-radius:4px;padding:8px 14px;font-size:13.5px}
details.toc summary{cursor:pointer;font-weight:700;color:var(--muted)}
details.toc ul{margin:8px 0 4px;columns:2 220px;column-gap:24px}
details.toc li{break-inside:avoid}
footer{margin-top:48px;padding-top:12px;border-top:1px solid var(--rule);font-size:12px;color:var(--muted)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
'''
FONTS='<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=BIZ+UDPGothic:wght@400;700&family=Zen+Kaku+Gothic+New:wght@700&family=JetBrains+Mono:wght@400;600&display=swap">'
for name,_,label in DOCS:
    md=open(f'{SRC}/{name}.md',encoding='utf8').read()
    m=markdown.Markdown(extensions=['fenced_code','tables','toc','sane_lists'],
        extension_configs={'toc':{'slugify':slugify_unicode,'toc_depth':'2'}})
    body=m.convert(md)
    body=re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>',lambda x:'<pre class="mermaid">'+x.group(1)+'</pre>',body,flags=re.S)
    body=re.sub(r'href="([a-z-]+)\.md"',lambda x:f'href="{URL.get(x.group(1),x.group(0))}"',body)
    body=re.sub(r'<table>',"<div class=\"tbl\"><table>",body); body=body.replace('</table>','</table></div>')
    def bq(x):
        inner=x.group(1); txt=re.sub('<[^>]+>','',inner).strip()
        cls='stop' if txt.startswith('🛑') else 'warn' if txt.startswith('⚠') else 'role' if txt.startswith('担当') else ''
        return f'<blockquote class="{cls}">' if cls else '<blockquote>'
    body=re.sub(r'<blockquote>(\s*<p>.{0,40})',lambda x:bq(x)+x.group(1),body,flags=re.S)
    # remove hr directly before h2 (h2 has its own rule)
    body=re.sub(r'<hr />\s*(?=<h2)','',body)
    # toc after first blockquote.role or after h1 paragraph block
    toks=[t for t in m.toc_tokens[0]['children']] if m.toc_tokens else []
    toc=''.join(f'<li><a href="#{t["id"]}">{t["name"]}</a></li>' for t in toks)
    toc=f'<details class="toc" open><summary>目次</summary><ul>{toc}</ul></details>' if toc else ''
    i=body.find('<h2'); body=body[:i]+toc+body[i:] if i>0 else body
    CUR=' aria-current="page"'
    nav=''.join(f'<a href="{URL[n]}"{CUR if n==name else ""}><b>{n}</b>{l}</a>' for n,_,l in DOCS)
    page=f'''<title>{name}.md</title>
<meta name="color-scheme" content="light dark">
{FONTS}
<style>{CSS}</style>
<div class="wrap">
<nav class="docs" aria-label="環境ドキュメント">{nav}</nav>
<main>
{body}
</main>
<footer>正本は Mac の <code>~/Documents/setup-guides/{name}.md</code>。リポジトリ版は MS1977/TestProject の <code>setup-guides/</code>。</footer>
</div>
'''
    open(f'{OUT}/{name}.html','w',encoding='utf8').write(page)
    print(name,len(page))
