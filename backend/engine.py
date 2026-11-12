"""Atomic seat transitions. Raw card UIDs never leave this process or enter SQLite."""
import sqlite3,threading,time,hmac,hashlib,re,json
class SeatError(Exception): pass
class Engine:
 def __init__(self,path,seats,readers,secret):
  self.ids={s['id'] for s in seats}; self.readers=readers; self.secret=secret.encode();self.lock=threading.RLock();self.online={}
  if not readers or not all(v in self.ids for v in readers.values()): raise ValueError('Reader mapping must contain existing seat IDs')
  if len(set(readers.values()))!=len(readers): raise ValueError('One reader per seat required')
  self.db=sqlite3.connect(path,check_same_thread=False,isolation_level=None)
  self.db.executescript('PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS seats(id TEXT PRIMARY KEY,owner TEXT UNIQUE,since REAL); CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY,reader TEXT,seat_id TEXT,action TEXT,at REAL,result TEXT,card_hash TEXT);')
  self.db.executemany('INSERT OR IGNORE INTO seats(id) VALUES(?)',[(i,) for i in self.ids])
 def heartbeat(self,reader):
  if reader not in self.readers:raise SeatError('unknown_reader')
  with self.lock:self.online[reader]=time.time()
  return True
 def tap(self,reader,uid,event_id):
  if reader not in self.readers:raise SeatError('unknown_reader')
  if not isinstance(uid,str) or not re.fullmatch(r'(?:[A-Fa-f0-9]{8}|[A-Fa-f0-9]{14}|[A-Fa-f0-9]{20})',uid):raise SeatError('invalid_uid')
  if not isinstance(event_id,str) or not re.fullmatch(r'[A-Za-z0-9:_-]{1,100}',event_id):raise SeatError('invalid_event_id')
  card=hmac.new(self.secret,uid.upper().encode(),hashlib.sha256).hexdigest();seat=self.readers[reader];now=time.time()
  with self.lock:
   self.db.execute('BEGIN IMMEDIATE')
   try:
    existing=self.db.execute('SELECT result,reader,card_hash FROM events WHERE event_id=?',(event_id,)).fetchone()
    if existing:
     if existing[1:]!=(reader,card):raise SeatError('event_id_conflict')
     self.db.execute('COMMIT');return json.loads(existing[0])
    owner=self.db.execute('SELECT owner FROM seats WHERE id=?',(seat,)).fetchone()[0]
    other=self.db.execute('SELECT id FROM seats WHERE owner=? AND id<>?',(card,seat)).fetchone()
    # Guard quick duplicate scans even if a malfunctioning client creates a fresh event ID.
    last=self.db.execute('SELECT at FROM events WHERE reader=? AND card_hash=? ORDER BY at DESC LIMIT 1',(reader,card)).fetchone()
    if last and now-last[0]<2:action='debounced'
    elif owner and owner!=card:action='seat_in_use'
    elif other:action='already_seated'
    elif owner:
     self.db.execute('UPDATE seats SET owner=NULL,since=NULL WHERE id=?',(seat,));action='check_out'
    else:
     self.db.execute('UPDATE seats SET owner=?,since=? WHERE id=?',(card,now,seat));action='check_in'
    result={'seat_id':seat,'action':action,'at':now}
    self.db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)',(event_id,reader,seat,action,now,json.dumps(result),card))
    self.db.execute('COMMIT');self.online[reader]=now;return result
   except Exception:self.db.execute('ROLLBACK');raise
 def snapshot(self):
  now=time.time()
  with self.lock:
   mapping={s:r for r,s in self.readers.items()};rows=self.db.execute('SELECT id,owner,since FROM seats ORDER BY id').fetchall()
   seats=[]
   for sid,owner,since in rows:
    reader=mapping.get(sid);online=bool(reader and now-self.online.get(reader,0)<15);state='occupied' if owner else 'available'
    seats.append({'id':sid,'status':state if online else 'unknown','last_state':state if reader else None,'online':online,'since':since})
   events=[{'seat_id':s,'action':a,'at':t} for s,a,t in self.db.execute("SELECT seat_id,action,at FROM events WHERE action IN ('check_in','check_out','seat_in_use','already_seated') ORDER BY at DESC LIMIT 12")]
   return {'protocol':1,'seats':seats,'events':events,'at':now}
