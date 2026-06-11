# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid
import sqlalchemy

from database import database, create_tables, audit_logs
from mock_swarm import security_scan, call_model_real, calculate_cost, write_log

app = FastAPI(title="Talamanda AI Audit Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ── Request model ─────────────────────────────────────────────────────────────
class ProxyRequest(BaseModel):
    agent:  str    # Who is calling (e.g. "Marketing Agent", "Dashboard")
    model:  str    # Model string (e.g. "gpt-4o-mini", "claude-3-5-sonnet-20241022")
    prompt: str

# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event('startup')
async def startup():
    await database.connect()
    create_tables()

@app.on_event('shutdown')
async def shutdown():
    await database.disconnect()

# ── Core proxy endpoint ───────────────────────────────────────────────────────
@app.post('/agent/request')
async def handle_proxy_request(payload: ProxyRequest):
    req_id    = f"req_{uuid.uuid4().hex[:6]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    is_blocked, threat_type, processed_prompt = security_scan(payload.prompt)

    if is_blocked:
        log_entry = {
            'id': req_id, 'timestamp': timestamp, 'agent': payload.agent,
            'prompt': processed_prompt,
            'response': f"Blocked: {threat_type}",
            'model': payload.model, 'cost': '$0.000000',
            'input_tokens': 0, 'output_tokens': 0,
            'status': 'blocked', 'threat_type': threat_type,
        }
        await write_log(log_entry)
        return log_entry

    try:
        resp_text, in_tok, out_tok = await call_model_real(payload.model, payload.prompt)
        real_cost = calculate_cost(payload.model, in_tok, out_tok)
        log_entry = {
            'id': req_id, 'timestamp': timestamp, 'agent': payload.agent,
            'prompt': payload.prompt, 'response': resp_text,
            'model': payload.model, 'cost': f"${real_cost:.6f}",
            'input_tokens': in_tok, 'output_tokens': out_tok,
            'status': 'success', 'threat_type': None,
        }
    except Exception as e:
        log_entry = {
            'id': req_id, 'timestamp': timestamp, 'agent': payload.agent,
            'prompt': payload.prompt, 'response': f"Error: {str(e)}",
            'model': payload.model, 'cost': '$0.000000',
            'input_tokens': 0, 'output_tokens': 0,
            'status': 'error', 'threat_type': None,
        }

    await write_log(log_entry)
    return log_entry

# ── Audit log endpoints ───────────────────────────────────────────────────────
@app.get('/audit/logs')
async def get_all_logs(limit: int = 100):
    query = audit_logs.select().order_by(
        audit_logs.c.timestamp.desc()
    ).limit(limit)
    rows = await database.fetch_all(query)
    return [dict(r) for r in rows]

@app.get('/audit/logs/agent/{agent_name}')
async def get_logs_by_agent(agent_name: str):
    query = audit_logs.select().where(
        audit_logs.c.agent == agent_name
    ).order_by(audit_logs.c.timestamp.desc())
    rows = await database.fetch_all(query)
    return [dict(r) for r in rows]

@app.get('/audit/logs/status/{status}')
async def get_logs_by_status(status: str):
    """Filter by: success | blocked | error"""
    query = audit_logs.select().where(
        audit_logs.c.status == status
    ).order_by(audit_logs.c.timestamp.desc())
    rows = await database.fetch_all(query)
    return [dict(r) for r in rows]

# ── Dashboard stats endpoint — single call powers all KPI cards ───────────────
@app.get('/audit/stats')
async def get_stats():
    """
    Returns aggregated stats for the dashboard:
    total requests, blocked count, total cost, 
    per-model breakdown, per-agent breakdown.
    """
    all_rows = await database.fetch_all(audit_logs.select())
    rows = [dict(r) for r in all_rows]

    if not rows:
        return {
            'total_requests': 0,
            'total_blocked':  0,
            'total_errors':   0,
            'total_cost_usd': 0.0,
            'total_input_tokens':  0,
            'total_output_tokens': 0,
            'by_model':  {},
            'by_agent':  {},
            'by_status': {},
        }

    total_cost = sum(
        float(r['cost'].replace('$', ''))
        for r in rows if r['cost']
    )

    by_model = {}
    for r in rows:
        m = r['model']
        if m not in by_model:
            by_model[m] = {'requests': 0, 'cost': 0.0, 'input_tokens': 0, 'output_tokens': 0}
        by_model[m]['requests']      += 1
        by_model[m]['cost']          += float(r['cost'].replace('$', ''))
        by_model[m]['input_tokens']  += r['input_tokens']  or 0
        by_model[m]['output_tokens'] += r['output_tokens'] or 0

    by_agent = {}
    for r in rows:
        a = r['agent']
        if a not in by_agent:
            by_agent[a] = {'requests': 0, 'cost': 0.0}
        by_agent[a]['requests'] += 1
        by_agent[a]['cost']     += float(r['cost'].replace('$', ''))

    by_status = {}
    for r in rows:
        s = r['status']
        by_status[s] = by_status.get(s, 0) + 1

    return {
        'total_requests':      len(rows),
        'total_blocked':       by_status.get('blocked', 0),
        'total_errors':        by_status.get('error',   0),
        'total_cost_usd':      round(total_cost, 6),
        'total_input_tokens':  sum(r['input_tokens']  or 0 for r in rows),
        'total_output_tokens': sum(r['output_tokens'] or 0 for r in rows),
        'by_model':  by_model,
        'by_agent':  by_agent,
        'by_status': by_status,
    }

@app.get('/audit/threats')
async def get_threats():
    """Returns only blocked requests with threat classification."""
    query = audit_logs.select().where(
        audit_logs.c.status == 'blocked'
    ).order_by(audit_logs.c.timestamp.desc())
    rows = await database.fetch_all(query)
    return [dict(r) for r in rows]

@app.get('/health')
async def health():
    return {'status': 'ok', 'timestamp': datetime.now(timezone.utc).isoformat()}