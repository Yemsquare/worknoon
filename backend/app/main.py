import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse
from . import ai, auth, db, policy

@asynccontextmanager
async def lifespan(app):
    if os.getenv('AI_MODE','demo') not in ('demo','live'):
        raise RuntimeError('AI_MODE must be demo or live')
    if not auth.demo_enabled():
        if len(os.getenv('AUTH_SECRET','')) < 32 or len(os.getenv('ADMIN_PASSWORD','')) < 16:
            raise RuntimeError('With DEMO_MODE=false, configure AUTH_SECRET (32+ chars) and ADMIN_PASSWORD (16+ chars). Customer identity integration is required for production.')
    db.initialize()
    yield

app = FastAPI(title='Refund Desk API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('ALLOWED_ORIGINS','http://localhost:8080,http://localhost:5173').split(','),
                   allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type','Idempotency-Key'])
_buckets = defaultdict(deque)
_rate_lock = threading.Lock()

def rate_limit(key,limit=30,period=60):
    current = time.monotonic()
    with _rate_lock:
        # Bound memory for this single-process local assessment.
        if len(_buckets)>10000:
            for k in list(_buckets):
                if not _buckets[k] or _buckets[k][-1] < current-period:
                    del _buckets[k]
        bucket = _buckets[key]
        while bucket and bucket[0] < current-period:
            bucket.popleft()
        if len(bucket)>=limit:
            raise HTTPException(429,'Too many requests. Try again in a minute.',headers={'Retry-After':'60'})
        bucket.append(current)

@app.middleware('http')
async def security_headers(request: Request,call_next):
    request_id = str(uuid.uuid4())
    # Count actual bytes as well as Content-Length; do not trust client metadata.
    if request.method == 'POST':
        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 16384:
                return JSONResponse({'detail':'Request body too large.'},status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    response = await call_next(request)
    response.headers.update({'X-Content-Type-Options':'nosniff','Cache-Control':'no-store',
                             'X-Frame-Options':'DENY','X-Request-ID':request_id,'Referrer-Policy':'no-referrer'})
    return response

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid',str_strip_whitespace=True)

class CustomerLogin(StrictModel):
    customer_id: str = Field(pattern=r'^CUS-\d{3}$')

class AdminLogin(StrictModel):
    password: str = Field(min_length=1,max_length=200)

class RefundInput(StrictModel):
    order_id: str = Field(pattern=r'^ORD-\d{4}$')
    reason: Literal['damaged','incorrect','changed_mind','other']
    message: str = Field(min_length=10,max_length=2000)

class ReviewInput(StrictModel):
    decision: Literal['Approved','Denied']
    note: str = Field(min_length=10,max_length=500)

@app.get('/api/health')
def health():
    with db.connect() as conn:
        conn.execute('SELECT 1')
    return {'status':'ok','ai_mode':os.getenv('AI_MODE','demo'),'demo_mode':auth.demo_enabled(),
            'policy_version':policy.VERSION,'live_key_configured':bool(os.getenv('OPENAI_API_KEY'))}

@app.get('/api/policy')
def get_policy():
    return {'version':policy.VERSION,'currency':'USD','window_days':30,'rules':policy.RULES}

@app.get('/api/demo/customers')
def customers():
    if not auth.demo_enabled():
        raise HTTPException(404,'Demo sign-in is disabled.')
    with db.connect() as conn:
        return [dict(r) for r in conn.execute('SELECT id,name FROM customers ORDER BY id')]

@app.post('/api/auth/customer')
def customer_login(data: CustomerLogin,request: Request):
    if not auth.demo_enabled():
        raise HTTPException(403,'Demo sign-in is disabled. Integrate your identity provider before production use.')
    rate_limit('login:'+request.client.host,20)
    with db.connect() as conn:
        row = conn.execute('SELECT * FROM customers WHERE id=?',(data.customer_id,)).fetchone()
    if not row:
        raise HTTPException(404,'Customer not found.')
    return {'token':auth.issue(row['id'],'customer'),'user':dict(row),'role':'customer'}

@app.post('/api/auth/admin')
def admin_login(data: AdminLogin,request: Request):
    rate_limit('admin-login:'+request.client.host,10)
    expected = os.getenv('ADMIN_PASSWORD') or ('support-demo' if auth.demo_enabled() else '')
    if not expected or not hmac.compare_digest(data.password.encode(),expected.encode()):
        raise HTTPException(401,'Incorrect support password.')
    return {'token':auth.issue('support','admin'),'user':{'name':'Support team'},'role':'admin'}

@app.get('/api/orders')
def orders(user=Depends(auth.identity)):
    if user['role'] != 'customer':
        raise HTTPException(403,'Use a customer session to view orders.')
    with db.connect() as conn:
        return [dict(row) for row in conn.execute('SELECT o.*,r.id AS request_id,r.status AS request_status FROM orders o LEFT JOIN requests r ON o.id=r.order_id WHERE o.customer_id=? ORDER BY o.id',(user['sub'],))]

@app.get('/api/requests')
def requests_list(user=Depends(auth.identity)):
    with db.connect() as conn:
        rows = conn.execute('SELECT * FROM requests WHERE customer_id=? ORDER BY created_at DESC',(user['sub'],)).fetchall()
        return [db.request_record(conn,r) for r in rows]

@app.post('/api/requests',status_code=201)
def submit(data: RefundInput,user=Depends(auth.identity),idempotency_key: str = Header(min_length=8,max_length=100)):
    if user['role'] != 'customer':
        raise HTTPException(403,'Use a customer session to request a refund.')
    rate_limit('refund:'+user['sub'],10)
    fingerprint = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
    rid = 'RF-'+uuid.uuid4().hex[:12].upper()
    with db.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        prior = conn.execute('SELECT * FROM requests WHERE customer_id=? AND idempotency_key=?',(user['sub'],idempotency_key)).fetchone()
        if prior:
            if prior['fingerprint'] != fingerprint:
                raise HTTPException(409,'This request key was already used for different input.')
            if prior['status']=='Processing':
                raise HTTPException(409,'This request is still processing. Check your request history.')
            return db.request_record(conn,prior)
        row = conn.execute('SELECT * FROM orders WHERE id=? AND customer_id=?',(data.order_id,user['sub'])).fetchone()
        if not row:
            raise HTTPException(404,'Order not found.')
        order = dict(row)
        if conn.execute('SELECT id FROM requests WHERE order_id=?',(order['id'],)).fetchone():
            raise HTTPException(409,'This order already has a refund request. Check your request history.')
        stamp = db.now()
        conn.execute('INSERT INTO requests(id,order_id,customer_id,message,declared_reason,status,policy_version,created_at,updated_at,idempotency_key,fingerprint) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                     (rid,order['id'],user['sub'],data.message,data.reason,'Processing',policy.VERSION,stamp,stamp,idempotency_key,fingerprint))
        db.audit(conn,rid,user['sub'],'submitted','Customer submitted a full-order refund request.')
    # Network call is outside the write transaction. The unique order reservation prevents races.
    today = datetime.now(timezone.utc).date()
    precheck = policy.precheck(order,data.message,today)
    analysis = {'mode':'not_needed','summary':'Deterministic policy check resolved the request.','model':None}
    if not precheck:
        analysis = ai.classify(data.message)
    outcome,rule,explanation = precheck or policy.decide(order,data.message,data.reason,analysis,today)
    with db.connect() as conn:
        conn.execute('UPDATE requests SET status=?,rule_id=?,explanation=?,analysis=?,updated_at=? WHERE id=?',
                     (outcome,rule,explanation,json.dumps(analysis),db.now(),rid))
        db.audit(conn,rid,'policy-engine','decision',f'{outcome} · {rule} · AI mode: {analysis["mode"]}. {explanation}')
        return db.request_record(conn,conn.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone())

@app.get('/api/admin/requests')
def admin_requests(status: Literal['All','Approved','Denied','Escalated','Processing']='All',user=Depends(auth.admin)):
    with db.connect() as conn:
        rows = conn.execute('SELECT * FROM requests WHERE (?=\'All\' OR status=?) ORDER BY created_at DESC LIMIT 500',(status,status)).fetchall()
        return [db.request_record(conn,r,admin=True) for r in rows]

@app.post('/api/admin/requests/{request_id}/review')
def review(request_id: str,data: ReviewInput,user=Depends(auth.admin)):
    with db.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM requests WHERE id=?',(request_id,)).fetchone()
        if not row:
            raise HTTPException(404,'Request not found.')
        if row['status'] != 'Escalated':
            raise HTTPException(409,'Only escalated requests can be reviewed.')
        order = dict(conn.execute('SELECT * FROM orders WHERE id=?',(row['order_id'],)).fetchone())
        denied = policy.hard_denial(order,datetime.now(timezone.utc).date())
        if data.decision == 'Approved' and denied:
            raise HTTPException(409,f'Approval blocked by {denied[0]}: {denied[1]}')
        if data.decision == 'Approved' and order['purchased_at'] > datetime.now(timezone.utc).date().isoformat():
            raise HTTPException(409,'Correct the inconsistent order date before approving.')
        explanation = f'Support reviewed this request and {"approved" if data.decision=="Approved" else "denied"} it. {data.note}'
        conn.execute('UPDATE requests SET status=?,explanation=?,updated_at=? WHERE id=?',(data.decision,explanation,db.now(),request_id))
        db.audit(conn,request_id,user['sub'],'human_review',f'{data.decision}: {data.note}')
        return db.request_record(conn,conn.execute('SELECT * FROM requests WHERE id=?',(request_id,)).fetchone(),admin=True)
