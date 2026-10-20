import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Layers, ChevronDown, ChevronUp, Network, Copy, Check } from 'lucide-react';
import { querySystem } from '../api';
import SourcePanel from './SourcePanel';

const SAMPLE_QUESTIONS = [
  "What is the portfolio allocation requirement for Multi Cap mutual funds under SEBI categorization circulars?",
  "What is the mandatory liquid assets percentage and graded exit load framework for liquid mutual funds?",
  "Explain the Priority Sector Lending (PSL) targets for domestic commercial banks under RBI Master Directions.",
  "What are the conditions and approval requirements for creating a segregated portfolio (side-pocket) in mutual funds?"
];

export default function Chat({ onSubgraphActive }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hello! I am your **SEBI & RBI Regulatory Intelligence Assistant**. Ask me any compliance question, and I'll ground my response directly in regulatory circulars with multi-hop knowledge graph reasoning and citations.",
      citations: [],
      subgraph: null,
      mode: 'hybrid'
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [ragMode, setRagMode] = useState('hybrid'); // 'hybrid' or 'vanilla'
  const [expandedSources, setExpandedSources] = useState({});
  const [copiedIdx, setCopiedIdx] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = async (queryText) => {
    const q = queryText || inputQuery;
    if (!q.trim() || loading) return;

    const userMessage = { role: 'user', content: q };
    setMessages((prev) => [...prev, userMessage]);
    if (!queryText) setInputQuery('');
    setLoading(true);

    try {
      const res = await querySystem(q, ragMode, 6);
      const assistantMessage = {
        role: 'assistant',
        content: res.answer,
        citations: res.citations || [],
        subgraph: res.subgraph || null,
        mode: res.retrieval_mode || ragMode
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Inform parent to highlight traversed subgraph in ForceGraph2D
      if (res.subgraph && onSubgraphActive) {
        onSubgraphActive(res.subgraph);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, encountered an error processing your query against the regulatory index. Please check your connection or backend logs.',
          citations: [],
          subgraph: null,
          mode: ragMode
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSources = (idx) => {
    setExpandedSources((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const copyText = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl">
      {/* Top Header / Mode Switcher */}
      <div className="px-5 py-3.5 bg-slate-900/90 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Regulatory Q&A Intelligence</h3>
            <span className="text-[11px] text-slate-400">Grounded in SEBI & RBI circulars</span>
          </div>
        </div>

        {/* Toggle Mode: Hybrid GraphRAG vs Vanilla RAG */}
        <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setRagMode('hybrid')}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              ragMode === 'hybrid'
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3 h-3 text-amber-300" />
            GraphRAG (Hybrid)
          </button>
          <button
            onClick={() => setRagMode('vanilla')}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              ragMode === 'vanilla'
                ? 'bg-slate-800 text-slate-200 shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3 h-3" />
            Vanilla RAG (Vector)
          </button>
        </div>
      </div>

      {/* Message History */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0 mt-0.5">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-1' : 'order-2'}`}>
              <div
                className={`p-4 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white shadow-lg rounded-tr-xs'
                    : 'bg-slate-900/90 border border-slate-800 text-slate-200 shadow-xl rounded-tl-xs'
                }`}
              >
                {/* Assistant Metadata Header */}
                {msg.role === 'assistant' && (
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-xs text-slate-400">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      msg.mode === 'hybrid'
                        ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                        : 'bg-slate-800 text-slate-400'
                    }`}>
                      {msg.mode === 'hybrid' ? '⚡ GraphRAG Hybrid Traversal' : '📄 Vanilla Vector RAG'}
                    </span>
                    <button
                      onClick={() => copyText(msg.content, idx)}
                      className="hover:text-slate-200 flex items-center gap-1 transition-colors"
                    >
                      {copiedIdx === idx ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                )}

                {/* Body Text */}
                <div className="whitespace-pre-line prose prose-invert prose-sm max-w-none">
                  {msg.content}
                </div>

                {/* Subgraph Highlighter Action */}
                {msg.subgraph?.nodes?.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                    <button
                      onClick={() => onSubgraphActive && onSubgraphActive(msg.subgraph)}
                      className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1.5 font-medium transition-colors"
                    >
                      <Network className="w-3.5 h-3.5" />
                      Highlight {msg.subgraph.nodes.length} Traversed Entities on Graph
                    </button>
                  </div>
                )}

                {/* Sources & Citations Accordion */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-slate-800/80">
                    <button
                      onClick={() => toggleSources(idx)}
                      className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 font-medium transition-colors"
                    >
                      {expandedSources[idx] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      {expandedSources[idx] ? 'Hide Grounding Sources' : `View Grounding Sources (${msg.citations.length})`}
                    </button>

                    {expandedSources[idx] && <SourcePanel sources={msg.citations} />}
                  </div>
                )}
              </div>
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-0.5 order-2">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3.5 items-center text-slate-400 text-xs py-2">
            <div className="w-8 h-8 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 animate-pulse">
              <Bot className="w-4 h-4" />
            </div>
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-4 py-2.5 rounded-2xl">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping"></span>
              <span>
                {ragMode === 'hybrid'
                  ? 'Traversing knowledge graph & reranking cross-encoder citations...'
                  : 'Searching dense vector chunks in ChromaDB...'}
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions Carousel */}
      {messages.length <= 2 && (
        <div className="px-5 py-2.5 bg-slate-950 border-t border-slate-800/60 overflow-x-auto flex gap-2">
          {SAMPLE_QUESTIONS.map((sq, i) => (
            <button
              key={i}
              onClick={() => handleSubmit(sq)}
              className="text-[11px] text-slate-400 hover:text-slate-200 bg-slate-900 hover:bg-slate-800/90 border border-slate-800 px-3 py-1.5 rounded-xl whitespace-nowrap transition-all"
            >
              {sq}
            </button>
          ))}
        </div>
      )}

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSubmit();
        }}
        className="p-4 bg-slate-900/90 border-t border-slate-800/80 flex items-center gap-3"
      >
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder="Ask any regulatory compliance question (e.g. Multi Cap rules, PSL targets, ECB hedging)..."
          className="flex-1 bg-slate-950 border border-slate-700/80 focus:border-blue-500 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !inputQuery.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl font-medium text-sm flex items-center gap-2 transition-all shadow-lg shadow-blue-600/20"
        >
          <Send className="w-4 h-4" />
          Send
        </button>
      </form>
    </div>
  );
}
