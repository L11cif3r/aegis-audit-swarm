import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ChevronDown, Cloud, FlaskConical, KeyRound, Pencil, Plug, Save, Settings2, Zap,
} from 'lucide-react';
import {
  api,
  type CatalogEntry,
  type ProviderCatalog,
  type ProviderConfig,
  type ProviderTestResult,
  type ProxyRequestBody,
} from '../../lib/api';
import {
  PageHeader, Panel, SectionTitle, Badge, EmptyState, Bento,
} from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';

const SELECT_CLS =
  'w-full appearance-none rounded-xl border border-hairline bg-surface2/60 py-2.5 pl-3 pr-9 text-[12px] text-ink outline-none focus:border-brand/50';
const INPUT_CLS =
  'w-full rounded-xl border border-hairline bg-surface2/60 py-2 px-3 text-[12px] text-ink outline-none focus:border-brand/50';

type ProviderOption = { id: string; label: string; kind: 'builtin' | 'custom' };

type FormState = {
  api_key: string;
  base_url: string;
  chat_endpoint: string;
  model: string;
  input_price_per_m: string;
  output_price_per_m: string;
  enabled: boolean;
  // custom only
  provider_name: string;
  available_models: string;
};

function defaultForm(): FormState {
  return {
    api_key: '',
    base_url: '',
    chat_endpoint: '/v1/chat/completions',
    model: '',
    input_price_per_m: '',
    output_price_per_m: '',
    enabled: true,
    provider_name: '',
    available_models: '',
  };
}

function pricingForModel(
  catalog: ProviderCatalog | null,
  providerId: string,
  modelId: string,
  saved?: ProviderConfig | null,
): { input: string; output: string } {
  if (saved?.model_prices?.[modelId]) {
    return {
      input: String(saved.model_prices[modelId].input_price_per_m),
      output: String(saved.model_prices[modelId].output_price_per_m),
    };
  }
  const catModel = catalog?.[providerId]?.models.find((m) => m.id === modelId);
  if (catModel) {
    return {
      input: String(catModel.input_price_per_m),
      output: String(catModel.output_price_per_m),
    };
  }
  if (saved) {
    return {
      input: String(saved.input_price_per_m ?? ''),
      output: String(saved.output_price_per_m ?? ''),
    };
  }
  return { input: '', output: '' };
}

function modelsForSelection(
  providerId: string,
  catalog: ProviderCatalog | null,
  saved?: ProviderConfig | null,
): string[] {
  if (providerId === 'custom') return [];
  if (saved?.models?.length) return saved.models;
  return catalog?.[providerId]?.models.map((m) => m.id) ?? [];
}

export default function Component08GatewayConfig() {
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [savedProviders, setSavedProviders] = useState<ProviderConfig[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState('openai');
  const [form, setForm] = useState<FormState>(defaultForm);
  const [editPricing, setEditPricing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<ProviderTestResult | null>(null);

  const [testAgent, setTestAgent] = useState('Gateway Tester');
  const [testPrompt, setTestPrompt] = useState('Say hello in one short sentence.');
  const [testLoading, setTestLoading] = useState(false);
  const [testResponse, setTestResponse] = useState<any>(null);

  const load = useCallback(async () => {
    try {
      const [cat, provs] = await Promise.all([api.catalog(), api.providers()]);
      setCatalog(cat);
      setSavedProviders(provs);
    } catch {
      /* offline */
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const providerOptions: ProviderOption[] = useMemo(() => {
    const builtins: ProviderOption[] = Object.values(catalog ?? {})
      .filter((c) => c.id !== 'custom')
      .map((c) => ({ id: c.id, label: c.label, kind: 'builtin' as const }));
    const customs: ProviderOption[] = savedProviders
      .filter((p) => p.kind === 'custom')
      .map((p) => ({ id: p.provider, label: p.display_name, kind: 'custom' as const }));
    return [...builtins, { id: 'custom', label: 'Custom', kind: 'custom' }, ...customs];
  }, [catalog, savedProviders]);

  const isCustomNew = selectedProviderId === 'custom';
  const savedConfig = savedProviders.find((p) => p.provider === selectedProviderId) ?? null;
  const effectiveProviderId = isCustomNew
    ? 'custom'
    : (savedConfig?.kind === 'custom' ? savedConfig.provider : selectedProviderId);

  const modelOptions = useMemo(() => {
    if (isCustomNew) {
      const fromField = form.available_models.split(/[\n,]/).map((s) => s.trim()).filter(Boolean);
      if (fromField.length) return fromField;
      if (form.model) return [form.model];
      return [];
    }
    return modelsForSelection(selectedProviderId, catalog, savedConfig);
  }, [isCustomNew, form.available_models, form.model, selectedProviderId, catalog, savedConfig]);

  const selectedCatalog: CatalogEntry | null =
    catalog?.[isCustomNew ? 'custom' : selectedProviderId] ?? null;

  // Sync form when provider selection changes
  useEffect(() => {
    if (isCustomNew) {
      setForm({
        ...defaultForm(),
        provider_name: '',
        model: '',
      });
      setEditPricing(true);
      return;
    }
    const saved = savedProviders.find((p) => p.provider === selectedProviderId);
    const models = modelsForSelection(selectedProviderId, catalog, saved);
    const defaultModel = saved?.default_model || catalog?.[selectedProviderId]?.default_model || models[0] || '';
    const pricing = pricingForModel(catalog, selectedProviderId, defaultModel, saved);
    setForm({
      api_key: '',
      base_url: saved?.base_url || '',
      chat_endpoint: saved?.chat_endpoint || '/v1/chat/completions',
      model: defaultModel,
      input_price_per_m: pricing.input,
      output_price_per_m: pricing.output,
      enabled: saved?.enabled ?? true,
      provider_name: saved?.display_name || '',
      available_models: saved?.models?.join('\n') || '',
    });
    setEditPricing(false);
    setTestResult(null);
  }, [selectedProviderId, savedProviders, catalog, isCustomNew]);

  // Update pricing when model changes (built-in)
  useEffect(() => {
    if (isCustomNew || !form.model) return;
    const pricing = pricingForModel(catalog, selectedProviderId, form.model, savedConfig);
    if (!editPricing) {
      setForm((f) => ({
        ...f,
        input_price_per_m: pricing.input,
        output_price_per_m: pricing.output,
      }));
    }
  }, [form.model, selectedProviderId, catalog, savedConfig, isCustomNew, editPricing]);

  const patchForm = (patch: Partial<FormState>) => setForm((f) => ({ ...f, patch }));

  const saveConfig = async () => {
    setSaving(true);
    setTestResult(null);
    try {
      const body: Record<string, unknown> = {
        default_model: form.model,
        base_url: form.base_url,
        enabled: form.enabled,
        input_price_per_m: parseFloat(form.input_price_per_m) || 0,
        output_price_per_m: parseFloat(form.output_price_per_m) || 0,
      };
      if (form.api_key.trim()) body.api_key = form.api_key.trim();

      let targetId = selectedProviderId;
      if (isCustomNew || savedConfig?.kind === 'custom') {
        body.kind = 'custom';
        body.display_name = form.provider_name.trim() || 'Custom Provider';
        body.provider_name = body.display_name;
        body.chat_endpoint = form.chat_endpoint.trim() || '/v1/chat/completions';
        const models = form.available_models.split(/[\n,]/).map((s) => s.trim()).filter(Boolean);
        if (models.length) body.models = models;
        else if (form.model) body.models = [form.model];
        targetId = isCustomNew ? 'custom' : selectedProviderId;
      }

      const updated = await api.updateProvider(targetId, body);
      setSavedProviders((list) => {
        const idx = list.findIndex((p) => p.provider === updated.provider);
        if (idx >= 0) {
          const next = [...list];
          next[idx] = updated;
          return next;
        }
        return [...list, updated];
      });
      if (isCustomNew) setSelectedProviderId(updated.provider);
      setForm((f) => ({ ...f, api_key: '' }));
      await load();
    } catch (e: any) {
      setTestResult({ ok: false, provider: selectedProviderId, error: e.message || 'Save failed' });
    } finally {
      setSaving(false);
    }
  };

  const runTest = async () => {
    const testId = isCustomNew ? null : (savedConfig?.provider || selectedProviderId);
    if (!testId || testId === 'custom') {
      setTestResult({ ok: false, provider: selectedProviderId, error: 'Save the custom provider before testing' });
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testProvider(testId, form.model || undefined);
      setTestResult(res);
    } catch (e: any) {
      setTestResult({ ok: false, provider: testId, error: e.message || 'Test failed' });
    } finally {
      setTesting(false);
    }
  };

  const submitProxyTest = async () => {
    setTestLoading(true);
    setTestResponse(null);
    try {
      const body: ProxyRequestBody = { agent: testAgent, prompt: testPrompt };
      if (form.model) body.model = form.model;
      const res = await api.proxyRequest(body);
      setTestResponse(res);
    } catch (e: any) {
      setTestResponse({ status: 'error', response: e.message || 'Request failed' });
    } finally {
      setTestLoading(false);
    }
  };

  const showCustomFields = isCustomNew || savedConfig?.kind === 'custom';
  const keyConfigured = savedConfig?.api_key_set ?? false;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="AI Gateway"
        title="One panel. Every provider."
        subtitle="Select a provider, choose a model, configure credentials, and test — including custom OpenAI-compatible endpoints."
      />

      <Reveal delay={0.05}>
        <Panel className="flex flex-col gap-6">
          {/* Header row */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-hairline">
            <div className="flex items-center gap-2.5">
              <span className="grid size-9 place-items-center rounded-xl bg-brand/10 text-brand">
                <Settings2 size={17} />
              </span>
              <div>
                <h2 className="text-[15px] font-semibold text-ink">Provider Configuration</h2>
                <p className="text-[11px] text-soft">Configure upstream LLM routing and credentials</p>
              </div>
            </div>
            {savedConfig && (
              <Badge tone={savedConfig.enabled ? 'ok' : 'neutral'}>
                {savedConfig.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            )}
          </div>

          {/* Step 1: Provider */}
          <div className="grid gap-4 lg:grid-cols-2">
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-soft">Provider</span>
              <div className="relative">
                <select
                  value={selectedProviderId}
                  onChange={(e) => setSelectedProviderId(e.target.value)}
                  className={SELECT_CLS}
                >
                  {providerOptions.map((o) => (
                    <option key={o.id} value={o.id}>{o.label}</option>
                  ))}
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-soft pointer-events-none" />
              </div>
            </label>

            {/* Step 2: Model */}
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-soft">Model</span>
              {showCustomFields && isCustomNew ? (
                <input
                  type="text"
                  placeholder="e.g. acme-chat-large"
                  value={form.model}
                  onChange={(e) => patchForm({ model: e.target.value })}
                  className={INPUT_CLS}
                />
              ) : (
                <div className="relative">
                  <select
                    value={form.model}
                    onChange={(e) => patchForm({ model: e.target.value })}
                    className={SELECT_CLS}
                    disabled={modelOptions.length === 0}
                  >
                    {modelOptions.length === 0 ? (
                      <option value="">No models available</option>
                    ) : (
                      modelOptions.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))
                    )}
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-soft pointer-events-none" />
                </div>
              )}
            </label>
          </div>

          {/* Custom provider fields */}
          {showCustomFields && (
            <div className="rounded-xl border border-hairline bg-surface2/30 p-4 flex flex-col gap-3">
              <div className="flex items-center gap-2 text-[11px] font-semibold text-brand uppercase tracking-wider">
                <Cloud size={13} />
                Custom Provider
              </div>
              <div className="grid gap-3 lg:grid-cols-2">
                <label className="flex flex-col gap-1.5">
                  <span className="text-[10px] uppercase tracking-wider text-soft">Provider Name</span>
                  <input
                    type="text"
                    placeholder="Acme AI"
                    value={form.provider_name}
                    onChange={(e) => patchForm({ provider_name: e.target.value })}
                    className={INPUT_CLS}
                  />
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="text-[10px] uppercase tracking-wider text-soft">Chat Completion Endpoint</span>
                  <input
                    type="text"
                    placeholder="/v1/chat/completions"
                    value={form.chat_endpoint}
                    onChange={(e) => patchForm({ chat_endpoint: e.target.value })}
                    className={INPUT_CLS}
                  />
                </label>
              </div>
              <label className="flex flex-col gap-1.5">
                <span className="text-[10px] uppercase tracking-wider text-soft">Available Models (one per line or comma-separated)</span>
                <textarea
                  rows={2}
                  placeholder="acme-chat-large&#10;acme-chat-small"
                  value={form.available_models}
                  onChange={(e) => patchForm({ available_models: e.target.value })}
                  className={`${INPUT_CLS} resize-none font-mono`}
                />
              </label>
            </div>
          )}

          {/* Step 3: Pricing */}
          <div className="rounded-xl border border-hairline bg-surface2/20 p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-soft">Model Pricing</span>
              {!isCustomNew && (
                <button
                  type="button"
                  onClick={() => setEditPricing((v) => !v)}
                  className="flex items-center gap-1 text-[10px] font-semibold text-brand hover:text-brand/80 transition-colors"
                >
                  <Pencil size={11} />
                  {editPricing ? 'Lock Pricing' : 'Edit Pricing'}
                </button>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="flex flex-col gap-1.5">
                <span className="text-[10px] uppercase tracking-wider text-soft">Input Cost / 1M Tokens ($)</span>
                <input
                  type="number"
                  step="0.01"
                  readOnly={!editPricing && !isCustomNew}
                  value={form.input_price_per_m}
                  onChange={(e) => patchForm({ input_price_per_m: e.target.value })}
                  className={`${INPUT_CLS} ${!editPricing && !isCustomNew ? 'opacity-70 cursor-default' : ''}`}
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-[10px] uppercase tracking-wider text-soft">Output Cost / 1M Tokens ($)</span>
                <input
                  type="number"
                  step="0.01"
                  readOnly={!editPricing && !isCustomNew}
                  value={form.output_price_per_m}
                  onChange={(e) => patchForm({ output_price_per_m: e.target.value })}
                  className={`${INPUT_CLS} ${!editPricing && !isCustomNew ? 'opacity-70 cursor-default' : ''}`}
                />
              </label>
            </div>
            {!editPricing && !isCustomNew && selectedCatalog && (
              <p className="text-[10px] text-soft">Auto-populated from catalog for {form.model || 'selected model'}.</p>
            )}
          </div>

          {/* Step 4: Credentials */}
          <div className="grid gap-4 lg:grid-cols-2">
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-soft">API Key</span>
              <div className="relative">
                <KeyRound size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-soft" />
                <input
                  type="password"
                  placeholder={keyConfigured ? savedConfig?.api_key_masked || '••••••••' : 'Enter API key'}
                  value={form.api_key}
                  onChange={(e) => patchForm({ api_key: e.target.value })}
                  className={`${INPUT_CLS} pl-9`}
                />
              </div>
              <span className="text-[9px] text-soft">
                {keyConfigured
                  ? `Configured (${savedConfig?.api_key_source}) — leave blank to keep existing`
                  : 'Uses environment variable if set'}
              </span>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-soft">Base URL (optional)</span>
              <input
                type="text"
                placeholder={
                  selectedProviderId === 'groq' ? 'https://api.groq.com/openai/v1'
                    : selectedProviderId === 'openrouter' ? 'https://openrouter.ai/api/v1'
                      : selectedProviderId === 'azure' ? 'https://{resource}.openai.azure.com/openai/deployments/{deployment}'
                        : 'Default SDK endpoint'
                }
                value={form.base_url}
                onChange={(e) => patchForm({ base_url: e.target.value })}
                className={INPUT_CLS}
              />
            </label>
          </div>

          <label className="flex items-center gap-2 cursor-pointer w-fit">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) => patchForm({ enabled: e.target.checked })}
              className="rounded border-hairline accent-brand"
            />
            <span className="text-[12px] text-ink">Enabled</span>
          </label>

          {/* Test result */}
          {testResult && (
            <div
              className={`rounded-xl border px-4 py-3 text-[12px] ${
                testResult.ok
                  ? 'border-ok/30 bg-ok/5 text-ok'
                  : 'border-bad/30 bg-bad/5 text-bad'
              }`}
            >
              <p className="font-semibold">{testResult.message || (testResult.ok ? 'Connected Successfully' : testResult.error)}</p>
              {testResult.ok && (
                <p className="text-[11px] mt-1 opacity-90">
                  {testResult.latency_ms != null && `Latency: ${testResult.latency_ms} ms · `}
                  Model: {testResult.model}
                </p>
              )}
              {!testResult.ok && testResult.error && (
                <p className="text-[11px] mt-1 opacity-90">{testResult.error}</p>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-2 pt-2 border-t border-hairline">
            <button
              type="button"
              onClick={saveConfig}
              disabled={saving}
              className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-brand/90 hover:bg-brand text-white py-2.5 text-[12px] font-semibold transition-colors disabled:opacity-50"
            >
              <Save size={14} />
              {saving ? 'Saving…' : 'Save Configuration'}
            </button>
            <button
              type="button"
              onClick={runTest}
              disabled={testing || isCustomNew}
              className="flex-1 flex items-center justify-center gap-2 rounded-xl border border-hairline bg-surface2/60 hover:bg-surface2 py-2.5 text-[12px] font-semibold text-ink transition-colors disabled:opacity-50"
            >
              <Plug size={14} />
              {testing ? 'Testing…' : 'Test Provider'}
            </button>
          </div>
        </Panel>
      </Reveal>

      {/* Request Tester */}
      <Reveal delay={0.1}>
        <Panel>
          <div className="flex items-center gap-2 mb-4">
            <FlaskConical size={16} className="text-brand" />
            <SectionTitle hint="uses selected provider + model">Request Tester</SectionTitle>
          </div>
          <Bento className="!grid-cols-1 lg:!grid-cols-2 gap-4">
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2 mb-1">
                <Badge tone="brand">{providerOptions.find((o) => o.id === selectedProviderId)?.label || selectedProviderId}</Badge>
                {form.model && <Badge tone="neutral">{form.model}</Badge>}
              </div>
              <label className="flex flex-col gap-1">
                <span className="text-[10px] uppercase tracking-wider text-soft">Agent</span>
                <input value={testAgent} onChange={(e) => setTestAgent(e.target.value)} className={INPUT_CLS} />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-[10px] uppercase tracking-wider text-soft">Prompt</span>
                <textarea
                  value={testPrompt}
                  onChange={(e) => setTestPrompt(e.target.value)}
                  rows={4}
                  className={`${INPUT_CLS} resize-none`}
                />
              </label>
              <button
                type="button"
                onClick={submitProxyTest}
                disabled={testLoading || !testPrompt.trim() || !form.model}
                className="flex items-center justify-center gap-2 rounded-xl bg-brand/90 hover:bg-brand text-white py-2.5 text-[12px] font-semibold transition-colors disabled:opacity-50"
              >
                <Zap size={14} />
                {testLoading ? 'Sending…' : 'POST /agent/request'}
              </button>
            </div>

            <div className="rounded-xl border border-hairline bg-surface2/40 p-4 min-h-[240px] flex flex-col gap-2">
              <span className="text-[10px] uppercase tracking-wider text-soft">Response</span>
              {!testResponse ? (
                <EmptyState>Submit a test request to see the gateway response.</EmptyState>
              ) : (
                <div className="flex flex-col gap-2 text-[11px] overflow-auto scrollbar-slim flex-1">
                  <div className="flex flex-wrap gap-2">
                    <Badge tone={testResponse.status === 'success' ? 'ok' : testResponse.status === 'held' ? 'warn' : 'bad'}>
                      {testResponse.status}
                    </Badge>
                    {testResponse.gate_decision && <Badge tone="neutral">gate: {testResponse.gate_decision}</Badge>}
                    {testResponse.model && <Badge tone="brand">{testResponse.model}</Badge>}
                  </div>
                  {(testResponse.input_tokens > 0 || testResponse.output_tokens > 0) && (
                    <p className="text-soft font-mono">
                      {testResponse.input_tokens} in · {testResponse.output_tokens} out · {testResponse.cost}
                    </p>
                  )}
                  {testResponse.risk_score != null && <p className="text-soft">Risk score: {testResponse.risk_score}</p>}
                  <pre className="whitespace-pre-wrap break-words text-ink bg-surface/80 rounded-lg p-3 text-[11px] leading-relaxed flex-1">
                    {testResponse.response}
                  </pre>
                </div>
              )}
            </div>
          </Bento>
        </Panel>
      </Reveal>
    </div>
  );
}
