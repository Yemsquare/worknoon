"""Exercise the actual Nginx -> container API -> SQLite flow after compose up."""
import json
import urllib.request
import uuid

BASE='http://localhost:8080/api'
def call(path,data=None,token=None):
    headers={'Content-Type':'application/json','Idempotency-Key':str(uuid.uuid4())}
    if token:
        headers['Authorization']='Bearer '+token
    req=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data else None,headers=headers)
    with urllib.request.urlopen(req,timeout=30) as response:
        return json.load(response)

assert call('/health')['status']=='ok'
assert len(call('/demo/customers'))==15
customer=call('/auth/customer',{'customer_id':'CUS-001'})['token']
assert len(call('/orders',token=customer))==2
approved=call('/requests',{'order_id':'ORD-1001','reason':'damaged','message':'The headphones arrived cracked and damaged.'},customer)
assert approved['status']=='Approved'
denied=call('/requests',{'order_id':'ORD-1002','reason':'damaged','message':'The sweater was damaged on arrival.'},customer)
assert denied['status']=='Denied'
noah=call('/auth/customer',{'customer_id':'CUS-002'})['token']
escalated=call('/requests',{'order_id':'ORD-1004','reason':'damaged','message':'The monitor arrived with a cracked screen.'},noah)
assert escalated['status']=='Escalated'
admin=call('/auth/admin',{'password':'support-demo'})['token']
reviewed=call('/admin/requests/'+escalated['id']+'/review',{'decision':'Approved','note':'Confirmed delivery and damage evidence for this assessment.'},admin)
assert reviewed['status']=='Approved'
assert len(reviewed['audit'])==3
print('Compose smoke passed: health, seed, ownership, approve, deny, escalate, support review and audit.')
