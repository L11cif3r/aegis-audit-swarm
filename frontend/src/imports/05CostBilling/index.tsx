import { CreditCard, BarChart3, Database } from 'lucide-react';

export default function Component05CostBilling() {
  return (
    <div className="p-4 flex flex-col gap-5 w-full max-w-md mx-auto">
      <div>
        <h1 className="text-lg font-bold text-white tracking-tight">Cost & Billing</h1>
        <p className="text-xs text-[#64748b] mt-0.5 leading-relaxed">Token consumption and provider expenses.</p>
      </div>

      <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-4 flex flex-col gap-2">
        <div className="flex justify-between items-start"><span className="text-[10px] text-[#64748b] font-bold uppercase tracking-wider">Total Spend (MTD)</span><CreditCard size={14} color="#f59e0b" /></div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold text-[#e2e8f0] font-mono leading-none">$142.80</span>
          <span className="text-[10px] font-medium text-emerald-400">Projected: $310.00</span>
        </div>
      </div>

      <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-4 flex flex-col gap-3">
        <h2 className="text-xs font-bold text-[#e2e8f0] tracking-wide">Model Usage Breakdown</h2>
        <div className="divide-y divide-[#1e2d45]/40 text-xs">
          <div className="py-2.5 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Database size={12} color="#8b5cf6" />
              <div>
                <p className="font-semibold text-white">Claude 3.5 Sonnet</p>
                <p className="text-[10px] text-[#64748b]">Security & Notary Agent</p>
              </div>
            </div>
            <span className="font-mono text-[#e2e8f0]">$84.20</span>
          </div>
          <div className="py-2.5 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Database size={12} color="#3b82f6" />
              <div>
                <p className="font-semibold text-white">Gemini Flash Live</p>
                <p className="text-[10px] text-[#64748b]">Voice Sessions</p>
              </div>
            </div>
            <span className="font-mono text-[#e2e8f0]">$41.10</span>
          </div>
          <div className="py-2.5 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Database size={12} color="#10b981" />
              <div>
                <p className="font-semibold text-white">GPT-4o Mini</p>
                <p className="text-[10px] text-[#64748b]">Content Studio</p>
              </div>
            </div>
            <span className="font-mono text-[#e2e8f0]">$17.50</span>
          </div>
        </div>
      </div>
    </div>
  );
}