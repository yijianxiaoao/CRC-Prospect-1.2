from pathlib import Path
import re
for p in Path('app/web/static/images').glob('*.svg'):
    s=p.read_text(encoding='utf-8')
    print('\n###',p.name)
    for m in re.finditer(r'<style[^>]*>(.*?)</style>',s,re.S):
        print(m.group(1).strip())
    for m in re.finditer(r'<text[^>]*font-size="([^"]+)"[^>]*>(.*?)</text>',s,re.S):
        print('inline',m.group(1),re.sub('<[^>]+>','',m.group(2))[:80])
