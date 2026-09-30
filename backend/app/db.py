import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connect():
    path = Path(os.getenv('DB_PATH','./data/refunds.sqlite3'))
    path.parent.mkdir(parents=True,exist_ok=True)
    conn = sqlite3.connect(path,timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def initialize():
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS customers(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,customer_id TEXT NOT NULL REFERENCES customers(id),
          product TEXT NOT NULL,amount_cents INTEGER NOT NULL CHECK(amount_cents>0), purchased_at TEXT NOT NULL,
          final_sale INTEGER NOT NULL DEFAULT 0,refunded INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,order_id TEXT UNIQUE NOT NULL REFERENCES orders(id),
          customer_id TEXT NOT NULL REFERENCES customers(id),message TEXT NOT NULL,declared_reason TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('Processing','Approved','Denied','Escalated')),
          rule_id TEXT,explanation TEXT,analysis TEXT NOT NULL DEFAULT '{}',policy_version TEXT NOT NULL,
          created_at TEXT NOT NULL,updated_at TEXT NOT NULL,idempotency_key TEXT NOT NULL,
          fingerprint TEXT NOT NULL,UNIQUE(customer_id,idempotency_key));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,request_id TEXT NOT NULL REFERENCES requests(id),
          actor TEXT NOT NULL,event TEXT NOT NULL,note TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS requests_created ON requests(created_at DESC);
        ''')
        # Single-process assessment recovery. Do not run multiple API workers with this recovery strategy.
        pending = db.execute("SELECT id FROM requests WHERE status='Processing'").fetchall()
        for row in pending:
            db.execute("UPDATE requests SET status='Escalated',rule_id='P06',explanation=?,updated_at=? WHERE id=?",
                       ('Assessment was interrupted. Support must review this request.',now(),row['id']))
            audit(db,row['id'],'system','recovery','Interrupted request sent to human review.')
        if db.execute('SELECT count(*) FROM customers').fetchone()[0]:
            return
        names = ['Amara Cole','Noah Reed','Maya Chen','Ethan Blake','Zara Quinn','Leo Hayes','Ava Brooks','Owen Lane',
                 'Isla Park','Theo Hart','Nia James','Luca Wells','Ada Stone','Finn Bell','Mila Rivers']
        products = [('Studio headphones',12900,5,0,0),('Merino knit sweater',8900,8,1,0),
                    ('Mechanical keyboard',15900,45,0,0),('4K studio monitor',64900,6,0,0),
                    ('Ceramic table lamp',7800,9,0,0),('Travel backpack',11500,4,0,0),
                    ('Espresso machine',50000,7,0,0),('Desk organiser',3400,3,0,1)]
        today = datetime.now(timezone.utc).date()
        for i,name in enumerate(names):
            cid = f'CUS-{i+1:03}'
            db.execute('INSERT INTO customers VALUES (?,?,?)',(cid,name,f'customer{i+1}@example.test'))
            for j in range(2):
                product,cents,days,final,refunded = products[(i*2+j)%len(products)]
                db.execute('INSERT INTO orders VALUES (?,?,?,?,?,?,?)',
                           (f'ORD-{1001+i*2+j}',cid,product,cents,(today-timedelta(days=days)).isoformat(),final,refunded))

def audit(db,request_id,actor,event,note):
    db.execute('INSERT INTO audit(request_id,actor,event,note,created_at) VALUES (?,?,?,?,?)',
               (request_id,actor,event,note,now()))

def request_record(db,row,admin=False):
    item = dict(row)
    for key in ['fingerprint','idempotency_key']:
        item.pop(key,None)
    item['analysis'] = json.loads(item['analysis'])
    item['order'] = dict(db.execute('SELECT * FROM orders WHERE id=?',(item['order_id'],)).fetchone())
    if admin:
        item['customer'] = dict(db.execute('SELECT * FROM customers WHERE id=?',(item['customer_id'],)).fetchone())
        item['audit'] = [dict(a) for a in db.execute('SELECT * FROM audit WHERE request_id=? ORDER BY id',(item['id'],))]
    else:
        item['analysis'] = {'mode':item['analysis'].get('mode','not_needed')}
    return item
