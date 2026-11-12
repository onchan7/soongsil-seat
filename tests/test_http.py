import unittest,tempfile,subprocess,sys,json,socket,time,urllib.request,urllib.error,secrets,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class HttpTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();root=Path(cls.tmp.name);shutil.copytree(ROOT/'backend',root/'backend');shutil.copytree(ROOT/'dist',root/'dist')
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  cls.base=f'http://127.0.0.1:{port}';cls.token=secrets.token_hex(16)
  config={'host':'127.0.0.1','port':port,'secret':secrets.token_hex(32),'readers':{'r1':{'seat_id':'B1_001','token':cls.token}},'allowed_origins':['https://example.github.io']}
  (root/'config.local.json').write_text(json.dumps(config));cls.proc=subprocess.Popen([sys.executable,str(root/'backend/server.py'),'--no-bridge'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for i in range(50):
   try:urllib.request.urlopen(cls.base+'/api/health',timeout=1);break
   except OSError:time.sleep(.05)
  else:raise RuntimeError('server failed')
 @classmethod
 def tearDownClass(cls):cls.proc.terminate();cls.proc.wait(timeout=5);cls.tmp.cleanup()
 def test_api_and_auth(self):
  req=urllib.request.Request(self.base+'/api/tap',data=json.dumps({'uid':'AABBCCDD','event_id':'http-1'}).encode(),headers={'Content-Type':'application/json','X-Reader-Id':'r1'},method='POST')
  with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
  self.assertEqual(e.exception.code,401);req.add_header('Authorization','Bearer '+self.token)
  result=json.load(urllib.request.urlopen(req));self.assertEqual(result['action'],'check_in')
  result2=json.load(urllib.request.urlopen(req));self.assertEqual(result,result2)
  req=urllib.request.Request(self.base+'/api/seats',headers={'Origin':'https://example.github.io'})
  with urllib.request.urlopen(req) as r:
   self.assertEqual(r.headers['Access-Control-Allow-Origin'],'https://example.github.io');data=json.load(r)
  self.assertEqual(next(s for s in data['seats'] if s['id']=='B1_001')['status'],'occupied');self.assertNotIn('AABBCCDD',json.dumps(data));self.assertEqual(len(data['seats']),83)
 def test_static_and_path_protection(self):
  with urllib.request.urlopen(self.base+'/') as r:self.assertIn('숭실 Seat',r.read().decode())
  for path in ['/config.local.json','/../config.local.json','/%2e%2e/config.local.json']:
   with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(self.base+path)
   self.assertEqual(e.exception.code,404)
if __name__=='__main__':unittest.main()
