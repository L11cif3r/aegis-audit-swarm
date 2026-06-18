import { useEffect, useState } from 'react';
import { BookOpen, Crosshair, Download } from 'lucide-react';
import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts';
import { motion } from 'motion/react';
import { api, API_BASE } from '../../lib/api';
import { TRUST_SCORE_INFO, CONTROL_COVERAGE_INFO, ADVERSARY_COVERAGE_INFO } from '../../lib/trustInfo';
import { PageHeader, Panel, SectionTitle, Badge, EmptyState, Bento } from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';
import Magnetic from '../../app/components/shell/Magnetic';
import InfoTip from '../../app/components/shell/InfoTip';

const FRAMEWORK_LABELS: Record<string, string> = {
  NIST_AI_RMF: 'NIST AI RMF',
  ISO_27001: 'ISO 27001',
  EU_AI_ACT: 'EU AI Act',
};

function bandTone(band: string): 'ok' | 'warn' | 'bad' {
  if (band === 'CERTIFIED') return 'ok';
  if (band === 'CONDITIONAL') return 'warn';
  return 'bad';
}
function bandColor(band: string) {
  if (band === 'CERTIFIED') return 'var(--ok)';
  if (band === 'CONDITIONAL') return 'var(--warn)';
  return 'var(--bad)';
}

export default function Component06Compliance() {
  const [trust, setTrust] = useState<any>(null);
  const [coverage, setCoverage] = useState<any>(null);
  const [advCoverage, setAdvCoverage] = useState<any>(null);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [t, c, a] = await Promise.all([api.trustScore(), api.coverage(), api.adversaryCoverage()]);
        setTrust(t); setCoverage(c); setAdvCoverage(a);
      } catch {
        /* offline */
      }
    };
    fetchAll();
    const interval = setInterval(fetchAll, 4000);
    return () => clearInterval(interval);
  }, []);

  const score = trust?.trust_score ?? 0;
  const band = trust?.band ?? 'AT_RISK';
  const frameworks: Record<string, number> = coverage?.by_framework || {};
  const gauge = [{ name: 'score', value: score, fill: bandColor(band) }];

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="Trust Certification"
        title="An independent verdict on your AI."
        subtitle="Continuous Aegis Swarm scoring across NIST, ISO, and the EU AI Act."
      />

      <Bento>
        {/* Trust gauge */}
        <Reveal delay={0.05} className="lg:col-span-5">
          <Panel className="h-full flex flex-col items-center gap-1">
            <div className="relative h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart innerRadius="72%" outerRadius="100%" data={gauge} startAngle={220} endAngle={-40}>
                  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                  <RadialBar dataKey="value" cornerRadius={20} background={{ fill: 'var(--hairline)' }} />
                </RadialBarChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pb-4">
                <motion.span
                  key={score}
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="font-display text-6xl text-ink tabular-nums"
                >
                  {score}
                </motion.span>
                <span className="text-[10px] uppercase tracking-[0.2em] text-soft mt-1 flex items-center gap-1.5">
                  Trust Score
                  <InfoTip text={TRUST_SCORE_INFO} />
                </span>
              </div>
            </div>
            <Badge tone={bandTone(band)}>{band}</Badge>

            {trust?.components && (
              <div className="grid grid-cols-2 gap-x-8 gap-y-2 mt-5 w-full text-[11px] text-soft">
                <span>Adversary pass <span className="float-right text-ink font-medium">{(trust.components.adversarial_pass_rate * 100).toFixed(0)}%</span></span>
                <span>Ledger <span className="float-right text-ink font-medium">{trust.components.ledger_integrity ? 'VALID' : 'BROKEN'}</span></span>
                <span>Gate health <span className="float-right text-ink font-medium">{(trust.components.gate_health * 100).toFixed(0)}%</span></span>
                <span>Block health <span className="float-right text-ink font-medium">{(trust.components.block_health * 100).toFixed(0)}%</span></span>
              </div>
            )}

            <Magnetic className="mt-5">
              <a
                href={`${API_BASE}/notary/certificate.pdf`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-brandink bg-brand rounded-full px-5 py-2.5 hover:opacity-90 transition-opacity"
              >
                <Download size={13} /> Download Safety Certificate
              </a>
            </Magnetic>
          </Panel>
        </Reveal>

        {/* Coverage stack */}
        <div className="lg:col-span-7 flex flex-col gap-4 sm:gap-5">
          <Reveal delay={0.1}>
            <Panel>
              <div className="flex items-center gap-2">
                <BookOpen size={15} className="text-brand" />
                <SectionTitle
                  hint={`${coverage?.total_controls ?? 0} controls`}
                  info={<InfoTip text={CONTROL_COVERAGE_INFO} />}
                >
                  Control Library Coverage
                </SectionTitle>
              </div>
              <div className="grid sm:grid-cols-3 gap-2.5 mt-4">
                {Object.keys(frameworks).length === 0 ? (
                  <div className="sm:col-span-3"><EmptyState>Loading control library…</EmptyState></div>
                ) : (
                  Object.entries(frameworks).map(([fw, count]) => (
                    <div key={fw} className="rounded-xl border border-hairline bg-surface2/60 p-4 flex flex-col gap-1">
                      <span className="text-[12px] font-semibold text-ink">{FRAMEWORK_LABELS[fw] || fw}</span>
                      <span className="font-display text-2xl text-brand tabular-nums">{count}</span>
                      <span className="text-[10px] text-soft">controls mapped</span>
                    </div>
                  ))
                )}
              </div>
            </Panel>
          </Reveal>

          <Reveal delay={0.15}>
            <Panel>
              <div className="flex items-center gap-2">
                <Crosshair size={15} className="text-bad" />
                <SectionTitle
                  hint={`pass ${((advCoverage?.pass_rate ?? 1) * 100).toFixed(0)}%`}
                  info={<InfoTip text={ADVERSARY_COVERAGE_INFO} />}
                >
                  Adversary Test Coverage
                </SectionTitle>
              </div>
              <div className="grid grid-cols-3 gap-2.5 mt-4">
                {[
                  { label: 'Passed', value: advCoverage?.passed ?? 0, color: 'var(--ok)' },
                  { label: 'Partial', value: advCoverage?.partial ?? 0, color: 'var(--warn)' },
                  { label: 'Failed', value: advCoverage?.failed ?? 0, color: 'var(--bad)' },
                ].map((s) => (
                  <div key={s.label} className="rounded-xl border border-hairline bg-surface2/60 p-4 text-center">
                    <p className="text-3xl font-bold font-display tabular-nums" style={{ color: s.color }}>{s.value}</p>
                    <p className="text-[9px] uppercase tracking-wide text-soft mt-1">{s.label}</p>
                  </div>
                ))}
              </div>
            </Panel>
          </Reveal>
        </div>
      </Bento>
    </div>
  );
}
