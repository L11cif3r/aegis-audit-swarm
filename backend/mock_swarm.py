# backend/mock_swarm.py
import os, re
import anthropic, openai
from google import genai
from dotenv import load_dotenv
from functools import partial
import asyncio

from database import database, audit_logs

load_dotenv()

# ── SDK clients (synchronous) ─────────────────────────────────────────────────
anthropic_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
openai_client    = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


# ── Pricing (per token, in USD) ───────────────────────────────────────────────
PRICE_PER_TOKEN = {
    'claude-3-5-sonnet-20241022': {'input': 0.000015,  'output': 0.000075},
    'gpt-4o-mini':                {'input': 0.00000015, 'output': 0.0000006},
    'gemini-2.5-flash':           {'input': 0.000000075,'output': 0.0000003},
    'gemini-2.5-pro':             {'input': 0.00000125, 'output': 0.000005}, # Add this line
}

# ── Security patterns ─────────────────────────────────────────────────────────
SECURITY_PATTERNS = [
    (r'ignore previous instructions',         'PROMPT_INJECTION'),
    (r'(jailbreak|DAN mode|do anything now)', 'PROMPT_INJECTION'),
    (r'sk-[a-zA-Z0-9]{20,}',                 'SECRET_API_KEY'),
    (r'AKIA[0-9A-Z]{16}',                    'SECRET_API_KEY'),
    (r'Bearer eyJ[a-zA-Z0-9._\-]+',          'SECRET_TOKEN'),
    (r'\b4[0-9]{12}(?:[0-9]{3})?\b',         'CREDIT_CARD'),
    (r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b',      'PII_SSN'),
]

def security_scan(prompt: str) -> tuple[bool, str, str]:
    redacted = prompt
    for pattern, threat_type in SECURITY_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            redacted = re.sub(pattern, '[REDACTED]', redacted, flags=re.IGNORECASE)
            return True, threat_type, redacted
    return False, '', redacted

# ── Model router — maps user-supplied model string to actual API model ─────────
def resolve_model(requested: str) -> tuple[str, str]:
    """Returns (provider, canonical_model_name)"""
    r = requested.lower()
    if 'claude' in r:
        # Always use the exact model string the user passed if it's valid,
        # otherwise fall back to sonnet
        valid = [k for k in PRICE_PER_TOKEN if 'claude' in k]
        canon = requested if requested in valid else 'claude-3-5-sonnet-20241022'
        return 'anthropic', canon
    elif 'gpt' in r or 'openai' in r:
        valid = [k for k in PRICE_PER_TOKEN if 'gpt' in k]
        canon = requested if requested in valid else 'gpt-4o-mini'
        return 'openai', canon
    else:
        return 'google', 'gemini-1.5-flash'

# ── Real LLM calls — run sync SDKs in thread pool to not block event loop ─────
async def call_model_real(model: str, prompt: str) -> tuple[str, int, int]:
    if 'claude' in model:
        r = anthropic_client.messages.create(
            model='claude-3-5-sonnet-20241022', max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return r.content[0].text, r.usage.input_tokens, r.usage.output_tokens
    elif 'gpt' in model:
        r = openai_client.chat.completions.create(
            model='gpt-4o-mini', max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return r.choices[0].message.content, r.usage.prompt_tokens, r.usage.completion_tokens
    else:
        # Default fallback to Gemini
        client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))
        r = client.models.generate_content(
            model=model,  # Dynamic model routing
            contents=prompt,
        )
        in_tok = r.usage_metadata.prompt_token_count if r.usage_metadata else 0
        out_tok = r.usage_metadata.candidates_token_count if r.usage_metadata else 0
        return r.text, in_tok, out_tok

# ── Cost calculation ──────────────────────────────────────────────────────────
def calculate_cost(model: str, input_tok: int, output_tok: int) -> float:
    _, canon = resolve_model(model)
    p = PRICE_PER_TOKEN.get(canon, {'input': 0.000003, 'output': 0.000015})
    return round(input_tok * p['input'] + output_tok * p['output'], 6)

# ── DB write ──────────────────────────────────────────────────────────────────
async def write_log(log_entry: dict):
    await database.execute(audit_logs.insert().values(**log_entry))