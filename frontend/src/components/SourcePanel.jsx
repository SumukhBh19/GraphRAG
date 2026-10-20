import React, { useState } from 'react';
import { BookOpen, FileText, ChevronDown, ChevronUp, ExternalLink, Award } from 'lucide-react';

export default function SourcePanel({ sources = [] }) {
  const [expandedId, setExpandedId] = useState(null);

  if (!sources || sources.length === 0) {
    return (
      <div className="p-6 text-center text-slate-500 text-xs bg-slate-900/40 rounded-xl border border-slate-800">
        No source citations attached to this query response.
      </div>
    );
  }

  return (
    <div className="space-y-2 mt-3 pt-3 border-t border-slate-800/80">
      <div className="flex items-center justify-between text-xs font-semibold text-slate-400 mb-2">
        <span className="flex items-center gap-1.5">
          <BookOpen className="w-3.5 h-3.5 text-blue-400" />
          Regulatory Grounding Citations ({sources.length})
        </span>
        <span className="text-[11px] text-slate-500 font-normal">Ranked by Cross-Encoder</span>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {sources.map((src, idx) => {
          const isExpanded = expandedId === src.chunk_id;
          const scorePercent = Math.round((src.score || 0.8) * 100);

          return (
            <div
              key={idx}
              className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-xl p-3 transition-all text-xs"
            >
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedId(isExpanded ? null : src.chunk_id)}
              >
                <div className="flex items-center gap-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                    src.regulator === 'SEBI' ? 'bg-blue-500/20 text-blue-400' : 'bg-emerald-500/20 text-emerald-400'
                  }`}>
                    {src.regulator || 'REG'}
                  </span>
                  <span className="font-semibold text-slate-200">
                    {src.circular_code || src.document_name}
                  </span>
                  <span className="text-slate-400 text-[11px]">
                    (Page {src.page_number})
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {src.score !== undefined && (
                    <span className="flex items-center gap-1 text-[11px] text-amber-400/90 font-mono bg-amber-500/10 px-1.5 py-0.5 rounded">
                      <Award className="w-3 h-3" />
                      {src.score.toFixed(2)}
                    </span>
                  )}
                  {isExpanded ? (
                    <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  )}
                </div>
              </div>

              {/* Excerpt */}
              <p className="mt-2 text-slate-300 font-serif leading-relaxed text-[12px] bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60">
                {isExpanded ? (src.text || src.excerpt) : src.excerpt}
              </p>

              {isExpanded && (
                <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                  <span>Chunk ID: {src.chunk_id}</span>
                  <span>File: {src.document_name}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
