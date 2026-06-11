import { Users, Target, TrendingUp, CheckCircle2 } from 'lucide-react';

export default function Component03LeadPipeline() {
  const mockLeads = [
    { id: 1, name: "Acme Corp", contact: "ceo@acme.co", status: "Qualified", score: 92 },
    { id: 2, name: "Stark Ind.", contact: "tony@stark.com", status: "Contacted", score: 85 },
    { id: 3, name: "Wayne Ent.", contact: "bruce@wayne.com", status: "New", score: 78 },
  ];

  return (
    <div className="p-4 flex flex-col gap-5 w-full max-w-md mx-auto">
      <div>
        <h1 className="text-lg font-bold text-white tracking-tight">Lead Pipeline</h1>
        <p className="text-xs text-[#64748b] mt-0.5 leading-relaxed">AI-driven prospect discovery and scoring.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-3 flex flex-col gap-2">
          <div className="flex justify-between items-start"><span className="text-[10px] text-[#64748b] font-bold uppercase tracking-wider">Total Leads</span><Users size={14} color="#3b82f6" /></div>
          <span className="text-2xl font-bold text-[#e2e8f0] font-mono leading-none">1,204</span>
        </div>
        <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-3 flex flex-col gap-2">
          <div className="flex justify-between items-start"><span className="text-[10px] text-[#64748b] font-bold uppercase tracking-wider">Conversion</span><TrendingUp size={14} color="#10b981" /></div>
          <span className="text-2xl font-bold text-[#e2e8f0] font-mono leading-none">12.4%</span>
        </div>
      </div>

      <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-4 flex flex-col gap-3">
        <h2 className="text-xs font-bold text-[#e2e8f0] tracking-wide">Recent Discoveries</h2>
        <div className="flex flex-col gap-2">
          {mockLeads.map((lead) => (
            <div key={lead.id} className="bg-[#080c14] border border-[#1e2d45]/50 rounded-lg p-3 flex items-center justify-between">
              <div className="flex flex-col gap-0.5">
                <span className="text-[11px] font-bold text-white">{lead.name}</span>
                <span className="text-[9px] text-[#64748b] truncate">{lead.contact}</span>
              </div>
              <div className="flex flex-col items-end gap-1">
                <span className={`text-[8px] font-black px-1.5 py-0.5 rounded ${lead.status === 'Qualified' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-blue-500/15 text-blue-400'}`}>{lead.status.toUpperCase()}</span>
                <span className="text-[9px] text-[#64748b]">Score: {lead.score}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}