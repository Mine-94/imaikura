from pathlib import Path
from bs4 import BeautifulSoup
import re

root=Path('.')

# Correct the representative date so the test sits in the 12-day grant period.
visual=root/'tests/visual-smoke.spec.js'
if visual.exists():
    text=visual.read_text(encoding='utf-8')
    text=text.replace("await page.fill('#hire-date', '2024-04-01');", "await page.fill('#hire-date', '2023-04-01');")
    visual.write_text(text,encoding='utf-8')

# Keep pills, labels and buttons content-driven instead of clipping Japanese text.
css_path=root/'assets/site.css'
css=css_path.read_text(encoding='utf-8')
if 'layout-quality-v3-hotfix' not in css:
    css += '''\n/* layout-quality-v3-hotfix */\n.trust-badge,.tool-no,.badge,.result-eyebrow{height:auto;min-height:40px;padding-block:8px;}\nbutton,.button,.btn,.primary-button{height:auto;min-height:48px;padding-block:11px;}\n.brand-mark{min-height:44px;padding:0;}\n@media(max-width:420px){.brand-mark{min-height:40px;}}\n'''
css_path.write_text(css,encoding='utf-8')

# Recount guide cards and make labels accurate even when another release landed first.
guides_path=root/'guides/index.html'
if guides_path.exists():
    soup=BeautifulSoup(guides_path.read_text(encoding='utf-8'),'html.parser')
    guide_count=len(soup.select('.tool-grid a.tool-card'))
    text=str(soup)
    text=re.sub(r'\d+本の制度ガイド',f'{guide_count}本の制度ガイド',text)
    text=re.sub(r'\d+本のガイド',f'{guide_count}本のガイド',text)
    text=re.sub(r'制度を公的資料から解説する\d+本',f'制度を公的資料から解説する{guide_count}本',text)
    guides_path.write_text(text,encoding='utf-8')
else:
    guide_count=0

home_path=root/'index.html'
if home_path.exists():
    soup=BeautifulSoup(home_path.read_text(encoding='utf-8'),'html.parser')
    tool_count=len(soup.select('[data-search]'))
    for index,card in enumerate(soup.select('[data-search]'),1):
        number=card.select_one('.tool-no')
        if number: number.string=f'{index:02d}'
    text=str(soup)
    if guide_count:
        text=re.sub(r'現在\s*\d+ツール・\d+ガイド公開中',f'現在 {tool_count}ツール・{guide_count}ガイド公開中',text)
        text=re.sub(r'すべての制度ガイドを見る（\d+本）',f'すべての制度ガイドを見る（{guide_count}本）',text)
    home_path.write_text(text,encoding='utf-8')

# Add permanent paid-leave calculation boundaries to the main quality gate once.
workflow_path=root/'.github/workflows/site-quality.yml'
workflow=workflow_path.read_text(encoding='utf-8')
if "require('./assets/paid-leave-engine.js')" not in workflow:
    block="""
          const paid = require('./assets/paid-leave-engine.js');
          let leave = paid.calculatePaidLeave({hireDate:'2023-04-01',referenceDate:'2026-09-05',scheduleMode:'weekly',weeklyDays:5,weeklyHours:40,attendanceRate:95,daysTaken:4});
          assert.strictEqual(leave.ok, true);
          assert.strictEqual(leave.statutoryGrantDays, 12);
          assert.strictEqual(leave.remainingDays, 8);
          leave = paid.calculatePaidLeave({hireDate:'2026-04-01',referenceDate:'2026-09-05',scheduleMode:'weekly',weeklyDays:3,weeklyHours:18,attendanceRate:100,daysTaken:0});
          assert.strictEqual(leave.beforeFirstGrant, true);
          assert.strictEqual(leave.firstGrantDays, 5);
          assert.strictEqual(leave.firstGrantDate, '2026-10-01');
"""
    marker="          console.log('calculator tests: PASS');"
    if marker in workflow:
        workflow=workflow.replace(marker,block+"\n"+marker)
    else:
        marker="          console.log('calculator boundary tests: PASS');"
        workflow=workflow.replace(marker,block+"\n"+marker)
workflow_path.write_text(workflow,encoding='utf-8')

print('paid leave release hotfix applied')
