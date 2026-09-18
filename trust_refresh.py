from __future__ import annotations
import argparse, hashlib, html, json, re, urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
VERSION='2026-09-18-trust-v1'
CSS='.hero{grid-template-columns:minmax(0,1fr)!important;gap:0!important}.hero-copy{max-width:860px}.hero-description{max-width:65ch}.ss-rating{display:inline-flex;align-items:center;flex-wrap:wrap;gap:.5rem 1rem;max-width:100%;margin:1.2rem 0 1.5rem;padding:.8rem 1rem;border:1px solid currentColor;border-radius:12px;color:inherit;text-decoration:none;font-size:.95rem;line-height:1.5}.ss-rating strong{font-size:1.15rem}.ss-trust{padding-top:clamp(3rem,6vw,6rem);padding-bottom:clamp(3rem,6vw,6rem)}.ss-trust-kicker{text-transform:uppercase;letter-spacing:.14em;font-size:.75rem;margin:0 0 1rem}.ss-trust h2{font-family:inherit;font-size:clamp(1.8rem,3vw,2.8rem);line-height:1.15;margin:0 0 1rem;max-width:24ch}.ss-trust-summary{max-width:65ch;line-height:1.7;margin:0 0 2rem}.ss-review-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.ss-review-card{margin:0;padding:clamp(1.3rem,3vw,2rem);border:1px solid color-mix(in srgb,currentColor 22%,transparent);border-radius:16px;min-width:0;display:flex;flex-direction:column;gap:1rem}.ss-review-card blockquote{padding:0;margin:0;font:inherit;font-size:clamp(1.1rem,2vw,1.35rem);line-height:1.6;overflow-wrap:anywhere}.ss-review-card figcaption{margin-top:auto;line-height:1.6;font-size:.85rem}.ss-review-card cite{font-style:normal;font-weight:600}.ss-review-meta{display:block;font-size:.78rem;opacity:.8}.ss-review-stars{font-size:.8rem;letter-spacing:.06em}.ss-trust-note{font-size:.76rem;line-height:1.65;margin-top:1.5rem;opacity:.8}.ss-trust a{color:inherit;text-underline-offset:4px}.ss-trust a:focus-visible,.ss-rating:focus-visible{outline:3px solid currentColor;outline-offset:5px}@media(max-width:640px){.ss-review-grid{grid-template-columns:1fr}.ss-rating{font-size:.84rem;gap:.35rem .7rem}.hero-copy{max-width:100%}}'
class HeroVisual(HTMLParser):
 def __init__(self,text):
  super().__init__(convert_charrefs=False);self.text=text;self.start=None;self.tag=None;self.depth=0;self.ranges=[];self.lines=[0]+[m.end() for m in re.finditer('\n',text)]
 def pos(self):
  line,col=self.getpos();return self.lines[line-1]+col
 def handle_starttag(self,tag,attrs):
  if self.start is not None:
   if tag==self.tag:self.depth+=1
  elif 'hero-visual' in dict(attrs).get('class','').split():self.start=self.pos();self.tag=tag;self.depth=1
 def handle_endtag(self,tag):
  if self.start is not None and tag==self.tag:
   self.depth-=1
   if self.depth==0:self.ranges.append((self.start,self.text.find('>',self.pos())+1));self.start=None;self.tag=None

def contact_links(text):
 return sorted(re.findall(r'href=["\x27]((?:tel:|https://wa.me/)[^"\x27]+)',text))

def apply(source,d):
 assert d.get('version')==VERSION
 assert 1<=float(d['rating'])<=5 and int(d['review_count'])>0
 assert d['source'].startswith('https://www.google.com/maps/')
 assert d['phone'] in source and 'hero-copy' in source and '</h1>' in source
 quotes=d['reviews'];assert len(quotes)<=3 and sum(len(q['quote'].split()) for q in quotes)<=25
 for q in quotes:
  assert q['author'].strip() and q['quote'].strip() and q['stars'] in (4,5);date.fromisoformat(q['date'])
 original=source
 for key in ['STYLE','BADGE','REVIEWS']:source=re.sub('<!--SS_TRUST_'+key+'_START-->.*?<!--SS_TRUST_'+key+'_END-->','',source,flags=re.S)
 parser=HeroVisual(source);parser.feed(source);assert parser.start is None and len(parser.ranges)<=1
 for a,b in reversed(parser.ranges):source=source[:a]+source[b:]
 e=lambda v:html.escape(str(v),quote=True)
 rating=f"{float(d['rating']):.1f}";count=f"{int(d['review_count']):,}";target=e(d['source'])
 style='<!--SS_TRUST_STYLE_START--><style id="ss-trust-styles">'+CSS+'</style><!--SS_TRUST_STYLE_END-->'
 badge='<!--SS_TRUST_BADGE_START--><a class="ss-rating" href="'+target+'" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">★</span><strong>'+rating+' / 5 on Google</strong><span>'+count+' reviews</span></a><!--SS_TRUST_BADGE_END-->'
 cards=[]
 for q in quotes:
  stamp=date.fromisoformat(q['date']).strftime('%d %b %Y');quotation=e(q['quote'])+(' …' if q.get('excerpt') else '');url=e(q.get('url') or d['source'])
  cards.append('<figure class="ss-review-card"><span class="ss-review-stars">'+str(q['stars'])+' / 5 · Google review</span><blockquote>“'+quotation+'”</blockquote><figcaption><cite>'+e(q['author'])+'</cite><span class="ss-review-meta">'+stamp+'</span><a href="'+url+'" target="_blank" rel="noopener noreferrer">Read on Google</a></figcaption></figure>')
 section='<!--SS_TRUST_REVIEWS_START--><section class="ss-trust wrap" id="google-reviews" aria-labelledby="ss-review-heading"><p class="ss-trust-kicker">Selected Google review excerpts</p><h2 id="ss-review-heading">A reputation you can look up.</h2><p class="ss-trust-summary"><strong>'+rating+' out of 5</strong>, based on <strong>'+count+' Google reviews</strong>. <a href="'+target+'" target="_blank" rel="noopener noreferrer">Explore the full Google profile</a>.</p><div class="ss-review-grid">'+''.join(cards)+'</div><p class="ss-trust-note">Rating and review count checked on 18 September 2026; this is a dated snapshot, not a live feed. Selected excerpts from public Google reviews; individual experiences vary.</p></section><!--SS_TRUST_REVIEWS_END-->'
 assert '</head>' in source
 source=source.replace('</head>',style+'</head>',1).replace('</h1>','</h1>'+badge,1)
 loc=re.search(r'<section\b[^>]*\bid=["\x27]enquire["\x27][^>]*>',source);assert loc,'Missing enquiry section; do not rebuild'
 source=source[:loc.start()]+section+source[loc.start():]
 assert contact_links(original)==contact_links(source)
 assert source.count('id="google-reviews"')==1 and source.count('id="ss-trust-styles"')==1
 audit={'version':VERSION,'business':d['business'],'source':d['source'],'rating':d['rating'],'review_count':d['review_count'],'checked_on':d['checked_on'],'quoted_reviews':len(quotes),'quoted_words':sum(len(q['quote'].split()) for q in quotes),'hero':'text-led; business photos have not been visually verified','original_sha256':hashlib.sha256(original.encode()).hexdigest(),'updated_sha256':hashlib.sha256(source.encode()).hexdigest(),'contact_destinations_preserved':True}
 return source,audit

def main():
 p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--rows',required=True);p.add_argument('--output',default='prepared');p.add_argument('--sources');a=p.parse_args();wanted=set(map(int,a.rows.split(',')));data=json.loads(Path(a.manifest).read_text());report=[]
 for d in data:
  if d['row'] not in wanted:continue
  try:
   if a.sources:source=(Path(a.sources)/(d['slug']+'.html')).read_text(encoding='utf-8')
   else:
    u='https://raw.githubusercontent.com/SharpSites-Demo/'+d['slug']+'/gh-pages/index.html'
    with urllib.request.urlopen(u,timeout=30) as r:source=r.read().decode('utf-8')
   updated,audit=apply(source,d);out=Path(a.output)/d['slug'];out.mkdir(parents=True,exist_ok=True)
   (out/'index.html').write_text(updated,encoding='utf-8');(out/'sharpsites-trust.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');(out/'sharpsites-trust-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
   report.append({'row':d['row'],'repo':'SharpSites-Demo/'+d['slug'],'prepared':True,'html_sha256':audit['updated_sha256'],'files':[str(out/x) for x in ['index.html','sharpsites-trust.json','sharpsites-trust-audit.json']]})
  except Exception as ex:report.append({'row':d['row'],'prepared':False,'error':str(ex)})
 Path(a.output).mkdir(exist_ok=True,parents=True);Path(a.output,'preparation-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
