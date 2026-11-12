"""UNO Q Linux: RFID Bridge + SQLite + HTTP API + the exact same static website."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import argparse,json,os,secrets,sys,uuid,mimetypes,hmac,threading
from urllib.parse import urlsplit,unquote
from engine import Engine,SeatError
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',default=str(ROOT/'config.local.json'));p.add_argument('--no-bridge',action='store_true',help='Use for API-only server/testing; hardware not enabled');p.add_argument('--init',action='store_true');a=p.parse_args();cfgpath=Path(a.config)
 if a.init:
  if cfgpath.exists():sys.exit('Existing config preserved; edit it manually.')
  cfg={'host':'0.0.0.0','port':8080,'allowed_origins':[],'secret':secrets.token_hex(32),'readers':{'reader-01':{'seat_id':'B1_001','token':secrets.token_urlsafe(32)}}}
  fd=os.open(cfgpath,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
  with os.fdopen(fd,'w') as f:json.dump(cfg,f,indent=2)
  print('Created private config.local.json. Do not commit it.');return
 cfg=json.loads(cfgpath.read_text());runtime=ROOT/'runtime';runtime.mkdir(exist_ok=True)
 engine=Engine(str(runtime/'seats.sqlite3'),json.loads((ROOT/'dist/seats.json').read_text())['seats'],{k:v['seat_id'] for k,v in cfg['readers'].items()},cfg['secret'])
 bridge=None
 if not a.no_bridge:
  from arduino.router_bridge import Bridge
  bridge=Bridge()
  def new_session(reader):
   if reader not in cfg['readers']:raise SeatError('unknown_reader')
   return uuid.uuid4().hex
  def on_tap(reader,uid,event_id):
   try:return json.dumps(engine.tap(reader,uid,event_id))
   except SeatError as e:return json.dumps({'error':str(e)})
  bridge.provide('seat_session',new_session);bridge.provide('seat_tap',on_tap);bridge.provide('seat_heartbeat',engine.heartbeat)
  if not bridge.connect(timeout=10):sys.exit('UNO Q arduino-router unavailable. Check its service before retrying.')
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,fmt,*args):pass # Never log Authorization or card UIDs.
  def end_headers(self):
   origin=self.headers.get('Origin')
   if origin in cfg.get('allowed_origins',[]):self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Vary','Origin')
   self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
  def reply(self,data,code=200):
   b=json.dumps(data).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
  def do_OPTIONS(self):
   if self.headers.get('Origin') not in cfg.get('allowed_origins',[]):return self.reply({'error':'origin_not_allowed'},403)
   self.send_response(204);self.send_header('Access-Control-Allow-Methods','GET, OPTIONS');self.end_headers()
  def do_GET(self):
   path=urlsplit(self.path).path
   if path=='/api/seats':return self.reply(engine.snapshot())
   if path=='/api/health':return self.reply({'ok':True,'protocol':1,'bridge_enabled':not a.no_bridge})
   file=(ROOT/'dist'/unquote(path).lstrip('/')).resolve() if path!='/' else ROOT/'dist/index.html'
   if not file.is_relative_to((ROOT/'dist').resolve()) or not file.is_file():return self.reply({'error':'not_found'},404)
   data=file.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(file)[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  def do_POST(self):
   path=urlsplit(self.path).path
   if path not in ['/api/tap','/api/heartbeat']:return self.reply({'error':'not_found'},404)
   reader=self.headers.get('X-Reader-Id','');record=cfg['readers'].get(reader);auth=self.headers.get('Authorization','')
   if not record or not hmac.compare_digest(auth,'Bearer '+record['token']):return self.reply({'error':'unauthorized'},401)
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=2048:return self.reply({'error':'invalid_size'},400)
    data=json.loads(self.rfile.read(size))
    result=engine.tap(reader,data['uid'],data['event_id']) if path=='/api/tap' else {'ok':engine.heartbeat(reader)}
    return self.reply(result)
   except (ValueError,KeyError,TypeError,SeatError):return self.reply({'error':'invalid_event'},400)
 server=ThreadingHTTPServer((cfg.get('host','0.0.0.0'),cfg.get('port',8080)),Handler)
 print('Seat server ready on port',cfg.get('port',8080),'— select actual server mode in Connection settings.')
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:
  server.server_close()
  if bridge:bridge.disconnect()
if __name__=='__main__':main()
