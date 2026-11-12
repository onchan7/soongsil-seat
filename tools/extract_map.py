"""Extract actual StudySeat models from the supplied Roblox XML; no invented seats."""
import sys,json,xml.etree.ElementTree as E
from pathlib import Path
r=E.parse(sys.argv[1]).getroot(); seats=[]
for i in r.iter('Item'):
 n=i.find("Properties/string[@name='Name']")
 if n is None or not (n.text or '').startswith('StudySeat_'): continue
 p=i.find("Item[@class='Seat']/Properties/CoordinateFrame[@name='CFrame']")
 if p is None: continue
 _,floor,label=n.text.split('_'); demo=floor=='DEMO'
 seats.append(dict(id=n.text.removeprefix('StudySeat_'),floor='1F' if demo else floor,label='D' if demo else label,kind='demo' if demo else 'study',x=float(p.find('X').text),z=float(p.find('Z').text),model=n.text))
assert len(seats)==83 and len({s['id'] for s in seats})==83
Path('dist/seats.json').write_text(json.dumps(dict(source='Soongsil_Central_Library.rbxlx · version 2',seats=seats),ensure_ascii=False,indent=2))
print('Extracted',len(seats),'seats')
