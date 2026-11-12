import unittest,tempfile,sys,time,threading,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from engine import Engine,SeatError
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=self.tmp.name+'/test.db';self.seats=[{'id':'B1_001'},{'id':'B1_002'},{'id':'B1_003'}];self.e=Engine(self.path,self.seats,{'r1':'B1_001','r2':'B1_002'},'test-secret')
 def tearDown(self):self.e.db.close();self.tmp.cleanup()
 def tap(self,r='r1',u='AABBCCDD',id='e1'):return self.e.tap(r,u,id)['action']
 def expire_debounce(self):self.e.db.execute('UPDATE events SET at=at-3')
 def test_check_in_out_and_duplicate(self):
  self.assertEqual(self.tap(),'check_in');self.assertEqual(self.tap(),'check_in');self.assertEqual(self.e.snapshot()['seats'][0]['status'],'occupied');self.expire_debounce();self.assertEqual(self.tap(id='e2'),'check_out')
 def test_debounce(self):self.tap();self.assertEqual(self.tap(id='e2'),'debounced');self.assertEqual(self.e.snapshot()['seats'][0]['last_state'],'occupied')
 def test_other_card_and_double_booking(self):self.tap();self.assertEqual(self.tap(u='11223344',id='e2'),'seat_in_use');self.assertEqual(self.tap(r='r2',id='e3'),'already_seated')
 def test_unknown_and_stale(self):
  self.assertTrue(all(s['status']=='unknown' for s in self.e.snapshot()['seats']));self.tap();self.e.online['r1']=time.time()-20;s=self.e.snapshot()['seats'][0];self.assertEqual(s['status'],'unknown');self.assertEqual(s['last_state'],'occupied')
 def test_restart_persistence(self):
  self.tap();self.e.db.close();self.e=Engine(self.path,self.seats,{'r1':'B1_001'},'test-secret');self.e.heartbeat('r1');self.assertEqual(self.e.snapshot()['seats'][0]['status'],'occupied');self.assertEqual(self.tap(),'check_in')
 def test_validation_privacy(self):
  for args in [('bad','AABBCCDD','id'),('r1','<script>','id'),('r1','AABBCCDD','')]:
   with self.assertRaises(SeatError):self.e.tap(*args)
  self.tap();self.assertNotIn('AABBCCDD',json.dumps(self.e.snapshot()));self.assertNotIn('AABBCCDD',str(list(self.e.db.execute('SELECT * FROM events'))))
 def test_event_conflict(self):
  self.tap()
  with self.assertRaises(SeatError):self.tap(u='11223344')
 def test_concurrent_single_owner(self):
  result=[];threads=[threading.Thread(target=lambda r=r:result.append(self.tap(r=r,id=r))) for r in ['r1','r2']]
  for t in threads:t.start()
  for t in threads:t.join()
  self.assertCountEqual(result,['check_in','already_seated'])
 def test_map_ids(self):
  seats=json.loads((Path(__file__).resolve().parents[1]/'dist/seats.json').read_text())['seats'];self.assertEqual(len(seats),83);self.assertEqual(len({s['id'] for s in seats}),83);self.assertEqual(sum(s['kind']=='study' for s in seats),82)
if __name__=='__main__':unittest.main()
