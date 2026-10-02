import type { InvestigationMessage, StreamDetections } from '../types';
import { useState, useRef, useEffect } from 'react';
import { dashboardFetch, investigateQuery, readJson } from '../api';
import { LoadingDots, SeverityBadge, formatDateTime } from '../components/Shared';
import { Send, Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
const SUGGESTIONS = [
  'What suspicious activity happened today?',
  'Who entered the restricted area?',
  'Show vault corridor events',
  'Any after-hours presence?',
  'Cash counter anomalies',
  'Show all critical events',
];
const WELCOME: InvestigationMessage = {
  role: 'ai',
  content: `**Welcome to AI Investigation**
Ask me anything about the CCTV footage in natural language:
• *"What suspicious activity happened near cash counter?"*
• *"Who entered the restricted area after hours?"*
• *"Show me all critical events from today"*
I'll search through event records and provide evidence-backed answers.`,
  timestamp: new Date().toISOString(),
};
function Bubble({ msg }: { msg: InvestigationMessage }) {
  const isAI = msg.role === 'ai';
  return (
    <div className={`chat-msg ${isAI ? 'ai' : 'user'}`}>
      <div className="chat-avatar">
        {isAI ? <Bot size={13} /> : <User size={13} />}
      </div>
      <div className="chat-bubble shadow-sm backdrop-blur-sm bg-white/90">
        <div className="markdown-body" style={{ whiteSpace: 'pre-wrap', fontSize: '0.95em' }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        </div>
        {}
        {msg.events && msg.events.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div className="text-xs text-muted mb-2" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.6px' }}>
              Evidence · {msg.events.length} events
            </div>
            {msg.events.slice(0, 4).map(ev => (
              <div
                key={ev.id}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderLeft: `2px solid ${ev.severity === 'critical' ? 'var(--red)' : ev.severity === 'high' ? 'var(--amber)' : 'var(--border)'}`,
                  borderRadius: 6,
                  padding: '9px 11px',
                  marginBottom: 6,
                }}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold" style={{ fontSize: 11 }}>
                    {ev.event_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </span>
                  <SeverityBadge severity={ev.severity} />
                </div>
                <div className="flex gap-3 text-xs text-muted mb-2">
                  <span>{ev.camera_name}</span>
                  <span className="font-mono">{formatDateTime(ev.timestamp)}</span>
                  {ev.person_id && <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{ev.person_id}</span>}
                </div>
                {ev.clip_ref ? (
                  <div className="flex gap-2 mt-2">
                    <video 
                      src={ev.clip_ref.startsWith('http') ? ev.clip_ref : `http://127.0.0.1:8000${ev.clip_ref}`} 
                      controls 
                      autoPlay
                      muted
                      loop
                      style={{ height: '90px', width: '100%', borderRadius: '4px', border: '1px solid var(--border)', background: '#000' }} 
                      onError={(e) => {
                        if (!e.currentTarget.dataset.fallback) {
                          e.currentTarget.dataset.fallback = 'true';
                          e.currentTarget.src = `http://127.0.0.1:8000/stream/${ev.camera_id}`;
                        } else {
                          e.currentTarget.style.display = 'none';
                        }
                      }}
                    />
                  </div>
                ) : ev.thumbnail && (
                  <div className="flex gap-2 mt-2">
                    <img src={ev.thumbnail} alt="Evidence Thumbnail" style={{ height: '70px', borderRadius: '4px', border: '1px solid var(--border)' }} />
                  </div>
                )}
              </div>
            ))}
            {msg.events.length > 4 && (
              <div className="text-xs text-muted" style={{ textAlign: 'center', padding: '4px 0' }}>
                +{msg.events.length - 4} more
              </div>
            )}
          </div>
        )}
        {}
        {msg.timeline && msg.timeline.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div className="text-xs text-muted mb-2" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.6px' }}>
              Timeline
            </div>
            <div className="timeline">
              {msg.timeline.slice(0, 5).map((t, i) => (
                <div
                  key={i}
                  className={`timeline-item ${t.type?.includes('restricted') || t.type?.includes('critical') ? 'tl-critical' : ''}`}
                >
                  <div className="timeline-time">{t.time?.slice(11, 19)}</div>
                  <div className="timeline-event">{t.event}</div>
                  <div className="timeline-camera">{t.camera}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="text-xs text-muted mt-2">
          {new Date(msg.timestamp).toLocaleTimeString('en-IN', { hour12: false })}
          {msg.confidence && ` · ${Math.round(msg.confidence * 100)}% confidence`}
        </div>
      </div>
    </div>
  );
}
export default function Investigate() {
  const [messages, setMessages] = useState<InvestigationMessage[]>([WELCOME]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  async function send(q?: string) {
    const query = q || input.trim();
    if (!query) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: query, timestamp: new Date().toISOString() }]);
    setLoading(true);
      let liveContext = "";
      try {
        const statsRes = await dashboardFetch('/reports/system/stats');
        if (statsRes.ok) {
          // We can't fetch 50 camera streams instantly, so we'll just summarize that the system is active
          // and let the backend handle the RAG. But we can fetch CAM_01 as a sample of live edge context.
          const detRes = await dashboardFetch('/stream/CAM_01/detections');
          if (detRes.ok) {
            const detData = await readJson<StreamDetections>(detRes);
            if (detData.status === "live") {
               liveContext = `\n[LIVE EDGE NODE CONTEXT (CAM_01)]: ${detData.total_objects} objects tracked, ${detData.vehicles} vehicles. Confirmed plates: ${detData.confirmed_plates.join(', ')}`;
            }
          }
        }
      } catch (e) {
        // Ignore live context errors
      }

      try {
        const res = await investigateQuery({ query: query + liveContext });
        const d = res.data;
        setMessages(prev => [...prev, {
          role: 'ai',
          content: d.answer,
          events: d.events || d.relevant_events,
          timeline: d.timeline,
          confidence: d.confidence,
          timestamp: new Date().toISOString(),
        }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'ai',
        content: 'Investigation service unavailable. Ensure backend is running on port 8000.',
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  }
  return (
    <div
      className="page-body"
      style={{ height: 'calc(100vh - 56px)', display: 'flex', flexDirection: 'column', padding: '16px 20px' }}
    >
      <div className="page-header" style={{ marginBottom: 12 }}>
        <div className="flex items-center gap-3">
          <div className="page-title">AI Investigation</div>
          <span className="bg-blue-500/10 border border-blue-500/20 text-blue-500 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
            Tracking 50 Cameras Live
          </span>
        </div>
        <div className="page-desc">Natural language query · Video RAG · Evidence retrieval</div>
      </div>
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 260px', gap: 14, minHeight: 0 }}>
        {}
        <div className="chat-area">
          <div className="chat-messages">
            {messages.map((m, i) => <Bubble key={i} msg={m} />)}
            {loading && (
              <div className="chat-msg ai">
                <div className="chat-avatar"><Bot size={13} /></div>
                <div className="chat-bubble">
                  <div className="flex items-center gap-2 text-muted text-xs">
                    <LoadingDots /> Searching event database…
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          {}
          <div className="suggestion-chips">
            {SUGGESTIONS.map(s => (
              <button key={s} className="chip" onClick={() => send(s)}>{s}</button>
            ))}
          </div>
          {}
          <div className="chat-input-bar">
            <input
              className="chat-input"
              placeholder="Ask about any event, person, zone, or time…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
              disabled={loading}
            />
            <button
              className="btn btn-primary btn-sm"
              onClick={() => send()}
              disabled={loading || !input.trim()}
            >
              <Send size={12} />
              {loading ? 'Searching…' : 'Ask'}
            </button>
          </div>
        </div>
        {}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">How It Works</span>
            </div>
            {[
              ['01', 'Query parsed into structured filters'],
              ['02', 'Event database searched (Video RAG)'],
              ['03', 'Relevant evidence clips retrieved'],
              ['04', 'VLM provides contextual analysis'],
              ['05', 'Evidence-backed answer generated'],
            ].map(([n, label]) => (
              <div key={n} className="flex gap-2 mb-3 items-start">
                <span style={{
                  fontFamily: 'var(--mono)', fontSize: 10, fontWeight: 700,
                  color: 'var(--amber)', minWidth: 22,
                }}>{n}</span>
                <span className="text-xs" style={{ color: 'var(--text-secondary)', lineHeight: 1.5 }}>{label}</span>
              </div>
            ))}
          </div>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Query Examples</span>
            </div>
            {SUGGESTIONS.map(s => (
              <button
                key={s}
                className="chip"
                style={{ display: 'block', width: '100%', textAlign: 'left', borderRadius: 6, marginBottom: 5, padding: '7px 10px' }}
                onClick={() => send(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
