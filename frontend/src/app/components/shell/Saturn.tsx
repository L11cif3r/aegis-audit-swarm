import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { X, Send, Loader2 } from 'lucide-react';
import { api } from '../../../lib/api';

type Msg = { role: 'user' | 'assistant'; content: string };

const GREETING: Msg = {
  role: 'assistant',
  content:
    "Hi, I'm Saturn — your Aegis guide. Ask me anything: how to route requests, where to put your POST call, your ingress key, billing, and more.",
};

const SUGGESTIONS = [
  'Where do I put the POST request?',
  'How do I use my ingress key?',
  'How do I add a provider key?',
];

function SaturnIcon({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="5.4" fill="currentColor" />
      <ellipse
        cx="12" cy="12" rx="10.2" ry="3.1"
        fill="none" stroke="currentColor" strokeWidth="1.7"
        transform="rotate(-22 12 12)"
      />
    </svg>
  );
}

export default function Saturn() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([GREETING]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading, open]);

  const send = async (text: string) => {
    const content = text.trim();
    if (!content || loading) return;
    const next = [...messages, { role: 'user' as const, content }];
    setMessages(next);
    setInput('');
    setLoading(true);
    try {
      const res = await api.assistantChat(next.map((m) => ({ role: m.role, content: m.content })));
      setMessages((m) => [...m, { role: 'assistant', content: res.reply }]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: `Sorry — I'm unavailable right now (${e?.message || 'error'}). Try the Integration tab for setup snippets.` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Launcher */}
      <motion.button
        onClick={() => setOpen((o) => !o)}
        data-cursor="hover"
        aria-label="Open Saturn support assistant"
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.6, type: 'spring', stiffness: 260, damping: 20 }}
        whileHover={{ scale: 1.06 }}
        whileTap={{ scale: 0.94 }}
        className="fixed bottom-5 right-5 z-50 grid size-14 place-items-center rounded-full bg-brand text-white shadow-xl shadow-brand/30"
      >
        <AnimatePresence mode="wait" initial={false}>
          {open ? (
            <motion.span key="x" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }}>
              <X size={22} />
            </motion.span>
          ) : (
            <motion.span key="s" initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: -90, opacity: 0 }}>
              <SaturnIcon />
            </motion.span>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.96 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="fixed bottom-24 right-5 z-50 flex h-[32rem] max-h-[calc(100vh-8rem)] w-[22rem] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-2xl border border-hairline bg-surface shadow-2xl shadow-black/20"
          >
            <div className="flex items-center gap-2.5 border-b border-hairline px-4 py-3">
              <span className="grid size-8 place-items-center rounded-full bg-brand text-white">
                <SaturnIcon size={18} />
              </span>
              <div className="leading-tight">
                <p className="text-[13px] font-semibold text-ink">Saturn</p>
                <p className="text-[10px] text-soft">Aegis support · always here</p>
              </div>
              <button onClick={() => setOpen(false)} data-cursor="hover" className="ml-auto text-soft hover:text-ink" aria-label="Close">
                <X size={16} />
              </button>
            </div>

            <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto scrollbar-slim px-4 py-4">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-[12.5px] leading-relaxed ${
                    m.role === 'user' ? 'bg-brand text-white rounded-br-sm' : 'bg-surface2 text-ink rounded-bl-sm border border-hairline'
                  }`}>
                    {m.content}
                  </div>
                </div>
              ))}

              {messages.length === 1 && !loading && (
                <div className="flex flex-col gap-1.5 pt-1">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      data-cursor="hover"
                      className="rounded-lg border border-hairline px-3 py-2 text-left text-[11.5px] text-soft hover:text-ink hover:border-brand/50 transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}

              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-bl-sm border border-hairline bg-surface2 px-3.5 py-2.5 text-soft">
                    <Loader2 size={14} className="animate-spin" />
                  </div>
                </div>
              )}
            </div>

            <form
              onSubmit={(e) => { e.preventDefault(); send(input); }}
              className="flex items-center gap-2 border-t border-hairline p-3"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask Saturn…"
                className="flex-1 rounded-xl border border-hairline bg-surface2/60 px-3 py-2 text-[12.5px] text-ink outline-none focus:border-brand"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                data-cursor="hover"
                className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand text-white disabled:opacity-40 transition-opacity"
                aria-label="Send"
              >
                <Send size={15} />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
