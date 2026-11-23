from pathlib import Path
p=Path('app/web/static/css/main.css')
s=p.read_text(encoding='utf-8')
block='''

/* Unified English typography benchmark for figures and chart surroundings */
.sub-title{font-size:14px;font-weight:600;color:#5d7488}
.card h3{font-size:15.5px;font-weight:780;color:#31536c}
.figure-title{font-size:21px;font-weight:820;color:#0e304e}
.figure-caption{font-size:14px;font-weight:650;color:#5d7488;line-height:1.72}
.figure-panel h3{font-size:16px;font-weight:780;color:#284861}
.figure-note{font-size:13.2px;font-weight:550;color:#526b80;line-height:1.75}
.chart-legend{font-size:15px;font-weight:700;color:#40566c;gap:22px}
.chart-legend span{font-weight:700}.chart-legend i{width:16px;height:11px}
.chart-badge{font-size:12.5px;font-weight:800}.chart-toolbar .btn{font-size:13px;font-weight:700}
.visual-copy h3{font-size:19px;font-weight:800}.visual-copy p{font-size:14px;font-weight:550}
.insight-panel p{font-size:14px;font-weight:550;line-height:1.78}
.story-step b{font-size:14px;font-weight:800}.story-step span{font-size:12.5px;font-weight:600;line-height:1.62}
.hero-stat span{font-size:12.5px;font-weight:650}.floating-chip{font-size:12.5px;font-weight:650}
.banner-caption b{font-size:15px;font-weight:800}.banner-caption span{font-size:13px;font-weight:600}
'''
if 'Unified English typography benchmark' not in s:
    s += block
p.write_text(s,encoding='utf-8')
print('css typography benchmark applied')
