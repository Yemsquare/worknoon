import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {ArrowUpRight, ArrowRight, ArrowLeft, ArrowLeftRight, Check, CheckCircle2, ChevronRight, Clock3, FileText, Headphones, LayoutDashboard, Loader2, LogOut, MessageSquare, Package, Plus, RefreshCw, Search, ShieldCheck, Sparkles, X, XCircle} from 'lucide-react';
import './styles.css';

const money = cents => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(cents/100);
const date = stamp => new Date(stamp).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'});
const reasons = {damaged:'Damaged item',incorrect:'Incorrect item',changed_mind:'Changed my mind',other:'Something else'};

async function api(path,{token,body,key,...options}={}) {
  const controller = new AbortController();
  const timer = setTimeout(()=>controller.abort(),28000);
  try {
    const res = await fetch('/api'+path,{...options,signal:controller.signal,headers:{...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:`Bearer ${token}`} : {}),...(key?{'Idempotency-Key':key}:{})},body:body?JSON.stringify(body):undefined});
    const data = await res.json();
    if(!res.ok) throw new Error(typeof data.detail==='string'?data.detail:'Please check your input and try again.');
    return data;
  } catch(e) {if(e.name==='AbortError') throw new Error('The request is taking longer than expected. Check request history before retrying.'); throw e;}
  finally {clearTimeout(timer);}
}

function Badge({status}) {return <span className={'badge '+status.toLowerCase()}>{status==='Approved'?<Check size={12}/>:status==='Denied'?<X size={12}/>:<Clock3 size={12}/>} {status==='Escalated'?'Needs review':status}</span>;}
function ErrorNote({children}) {return children?<div className="error" role="alert"><XCircle size={17}/>{children}</div>:null;}
function Empty({title,children}) {return <div className="empty"><Package size={28}/><h3>{title}</h3><p>{children}</p></div>;}

function App() {
  const [health,setHealth]=useState(null),[customers,setCustomers]=useState([]),[session,setSession]=useState(null);
  const [view,setView]=useState('request'),[area,setArea]=useState('customer'),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [password,setPassword]=useState(''),[policy,setPolicy]=useState(null),[booting,setBooting]=useState(true);
  async function loginCustomer(id) {
    setError('');setBusy(true);setSession(null);
    try{setSession(await api('/auth/customer',{method:'POST',body:{customer_id:id}}));setView('request');}
    catch(e){setError(e.message);}finally{setBusy(false);}
  }
  useEffect(()=>{let active=true;(async()=>{
    try{const [h,p]=await Promise.all([api('/health'),api('/policy')]);if(!active)return;setHealth(h);setPolicy(p);
      if(h.demo_mode){const c=await api('/demo/customers');if(!active)return;setCustomers(c);}
    }catch(e){if(active)setError('Could not connect to the API. Start the backend and refresh this page.');}
    finally{if(active)setBooting(false);}
  })();return()=>{active=false;};},[]);
  async function adminLogin(e){e.preventDefault();setBusy(true);setError('');try{setSession(await api('/auth/admin',{method:'POST',body:{password}}));setPassword('');setView('dashboard');}catch(e){setError(e.message);}finally{setBusy(false);}}
  function changeArea(next){setArea(next);setSession(null);setError('');setView(next==='customer'?'request':'dashboard');}
  const isAdmin=area==='support';
  return <div className="shell">
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="Refund Desk home"><span className="brand-icon"><ArrowLeftRight size={21}/></span><span>refund<span className="brand-light">desk</span><small>CARE, WITHOUT THE COMPLEXITY</small></span></a>
      <div className="workspace"><div className="store-icon">N</div><div><strong>Northstar Store</strong><small>Assessment workspace</small></div><span className="dot"/></div>
      <p className="nav-label">WORKSPACE</p>
      <nav aria-label="Main navigation">
        {!isAdmin?<><button className={view==='request'?'active':''} onClick={()=>setView('request')}><Plus size={18}/>New request</button><button className={view==='history'?'active':''} onClick={()=>setView('history')}><Clock3 size={18}/>Request history</button></>:<button className={view==='dashboard'?'active':''} onClick={()=>setView('dashboard')}><LayoutDashboard size={18}/>Support dashboard</button>}
        <button className={view==='policy'?'active':''} onClick={()=>setView('policy')}><FileText size={18}/>Refund policy</button>
      </nav>
      <div className="sidebar-bottom"><div className="trust-card"><ShieldCheck size={23}/><strong>Policy first. Always.</strong><p>Clear rules guide every decision. A person steps in when it matters.</p></div><span className="made-by">Built by Dev.Yemsquare <ArrowUpRight size={13}/></span></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumb">Workspace <ChevronRight size={13}/><strong>{isAdmin?'Support':'Customer care'}</strong></div><div className="area-switch" aria-label="Workspace view"><button className={!isAdmin?'selected':''} onClick={()=>changeArea('customer')}>Customer</button><button className={isAdmin?'selected':''} onClick={()=>changeArea('support')}>Support</button></div><span className="avatar">{session?.user.name?.split(' ').map(x=>x[0]).join('').slice(0,2)||'NS'}</span></header>
      <main>
        <div className="demo-banner"><span><span className="dot"/>{health?.ai_mode==='live'?'Live AI configured':'Demo workspace'}</span><p>{health?.ai_mode==='live'?'Live requests use OpenAI when policy checks allow. All orders remain synthetic.':'Synthetic orders · Local demo classifier · No real payments'}</p><span className="pill">ASSESSMENT</span></div>
        <ErrorNote>{error}</ErrorNote>
        {booting?<div className="empty"><Loader2 className="spin"/>Connecting to your workspace…</div>:view==='policy'?<Policy policy={policy}/>:!session?<section className="welcome"><div className="eyebrow">{isAdmin?'SUPPORT WORKSPACE':'A LITTLE HELP, RIGHT ON TIME'}</div><h1>{isAdmin?'Good decisions start here.':'Let’s make it right.'}</h1><p>{isAdmin?'Review requests, understand the policy, and take the next step.':'Something not quite right with your order? We’ll help you find a clear next step.'}</p><div className="login-card"><div className="section-icon">{isAdmin?<ShieldCheck/>:<Package/>}</div><h2>{isAdmin?'Sign in to support':'Choose a demo customer'}</h2><p>{isAdmin?'Use the support password configured for this local assessment.':'Explore 15 fictional customer profiles, each with their own order history.'}</p>{isAdmin?<form onSubmit={adminLogin}><label htmlFor="password">Support password</label><input id="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} required autoComplete="current-password"/><button className="primary" disabled={busy}>{busy?<Loader2 className="spin" size={16}/>:<ArrowRight size={16}/>}Enter support workspace</button>{health?.demo_mode&&<small className="helper">Default local demo password: <code>support-demo</code></small>}</form>:<><label htmlFor="customer">Customer profile</label><select id="customer" defaultValue="" disabled={busy||!customers.length} onChange={e=>loginCustomer(e.target.value)}><option value="" disabled>Select a customer to begin</option>{customers.map(c=><option key={c.id} value={c.id}>{c.name} · {c.id}</option>)}</select>{!health?.demo_mode&&<p>Demo customer sign-in is disabled. An identity provider must be integrated for customer access.</p>}<div className="safe-note"><ShieldCheck size={15}/>Fictional accounts only. No personal data.</div></>}</div></section>:<>
          <div className="session-row"><span>Signed in as <strong>{session.user.name}</strong></span><button className="text-button" onClick={()=>setSession(null)}><LogOut size={14}/>{isAdmin?'Sign out':'Switch customer'}</button></div>
          {isAdmin?<Dashboard token={session.token}/>:view==='history'?<History token={session.token}/>:<Customer token={session.token} name={session.user.name} onHistory={()=>setView('history')}/>}
        </>}
        <footer><span>Refund Desk <span className="footer-dot">·</span> Thoughtful support, clear outcomes.</span><span>Policy {policy?.version||'…'} <ShieldCheck size={13}/></span></footer>
      </main>
    </div>
  </div>;
}

function Customer({token,name,onHistory}) {
  const [orders,setOrders]=useState([]),[selected,setSelected]=useState(''),[reason,setReason]=useState('damaged'),[message,setMessage]=useState('');
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[loading,setLoading]=useState(true);
  const [requestKey,setRequestKey]=useState(()=>crypto.randomUUID());
  useEffect(()=>{api('/orders',{token}).then(setOrders).catch(e=>setError(e.message)).finally(()=>setLoading(false));},[token]);
  function edit(fn){fn();setRequestKey(crypto.randomUUID());}
  const order=orders.find(o=>o.id===selected);
  async function submit(e){e.preventDefault();setError('');setBusy(true);try{const r=await api('/requests',{token,method:'POST',key:requestKey,body:{order_id:selected,reason,message}});setResult(r);}catch(e){setError(e.message);}finally{setBusy(false);}}
  return <>
    <div className="page-heading"><div><div className="eyebrow">CUSTOMER CARE</div><h1>Let’s make it right, {name.split(' ')[0]}.</h1><p>Tell us what happened. We’ll take it from here.</p></div><span className="heading-icon"><Headphones size={29}/></span></div>
    {result?<div className="result-layout"><section className="card result-card"><div className={'result-icon '+result.status.toLowerCase()}>{result.status==='Approved'?<CheckCircle2 size={36}/>:result.status==='Denied'?<XCircle size={36}/>:<Clock3 size={36}/>}</div><Badge status={result.status}/><h2>{result.status==='Approved'?'Your refund request is approved.':result.status==='Denied'?'This order isn’t eligible.':'A person will take it from here.'}</h2><p>{result.explanation}</p><div className="receipt"><div><span>Request reference</span><strong>{result.id}</strong></div><div><span>Order</span><strong>{result.order_id}</strong></div><div><span>Requested amount</span><strong>{money(result.order.amount_cents)}</strong></div><div><span>Policy rule</span><strong>{result.rule_id}</strong></div></div><div className="safe-note"><ShieldCheck size={16}/>Assessment decision only. No money has been transferred.</div><button className="primary" onClick={onHistory}>View request history<ArrowRight size={17}/></button></section><HowItWorks/></div>:<div className="customer-grid"><form onSubmit={submit} className="card request-form"><div className="card-heading"><span className="section-number">01</span><div><h2>Choose your order</h2><p>Select the item you’d like help with.</p></div></div><ErrorNote>{error}</ErrorNote>{loading?<p className="helper">Loading your orders…</p>:<fieldset className="order-list" disabled={busy}><legend className="sr-only">Your orders</legend>{orders.map(o=><label key={o.id} className={'order-card '+(selected===o.id?'chosen':'')+(o.request_id?' unavailable':'')}><input type="radio" name="order" value={o.id} checked={selected===o.id} disabled={Boolean(o.request_id)} onChange={()=>edit(()=>setSelected(o.id))}/><span className="product-icon"><Package size={23}/></span><span className="order-info"><strong>{o.product}</strong><small>{o.id} <span>·</span> {date(o.purchased_at)}</small>{o.request_id?<span className="order-tag">Request already {o.request_status.toLowerCase()}</span>:o.final_sale?<span className="order-tag">Final sale</span>:o.refunded?<span className="order-tag">Previously refunded</span>:null}</span><strong className="price">{money(o.amount_cents)}</strong></label>)}</fieldset>}
      <div className="divider"/><div className="card-heading"><span className="section-number">02</span><div><h2>Tell us what happened</h2><p>A few details help us find the right resolution.</p></div></div>
      <label htmlFor="reason">Reason for your request</label><select id="reason" value={reason} disabled={busy} onChange={e=>edit(()=>setReason(e.target.value))}>{Object.entries(reasons).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select>
      <label htmlFor="message">What went wrong?</label><textarea id="message" placeholder="For example: My headphones arrived with a cracked ear cup. I’d like to request a refund." value={message} disabled={busy} onChange={e=>edit(()=>setMessage(e.target.value))} minLength={10} maxLength={2000} required rows={4}/><div className="field-help"><span>Please don’t include payment details or passwords.</span><span>{message.length}/2000</span></div>
      <div className="submit-row"><div><small>Requested refund</small><strong>{order?money(order.amount_cents):'—'}</strong></div><button className="primary" disabled={busy||!selected||message.trim().length<10}>{busy?<><Loader2 className="spin" size={17}/>Reviewing request…</>:<>Submit request<ArrowRight size={17}/></>}</button></div><p className="fine-print"><ShieldCheck size={13}/> Your request is checked against our refund policy.</p>
    </form><div><HowItWorks/><div className="soft-card"><Sparkles size={22}/><h3>Smart support.<br/>Human judgment.</h3><p>AI helps interpret your request. Clear policy rules determine the outcome. Anything uncertain goes to our support team.</p><span>Built with care <span>↗</span></span></div></div></div>}
  </>;
}

function HowItWorks(){return <aside className="card how-card"><div className="eyebrow">WHAT HAPPENS NEXT</div><h2>A clear path to resolution.</h2><div className="timeline"><div><span>1</span><section><strong>We check your order</strong><p>Order details and eligibility are verified securely.</p></section></div><div><span>2</span><section><strong>We review your request</strong><p>Your description is assessed against the refund policy.</p></section></div><div><span>3</span><section><strong>You get a clear answer</strong><p>Approved, denied, or sent to a person for review.</p></section></div></div><div className="policy-mini"><Clock3 size={17}/><div><strong>30-day refund window</strong><small>Final-sale items are excluded.</small></div></div></aside>;}

function Policy({policy}){return <><div className="page-heading"><div><div className="eyebrow">NO GUESSWORK</div><h1>Clear rules. Fair decisions.</h1><p>The policy behind every refund request.</p></div><ShieldCheck size={32}/></div><div className="policy-grid">{policy?.rules.map(rule=><article className="card policy-card" key={rule.id}><span className="rule-label">{rule.id}</span><h2>{rule.title}</h2><p>{rule.description}</p></article>)}</div><div className="policy-disclaimer"><ShieldCheck size={19}/><p>USD only. Full-order refunds only. Final sale, expired orders and previous refunds take precedence. Approvals are recorded decisions in this assessment; they do not initiate a payment. This sample policy is a product assumption, not legal guidance.</p></div></>;}

function History({token}){
  const [items,setItems]=useState([]),[error,setError]=useState(''),[busy,setBusy]=useState(true);
  async function load(){setBusy(true);setError('');try{setItems(await api('/requests',{token}));}catch(e){setError(e.message);}finally{setBusy(false);}}
  useEffect(()=>{load();},[token]);
  return <><div className="page-heading"><div><div className="eyebrow">YOUR REQUESTS</div><h1>Every update, in one place.</h1><p>Follow your requests from submission to resolution.</p></div><button className="secondary" disabled={busy} onClick={load}><RefreshCw size={15} className={busy?'spin':''}/>Refresh</button></div><ErrorNote>{error}</ErrorNote>{busy?<p className="helper">Loading request history…</p>:items.length?<div className="history-list">{items.map(item=><article className="card history-card" key={item.id}><div className="history-top"><div><small>{item.id}</small><h2>{item.order.product}</h2></div><Badge status={item.status}/></div><p>{item.explanation||'Your request is being assessed. Refresh for an update.'}</p><div className="history-bottom"><span>{item.order_id} · {date(item.created_at)}</span><strong>{money(item.order.amount_cents)}</strong></div></article>)}</div>:<Empty title="A clean slate">Your refund requests will appear here once you submit one.</Empty>}</>;
}

function Dashboard({token}){
  const [items,setItems]=useState([]),[filter,setFilter]=useState('All'),[query,setQuery]=useState(''),[selected,setSelected]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
  const [note,setNote]=useState(''),[saving,setSaving]=useState(false);
  async function load(){setError('');setLoading(true);try{setItems(await api('/admin/requests',{token}));}catch(e){setError(e.message);}finally{setLoading(false);}}
  useEffect(()=>{load();},[token]);
  async function review(decision){setSaving(true);setError('');try{const updated=await api(`/admin/requests/${selected.id}/review`,{token,method:'POST',body:{decision,note}});setSelected(updated);setItems(old=>old.map(i=>i.id===updated.id?updated:i));setNote('');}catch(e){setError(e.message);}finally{setSaving(false);}}
  const visible=items.filter(i=>(filter==='All'||i.status===filter)&&`${i.id} ${i.order_id} ${i.customer.name}`.toLowerCase().includes(query.toLowerCase()));
  return <><div className="page-heading"><div><div className="eyebrow">SUPPORT OVERVIEW</div><h1>A little judgment goes a long way.</h1><p>Understand the context. Make the next decision with confidence.</p></div><button className="secondary" onClick={load} disabled={loading}><RefreshCw size={15} className={loading?'spin':''}/>Refresh</button></div><ErrorNote>{error}</ErrorNote>
    <div className="stats">{[['Total requests','All',MessageSquare],['Approved','Approved',CheckCircle2],['Needs review','Escalated',Clock3],['Denied','Denied',XCircle]].map(([label,status,Icon])=><button className={'stat '+(filter===status?'stat-active':'')} key={status} onClick={()=>setFilter(status)}><span>{label}<Icon size={17}/></span><strong>{status==='All'?items.length:items.filter(i=>i.status===status).length}</strong><small>{status==='Escalated'?'Waiting for a human decision':status==='All'?'Across all demo customers':'Recorded policy outcomes'}</small></button>)}</div>
    <section className="card table-card"><div className="table-toolbar"><h2>Refund requests <span className="count">{visible.length}</span></h2><div className="search-field"><Search size={16}/><input aria-label="Search requests" placeholder="Search customer or reference…" value={query} onChange={e=>setQuery(e.target.value)}/></div></div><div className="filters" aria-label="Request status filter">{['All','Escalated','Approved','Denied'].map(status=><button key={status} className={filter===status?'selected':''} onClick={()=>setFilter(status)}>{status==='Escalated'?'Needs review':status}</button>)}</div>
    {loading?<p className="table-loading">Loading requests…</p>:visible.length?<div className="table-scroll"><table><thead><tr><th>Customer / request</th><th>Order</th><th>Amount</th><th>Outcome</th><th>Assessed by</th><th><span className="sr-only">Details</span></th></tr></thead><tbody>{visible.map(item=><tr key={item.id}><td><strong>{item.customer.name}</strong><small>{item.id}</small></td><td>{item.order.product}<small>{item.order_id}</small></td><td className="amount">{money(item.order.amount_cents)}</td><td><Badge status={item.status}/></td><td><span className="mode-label">{item.analysis.mode==='live'?'Live AI + policy':item.analysis.mode==='demo'?'Demo + policy':item.analysis.mode==='unavailable'?'AI unavailable':'Policy engine'}</span></td><td><button className="icon-button" aria-label={`View ${item.id}`} onClick={()=>{setSelected(item);setNote('');}}><ArrowUpRight size={18}/></button></td></tr>)}</tbody></table></div>:<Empty title={items.length?'No matching requests':'Your queue is clear'}>{items.length?'Try a different filter or search.':'Submit a request in the customer workspace to see it here.'}</Empty>}</section>
    {selected&&<section className="card detail-card" aria-label="Request details"><div className="detail-header"><div><div className="eyebrow">REQUEST DETAILS · {selected.id}</div><h2>{selected.customer.name} <Badge status={selected.status}/></h2></div><button className="icon-button" aria-label="Close request details" onClick={()=>setSelected(null)}><X size={20}/></button></div><div className="detail-grid"><div><label>Customer’s message</label><blockquote>{selected.message}</blockquote><div className="detail-meta"><span>Reason: <strong>{reasons[selected.declared_reason]}</strong></span><span>Amount: <strong>{money(selected.order.amount_cents)}</strong></span></div><label>Decision explanation</label><p>{selected.explanation}</p><div className="ai-note"><Sparkles size={16}/><div><strong>Classification summary · {selected.analysis.mode}</strong><p>{selected.analysis.summary}</p>{selected.analysis.category&&<small>{selected.analysis.category} · {Math.round(selected.analysis.confidence*100)}% model confidence (not calibrated)</small>}</div></div></div><div><label>Audit trail</label><ol className="audit-list">{selected.audit.map(a=><li key={a.id}><strong>{a.event.replaceAll('_',' ')}</strong><p>{a.note}</p><small>{a.actor} · {new Date(a.created_at).toLocaleString()}</small></li>)}</ol></div></div>{selected.status==='Escalated'&&<div className="review-form"><label htmlFor="review-note">Support decision note</label><textarea id="review-note" value={note} onChange={e=>setNote(e.target.value)} minLength={10} maxLength={500} rows={2} placeholder="Describe the evidence you checked and why this decision is appropriate."/><div className="review-actions"><small>Recorded in the audit trail. Hard policy exclusions still apply.</small><button className="secondary danger" disabled={saving||note.trim().length<10} onClick={()=>review('Denied')}>Deny request</button><button className="primary" disabled={saving||note.trim().length<10} onClick={()=>review('Approved')}>{saving?<Loader2 className="spin" size={16}/>:<Check size={16}/>}Approve request</button></div></div>}</section>}
  </>;
}

createRoot(document.getElementById('root')).render(<App/>);
