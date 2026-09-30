"""Deterministic policy. Model output is advisory, never executable authority."""
from datetime import date
import re

VERSION = '2026-09-v1'
RULES = [
    {'id':'P01','title':'Final sale is final','description':'Final-sale items cannot be refunded.'},
    {'id':'P02','title':'30-day window','description':'Requests must be made within 30 calendar days of purchase (day 30 included, UTC).'},
    {'id':'P03','title':'One refund per order','description':'Already-refunded orders are ineligible. One request per order in this assessment.'},
    {'id':'P04','title':'Human review above $500','description':'Refunds over $500 USD require an explicit support decision.'},
    {'id':'P05','title':'Damage or wrong item','description':'Eligible damaged or incorrect items qualify. Conflicting claims go to support.'},
    {'id':'P06','title':'Uncertainty needs a person','description':'Suspicious input, unclear claims, model failures and changed-mind requests go to support.'},
]

def hard_denial(order, today=None):
    age = ((today or date.today()) - date.fromisoformat(order['purchased_at'])).days
    if order['final_sale']:
        return 'P01', 'This item was marked final sale and is not eligible for a refund.'
    if age > 30:
        return 'P02', f'This order is {age} days old, outside the 30-day refund window.'
    if order['refunded']:
        return 'P03', 'This order has already been refunded.'
    return None

def suspicious(text):
    # Defense in depth only. Structural separation and policy enforcement are the boundary.
    patterns = [r'ignore.{0,40}(instruction|policy|rule)',r'(system|developer)\s*(prompt|message|:)',
                r'\b(bypass|override|jailbreak)\b',r'pretend.{0,25}(admin|manager)',
                r'reveal.{0,30}(secret|key|prompt)',r'<\s*/?\s*(system|script)']
    return any(re.search(p,text,re.I|re.S) for p in patterns)

def precheck(order, message, today=None):
    denied = hard_denial(order, today)
    if denied:
        return 'Denied', *denied
    if date.fromisoformat(order['purchased_at']) > (today or date.today()):
        return 'Escalated','P06','The order date is inconsistent. Support must verify it.'
    if suspicious(message):
        return 'Escalated','P06','The request includes instructions that conflict with the refund workflow. Support will review it.'
    if order['amount_cents'] > 50000:
        return 'Escalated','P04','Refunds above $500 require human review.'
    return None

def decide(order, message, declared_reason, analysis, today=None):
    initial = precheck(order,message,today)
    if initial:
        return initial
    if analysis['mode'] == 'unavailable':
        return 'Escalated','P06','The AI service could not assess this request. It has been safely sent to support.'
    if analysis['suspicious'] or analysis['confidence'] < .85:
        return 'Escalated','P06','The request needs clarification or additional verification by support.'
    if analysis['category'] != declared_reason:
        return 'Escalated','P06','The selected reason and request description do not agree. Support will clarify the request.'
    if analysis['category'] in ('damaged','incorrect'):
        return 'Approved','P05','Your request meets the refund policy for a damaged or incorrect item.'
    return 'Escalated','P06','This request needs a support decision under the refund policy.'
