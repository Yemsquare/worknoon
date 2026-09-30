import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)
_ephemeral_secret = secrets.token_urlsafe(48)

def demo_enabled():
    return os.getenv('DEMO_MODE','true').lower() == 'true'

def secret():
    return os.getenv('AUTH_SECRET') or _ephemeral_secret

def issue(sub,role):
    data = base64.urlsafe_b64encode(json.dumps({'sub':sub,'role':role,'exp':int(time.time())+3600}).encode()).decode().rstrip('=')
    signature = hmac.new(secret().encode(),data.encode(),hashlib.sha256).hexdigest()
    return data+'.'+signature

def identity(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    try:
        if not credentials:
            raise ValueError()
        data,sig = credentials.credentials.split('.')
        expected = hmac.new(secret().encode(),data.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,expected):
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(data+'='*(-len(data)%4)))
        if payload['exp'] <= time.time() or payload['role'] not in ('customer','admin'):
            raise ValueError()
        return payload
    except (ValueError,KeyError,TypeError):
        raise HTTPException(401,'Session expired or invalid. Please sign in again.')

def admin(user=Depends(identity)):
    if user['role'] != 'admin':
        raise HTTPException(403,'Support access is required.')
    return user
