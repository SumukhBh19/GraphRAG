import React, { useState, useEffect } from 'react';
import { Network, MessageSquare, UploadCloud, BarChart3, ShieldCheck, Database, Layers, Sparkles, BookOpen } from 'lucide-react';
import Chat from './components/Chat';
import GraphExplorer from './components/GraphExplorer';
import Upload from './components/Upload';
import EvaluationDashboard from './components/EvaluationDashboard';
import { fetchPing, fetchGraphStats } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('split'); // 'split', 'graph', 'upload', 'evaluation'
  const [activeSubgraph, setActiveSubgraph] = useState(null);
  const [backendStatus, setBackendStatus] = useState('connecting');
  const [stats, setStats] = useState({ nodes_count: 0, links_count: 0 });
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        await fetchPing();
        setBackendStatus('online');
      } catch (err) {
        setBackendStatus('offline');
      }
    };

    const loadStats = async () => {
      try {
        const s = await fetchGraphStats();
        setStats(s);
      } catch (err) {
        // silence
      }
    };

    checkBackend();
    loadStats();
    const interval = setInterval(() => {
      checkBackend();
      loadStats();
    }, 5000);
    return () => clearInterval(interval);
  }, [refreshKey]);

  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col selection:bg-blue-600 selection:text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Branding */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 p-0.5 shadow-lg shadow-blue-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Network className="w-5 h-5 text-blue-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight bg-gradient-to-r from-slate-100 via-slate-200 to-slate-400 bg-clip-text text-transparent">
                  GraphRAG
                </h1>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-full">
                  SEBI / RBI
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-0.5">Regulatory Intelligence & Multi-Hop Traversal</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center bg-slate-900/90 border border-slate-800 p-1 rounded-xl gap-1">
            <button
              onClick={() => setActiveTab('split')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === 'split'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Workspace</span>
            </button>

            <button
              onClick={() => setActiveTab('graph')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === 'graph'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              <span>Knowledge Graph</span>
            </button>

            <button
              onClick={() => setActiveTab('upload')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === 'upload'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Corpus Upload</span>
            </button>

            <button
              onClick={() => setActiveTab('evaluation')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === 'evaluation'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Benchmark</span>
            </button>
          </div>

          {/* System Status Indicators */}
          <div className="hidden lg:flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg text-slate-300">
              <Database className="w-3.5 h-3.5 text-indigo-400" />
              <span><b>{stats.nodes_count || 0}</b> nodes</span>
              <span className="text-slate-600">•</span>
              <span><b>{stats.links_count || 0}</b> relations</span>
            </div>

            <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg">
              <span className={`w-2 h-2 rounded-full ${
                backendStatus === 'online' ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
              }`} />
              <span className="text-slate-300 capitalize">{backendStatus}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col">
        {activeTab === 'split' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-[720px]">
            {/* Left Col: Q&A Chat */}
            <div className="lg:col-span-5 h-full flex flex-col">
              <Chat onSubgraphActive={(subgraph) => setActiveSubgraph(subgraph)} />
            </div>

            {/* Right Col: Knowledge Graph Visualizer */}
            <div className="lg:col-span-7 h-full flex flex-col">
              <GraphExplorer activeSubgraph={activeSubgraph} />
            </div>
          </div>
        )}

        {activeTab === 'graph' && (
          <div className="h-[800px] w-full">
            <GraphExplorer activeSubgraph={activeSubgraph} />
          </div>
        )}

        {activeTab === 'upload' && (
          <div className="max-w-4xl mx-auto w-full">
            <Upload onDataUpdated={() => setRefreshKey((k) => k + 1)} />
          </div>
        )}

        {activeTab === 'evaluation' && (
          <div className="max-w-5xl mx-auto w-full">
            <EvaluationDashboard />
          </div>
        )}
      </main>
    </div>
  );
}
