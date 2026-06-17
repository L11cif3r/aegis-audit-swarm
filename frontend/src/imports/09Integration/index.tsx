import { useMemo, useState } from 'react';
import { Copy, Check, Plug, KeyRound, ArrowRight, Info } from 'lucide-react';
import { API_BASE } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { PageHeader, Panel, SectionTitle } from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';

function useCopy() {
  const [copied, setCopied] = useState<string | null>(null);
  const copy = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
      setTimeout(() => setCopied((c) => (c === id ? null : c)), 1500);
    } catch {
      /* clipboard blocked */
    }
  };
  return { copied, copy };
}

function CodeBlock({ id, code, copied, onCopy }: {
  id: string; code: string; copied: string | null; onCopy: (id: string, text: string) => void;
}) {
  return (
    <div className="relative group">
      <pre className="overflow-x-auto rounded-xl border border-hairline bg-surface2/60 p-4 text-[12px] leading-relaxed text-ink font-mono whitespace-pre">
        {code}
      </pre>
      <button
        onClick={() => onCopy(id, code)}
        data-cursor="hover"
        className="absolute top-2.5 right-2.5 inline-flex items-center gap-1.5 rounded-lg border border-hairline bg-surface px-2.5 py-1.5 text-[11px] font-medium text-soft hover:text-ink transition-colors"
      >
        {copied === id ? <Check size={13} /> : <Copy size={13} />}
        {copied === id ? 'Copied' : 'Copy'}
      </button>
    </div>
  );
}

const TABS = [
  { id: 'javascript', label: 'JavaScript' },
  { id: 'python', label: 'Python' },
  { id: 'env', label: '.env' },
  { id: 'curl', label: 'curl' },
  { id: 'app', label: 'No-code app' },
  { id: 'proxy', label: 'Org proxy' },
];

export default function Component09Integration() {
  const { user } = useAuth();
  const { copied, copy } = useCopy();
  const [tab, setTab] = useState('javascript');

  const base = `${API_BASE}/v1`;
  const key = user?.ingress_api_key || 'ak_your_ingress_key';

  const snippets: Record<string, string> = useMemo(() => ({
    javascript:
`import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "${base}",          // ← route through Aegis
  apiKey: "${key}",            // ← your ingress key
});

const res = await client.chat.completions.create({
  model: "gpt-4o-mini",        // any model you configured in Gateway
  messages: [{ role: "user", content: "Hello!" }],
});
console.log(res.choices[0].message.content);`,
    python:
`from openai import OpenAI

client = OpenAI(
    base_url="${base}",        # ← route through Aegis
    api_key="${key}",          # ← your ingress key
)

res = client.chat.completions.create(
    model="gpt-4o-mini",       # any model you configured in Gateway
    messages=[{"role": "user", "content": "Hello!"}],
)
print(res.choices[0].message.content)`,
    env:
`# Set once per machine / container / CI — most SDKs read these
# automatically, so existing apps route through Aegis with no code change.
export OPENAI_BASE_URL="${base}"
export OPENAI_API_KEY="${key}"`,
    curl:
`curl ${base}/chat/completions \\
  -H "Authorization: Bearer ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{ "role": "user", "content": "Hello!" }]
  }'`,
    app:
`Any tool with an "OpenAI-compatible" or "Custom Base URL" option
(LibreChat, Flowise, LangChain, many IDE AI plugins, etc.):

  Base URL / API Host :  ${base}
  API Key             :  ${key}
  Model               :  a model you enabled in Gateway (e.g. gpt-4o-mini)

That's it — every request now flows through Aegis.`,
    proxy:
`For org-wide governance with NO app or env changes, redirect provider
traffic to Aegis at the network layer (transparent egress proxy):

  • Point api.openai.com (etc.) at Aegis via your forward proxy,
    Kubernetes egress, or DNS / /etc/hosts override.
  • Aegis must present a trusted TLS cert for those hostnames
    (TLS interception). Powerful, but set up by your infra/security team.

Most teams start with the .env approach and graduate to this later.`,
  }), [base, key]);

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="Integration"
        title="Route any app through Aegis in two lines."
        subtitle="Point your client's base URL at Aegis and use your ingress key. Aegis governs the request, calls your provider with your stored key, and returns a standard response."
      />

      <Reveal delay={0.04}>
        <Panel className="flex flex-col gap-4">
          <div className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-xl bg-brand/10 text-brand">
              <KeyRound size={17} />
            </span>
            <div>
              <h2 className="text-[15px] font-semibold text-ink">Your Ingress Key</h2>
              <p className="text-[11px] text-soft">Used as <code className="text-ink">Authorization: Bearer</code> or <code className="text-ink">X-API-Key</code>. Manage/rotate it in Gateway.</p>
            </div>
          </div>
          <CodeBlock id="key" code={key} copied={copied} onCopy={copy} />
        </Panel>
      </Reveal>

      <Reveal delay={0.06}>
        <Panel className="flex flex-col gap-3">
          <SectionTitle hint="mental model">How routing works</SectionTitle>
          <div className="flex flex-wrap items-center gap-2 text-[12px] text-ink">
            <span className="rounded-lg border border-hairline bg-surface2/60 px-3 py-1.5">Your app</span>
            <ArrowRight size={14} className="text-soft" />
            <span className="rounded-lg border border-hairline bg-surface2/60 px-3 py-1.5">Aegis <span className="text-soft">(scan · risk · budget)</span></span>
            <ArrowRight size={14} className="text-soft" />
            <span className="rounded-lg border border-hairline bg-surface2/60 px-3 py-1.5">Your LLM provider</span>
            <ArrowRight size={14} className="text-soft" />
            <span className="rounded-lg border border-hairline bg-surface2/60 px-3 py-1.5">Scanned response</span>
          </div>
          <p className="text-[11px] text-soft">
            The <strong className="text-ink">base URL</strong> decides where the request goes; the <strong className="text-ink">key</strong> says who you are. Swapping only the key won't reroute traffic — you must also set the base URL.
          </p>
        </Panel>
      </Reveal>

      <Reveal delay={0.08}>
        <Panel className="flex flex-col gap-4">
          <div className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-xl bg-brand/10 text-brand">
              <Plug size={17} />
            </span>
            <h2 className="text-[15px] font-semibold text-ink">Drop-in setup</h2>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                data-cursor="hover"
                className={`rounded-lg px-3 py-1.5 text-[12px] font-medium transition-colors ${
                  tab === t.id
                    ? 'bg-brand text-white'
                    : 'border border-hairline text-soft hover:text-ink'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <CodeBlock id={tab} code={snippets[tab]} copied={copied} onCopy={copy} />

          <div className="flex items-start gap-2 rounded-xl border border-hairline bg-surface2/40 p-3">
            <Info size={14} className="mt-0.5 shrink-0 text-soft" />
            <p className="text-[11px] text-soft">
              Prerequisite: add the provider (OpenAI, Anthropic, Google, …) and its API key under <strong className="text-ink">Gateway</strong> first. Aegis routes by model name and calls the provider with that stored key — your provider key never leaves Aegis. Streaming isn't supported yet (set <code className="text-ink">stream:false</code>).
            </p>
          </div>
        </Panel>
      </Reveal>
    </div>
  );
}
