from pathlib import Path
from html.parser import HTMLParser
import unittest
class Page(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.pages=[];self.iframes=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if 'data-page' in a:self.pages.append(a['data-page'])
  if tag=='iframe':self.iframes+=1
class UnifiedFrontendTests(unittest.TestCase):
 def test_one_application_for_original_and_main_entry(self):
  p=Path(__file__).parent/'static';self.assertEqual((p/'index.html').read_bytes(),(p/'original-dashboard.html').read_bytes())
  page=Page();page.feed((p/'index.html').read_text(encoding='utf-8'));self.assertEqual(page.iframes,0);self.assertEqual(len(page.ids),len(set(page.ids)));self.assertEqual(len(page.pages),16)
  self.assertTrue(set(['atlas','station','explorer','mechanical','twin','engineering','live','forecast','replay','ledger','arena','trust','fleet','bearing','evidence','home']).issubset(page.pages))
 def test_no_legacy_demo_simulator_loaded(self):
  s=(Path(__file__).parent/'static'/'index.html').read_text(encoding='utf-8');self.assertNotIn('function sim(',s);self.assertNotIn('Fictional sample',s)
  for name in ['app.js','timeline.js','twin3d.js','recommendations.js','robustness.js','unified.js']:self.assertIn('/'+name,s)
if __name__=='__main__':unittest.main(verbosity=2)
