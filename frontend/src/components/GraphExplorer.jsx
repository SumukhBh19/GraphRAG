import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Search, ZoomIn, ZoomOut, Maximize2, Layers, X, Info, Sparkles } from 'lucide-react';
import { fetchGraph, getNodeDetails } from '../api';

const TYPE_COLORS = {
  Regulation: '#3b82f6',
  Circular:   '#6366f1',
  Entity:     '#10b981',
  Instrument: '#f59e0b',
  Date:       '#94a3b8',
  Section:    '#8b5cf6',
  Obligation: '#ef4444',
  Default:    '#06b6d4'
};

// Neon edge colours per relationship type
const EDGE_COLORS = {
  ISSUED_BY:      '#22d3ee',   // cyan
  GOVERNS:        '#a78bfa',   // violet
  APPLIES_TO:     '#34d399',   // emerald
  EFFECTIVE_FROM: '#fb923c',   // orange
  MANDATES:       '#f472b6',   // pink
  SUPERSEDES:     '#facc15',   // yellow
  AMENDS:         '#f87171',   // rose
  REFERS_TO:      '#60a5fa',   // light-blue
  DEFAULT:        '#475569',   // slate (fallback)
};

// Truncate a string to maxLen, appending '…' if cut
function truncate(str, maxLen = 18) {
  if (!str) return '';
  return str.length > maxLen ? str.slice(0, maxLen - 1) + '…' : str;
}

// Format entity ID into a human-readable short label
function shortLabel(node) {
  const raw = node.name || node.id || '';
  // Prefer names that aren't just the ID repeated
  const label = raw
    .replace(/_/g, ' ')                        // underscores → spaces
    .replace(/\b\w/g, c => c.toUpperCase());    // Title Case
  return truncate(label, 22);
}

export default function GraphExplorer({ activeSubgraph, onNodeSelect }) {
  const fgRef = useRef();
  const containerRef = useRef();
  const [graphData, setGraphData]       = useState({ nodes: [], links: [] });
  const [dimensions, setDimensions]     = useState({ width: 800, height: 600 });
  const [searchQuery, setSearchQuery]   = useState('');
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeDetails, setNodeDetails]   = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [filterType, setFilterType]     = useState('ALL');

  // ------------------------------------------------------------------
  // Load graph
  // ------------------------------------------------------------------
  const loadGraph = async () => {
    try {
      const data = await fetchGraph();
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load knowledge graph', err);
    }
  };

  useEffect(() => { loadGraph(); }, []);

  // ------------------------------------------------------------------
  // Responsive canvas
  // ------------------------------------------------------------------
  useEffect(() => {
    const update = () => {
      if (containerRef.current) {
        setDimensions({
          width:  containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight || 620
        });
      }
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  // ------------------------------------------------------------------
  // Highlighted nodes from Q&A subgraph
  // ------------------------------------------------------------------
  const highlightedNodeIds = useMemo(() => {
    if (!activeSubgraph?.nodes) return new Set();
    return new Set(activeSubgraph.nodes.map(n => (typeof n === 'string' ? n : n.id)));
  }, [activeSubgraph]);

  // ------------------------------------------------------------------
  // Filtered data
  // ------------------------------------------------------------------
  const filteredData = useMemo(() => {
    if (filterType === 'ALL') return graphData;
    const nodes   = graphData.nodes.filter(n => n.type === filterType);
    const nodeIds = new Set(nodes.map(n => n.id));
    const links   = graphData.links.filter(l => {
      const s = typeof l.source === 'object' ? l.source.id : l.source;
      const t = typeof l.target === 'object' ? l.target.id : l.target;
      return nodeIds.has(s) && nodeIds.has(t);
    });
    return { nodes, links };
  }, [graphData, filterType]);

  // ------------------------------------------------------------------
  // Node click → inspector drawer
  // ------------------------------------------------------------------
  const handleNodeClick = useCallback(async (node) => {
    setSelectedNode(node);
    setLoadingDetails(true);
    if (onNodeSelect) onNodeSelect(node);
    try {
      const details = await getNodeDetails(node.id);
      setNodeDetails(details);
    } catch {
      setNodeDetails(node);
    } finally {
      setLoadingDetails(false);
    }
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 700);
      fgRef.current.zoom(2.8, 700);
    }
  }, [onNodeSelect]);

  // ------------------------------------------------------------------
  // Search
  // ------------------------------------------------------------------
  const handleSearch = (e) => {
    e.preventDefault();
    const q = searchQuery.toLowerCase().trim();
    if (!q) return;
    const match = graphData.nodes.find(
      n => n.id.toLowerCase().includes(q) || (n.name && n.name.toLowerCase().includes(q))
    );
    if (match) handleNodeClick(match);
  };

  // ------------------------------------------------------------------
  // Canvas node drawing — clear, spacious, readable
  // ------------------------------------------------------------------
  const drawNode = useCallback((node, ctx, globalScale) => {
    const isHighlighted = highlightedNodeIds.has(node.id);
    const isSelected    = selectedNode?.id === node.id;
    const baseColor     = TYPE_COLORS[node.type] || TYPE_COLORS.Default;

    // Radius: consistent base; slightly larger for key types
    const keyTypes = ['Circular', 'Regulation'];
    const baseR    = keyTypes.includes(node.type) ? 7 : 5;
    const radius   = isSelected ? baseR + 3 : isHighlighted ? baseR + 2 : baseR;

    // --- Outer glow ring (only for selected / highlighted, NOT hover) ---
    if (isHighlighted || isSelected) {
      const glowColor = isSelected
        ? 'rgba(244, 63, 94, 0.35)'
        : 'rgba(168, 85, 247, 0.35)';
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius + 5, 0, 2 * Math.PI);
      ctx.fillStyle = glowColor;
      ctx.fill();
    }

    // --- Node body ---
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
    ctx.fillStyle = isHighlighted ? '#c084fc' : baseColor;
    ctx.fill();

    // Border
    ctx.lineWidth  = isSelected ? 2 : 1;
    ctx.strokeStyle = isSelected ? '#fff' : isHighlighted ? '#fae8ff' : 'rgba(15,23,42,0.7)';
    ctx.stroke();

    // --- Label logic ---
    // Only show labels when zoomed in or explicitly selected / highlighted.
    // Never on bare hover — prevents label clutter on mouse-over.
    const showLabel = globalScale > 1.6 || isSelected || isHighlighted;
    if (!showLabel) return;

    const label    = shortLabel(node);
    const fontSize = Math.min(12, Math.max(7, 11 / globalScale));
    ctx.font       = `${fontSize}px "Inter", sans-serif`;

    // Pill background for readability
    const textW   = ctx.measureText(label).width;
    const padX    = 4;
    const padY    = 2;
    const rectX   = node.x - textW / 2 - padX;
    const rectY   = node.y + radius + 3;
    const rectH   = fontSize + padY * 2;

    ctx.fillStyle    = 'rgba(8, 12, 20, 0.75)';
    ctx.beginPath();
    ctx.roundRect(rectX, rectY, textW + padX * 2, rectH, 3);
    ctx.fill();

    // Text
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle    = isSelected ? '#fff' : isHighlighted ? '#e9d5ff' : '#cbd5e1';
    ctx.fillText(label, node.x, rectY + padY);
  }, [highlightedNodeIds, selectedNode]);

  // ------------------------------------------------------------------
  // Hit-area (larger than drawn node so it's easy to click)
  // ------------------------------------------------------------------
  const paintPointerArea = useCallback((node, color, ctx) => {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, 12, 0, 2 * Math.PI);
    ctx.fill();
  }, []);

  // ------------------------------------------------------------------
  // After engine stops, strengthen repulsion so nodes don't pile up
  // ------------------------------------------------------------------
  const handleEngineStop = useCallback(() => {
    if (!fgRef.current) return;
    fgRef.current.zoomToFit(600, 40);
  }, []);

  // Force configuration via d3 — called once the graph is rendered
  const handleEngineReady = useCallback(() => {
    if (!fgRef.current) return;
    const fg = fgRef.current;
    fg.d3Force('charge').strength(-280);          // stronger repulsion
    fg.d3Force('link').distance(70);              // longer link resting distance
    if (fg.d3Force('collision')) {
      fg.d3Force('collision').radius(22);         // stop nodes overlapping
    }
  }, []);

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  return (
    <div ref={containerRef} className="relative w-full h-full min-h-[620px] bg-[#080c14] rounded-2xl border border-slate-800/80 overflow-hidden flex flex-col">

      {/* ── Top control bar ── */}
      <div className="absolute top-3 left-3 right-3 z-10 flex flex-wrap items-center gap-2 pointer-events-none">

        {/* Search */}
        <form
          onSubmit={handleSearch}
          className="pointer-events-auto flex items-center bg-slate-900/90 backdrop-blur-md border border-slate-700/60 rounded-xl px-3 py-1.5 shadow-xl"
        >
          <Search className="w-3.5 h-3.5 text-slate-400 mr-2 shrink-0" />
          <input
            type="text"
            placeholder="Search entities, circulars…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="bg-transparent text-xs text-slate-100 placeholder-slate-500 focus:outline-none w-48"
          />
          {searchQuery && (
            <button type="button" onClick={() => setSearchQuery('')} className="ml-1 text-slate-400 hover:text-slate-200">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </form>

        {/* Type filter chips */}
        <div className="pointer-events-auto flex items-center gap-1 bg-slate-900/90 backdrop-blur-md border border-slate-700/60 rounded-xl p-1 shadow-xl text-xs overflow-x-auto">
          {['ALL', 'Regulation', 'Circular', 'Entity', 'Instrument', 'Obligation'].map(type => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-2.5 py-1 rounded-lg font-medium flex items-center gap-1.5 transition-all whitespace-nowrap ${
                filterType === type
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {type !== 'ALL' && (
                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: TYPE_COLORS[type] }} />
              )}
              {type}
            </button>
          ))}
        </div>

        {/* Zoom controls */}
        <div className="pointer-events-auto flex items-center gap-0.5 bg-slate-900/90 backdrop-blur-md border border-slate-700/60 rounded-xl p-1 shadow-xl ml-auto">
          <button
            onClick={() => fgRef.current?.zoom(fgRef.current.zoom() * 1.3, 350)}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            title="Zoom in"
          ><ZoomIn className="w-4 h-4" /></button>
          <button
            onClick={() => fgRef.current?.zoom(fgRef.current.zoom() / 1.3, 350)}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            title="Zoom out"
          ><ZoomOut className="w-4 h-4" /></button>
          <button
            onClick={() => fgRef.current?.zoomToFit(400, 30)}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            title="Fit view"
          ><Maximize2 className="w-4 h-4" /></button>
        </div>
      </div>

      {/* ── Force Graph canvas ── */}
      <div className="flex-1 w-full h-full">
        <ForceGraph2D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={filteredData}
          nodeCanvasObject={drawNode}
          nodePointerAreaPaint={paintPointerArea}
          onNodeClick={handleNodeClick}
          // Link appearance
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={1}
          linkColor={link => {
            const relType = link.type || link.label || 'DEFAULT';
            const base    = EDGE_COLORS[relType] || EDGE_COLORS.DEFAULT;
            const s = typeof link.source === 'object' ? link.source.id : link.source;
            const t = typeof link.target === 'object' ? link.target.id : link.target;
            const active  = highlightedNodeIds.has(s) && highlightedNodeIds.has(t);
            // Active edges: full neon; inactive edges: tinted but visible
            return active ? base : base + '55';  // 55 ≈ 33% opacity hex
          }}
          linkWidth={link => {
            const s = typeof link.source === 'object' ? link.source.id : link.source;
            const t = typeof link.target === 'object' ? link.target.id : link.target;
            return highlightedNodeIds.has(s) && highlightedNodeIds.has(t) ? 2.5 : 1.1;
          }}
          linkDirectionalParticles={2}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleColor={link => {
            const relType = link.type || link.label || 'DEFAULT';
            return EDGE_COLORS[relType] || EDGE_COLORS.DEFAULT;
          }}
          backgroundColor="#080c14"
          // Simulation
          cooldownTicks={180}
          d3AlphaDecay={0.018}
          d3VelocityDecay={0.45}
          onEngineStop={handleEngineStop}
          onEngineReady={handleEngineReady}
        />
      </div>

      {/* ── Legend (bottom-left) ── */}
      <div className="absolute bottom-4 left-4 z-10 flex gap-5 bg-slate-900/85 backdrop-blur-md border border-slate-800 rounded-xl px-3.5 py-3 shadow-xl pointer-events-none">
        {/* Node types */}
        <div className="flex flex-col gap-1.5">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Nodes</span>
          {Object.entries(TYPE_COLORS).filter(([t]) => t !== 'Default').map(([type, color]) => (
            <span key={type} className="flex items-center gap-2 text-[11px] text-slate-300">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
              {type}
            </span>
          ))}
        </div>
        {/* Edge relation types */}
        <div className="flex flex-col gap-1.5">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Relations</span>
          {Object.entries(EDGE_COLORS).filter(([t]) => t !== 'DEFAULT').map(([rel, color]) => (
            <span key={rel} className="flex items-center gap-2 text-[11px] text-slate-300">
              <span className="inline-block w-5 h-[2px] rounded shrink-0" style={{ backgroundColor: color, boxShadow: `0 0 5px ${color}` }} />
              {rel.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      </div>

      {/* ── Active subgraph banner ── */}
      {highlightedNodeIds.size > 0 && (
        <div className="absolute bottom-4 right-4 z-10 flex items-center gap-2 bg-purple-950/80 backdrop-blur-md border border-purple-500/40 text-purple-200 text-xs px-3.5 py-2 rounded-xl shadow-2xl">
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          <span><b>{highlightedNodeIds.size}</b> traversed entities highlighted</span>
        </div>
      )}

      {/* ── Node inspector drawer ── */}
      {selectedNode && (
        <div className="absolute top-0 right-0 bottom-0 w-72 bg-slate-900/95 backdrop-blur-xl border-l border-slate-800 p-5 shadow-2xl z-20 overflow-y-auto flex flex-col gap-4">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: TYPE_COLORS[selectedNode.type] || '#fff' }} />
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{selectedNode.type}</span>
            </div>
            <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Name + ID */}
          <div>
            <h3 className="text-sm font-bold text-slate-100 leading-snug mb-1">
              {selectedNode.name || selectedNode.id}
            </h3>
            <p className="text-[10px] text-slate-500 font-mono break-all">{selectedNode.id}</p>
          </div>

          {/* Source documents */}
          {selectedNode.source_documents?.length > 0 && (
            <div>
              <h5 className="text-[11px] font-semibold text-slate-400 mb-1.5 flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-blue-400" /> Source Documents
              </h5>
              <div className="space-y-1">
                {selectedNode.source_documents.map((doc, i) => (
                  <div key={i} className="text-[11px] bg-slate-800/60 border border-slate-700/50 rounded-lg px-2.5 py-1.5 text-slate-300">
                    {doc}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Connections */}
          {loadingDetails ? (
            <p className="text-xs text-slate-500 animate-pulse text-center py-4">Loading connections…</p>
          ) : nodeDetails?.neighbors?.length > 0 && (
            <div>
              <h5 className="text-[11px] font-semibold text-slate-400 mb-1.5 flex items-center gap-1">
                <Info className="w-3.5 h-3.5 text-emerald-400" /> Relations ({nodeDetails.neighbors.length})
              </h5>
              <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                {nodeDetails.neighbors.map((nbr, i) => (
                  <div key={i} className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-2.5 py-2 text-[11px]">
                    <div className="flex justify-between text-slate-500 mb-0.5">
                      <span className="font-semibold text-indigo-400">{nbr.relation}</span>
                      <span className="capitalize">{nbr.direction}</span>
                    </div>
                    <div className="text-slate-200 font-medium">{truncate(nbr.target_name, 30)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Focus button */}
          <button
            onClick={() => { fgRef.current?.centerAt(selectedNode.x, selectedNode.y, 600); fgRef.current?.zoom(3.2, 600); }}
            className="mt-auto py-2 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 rounded-xl text-xs font-medium text-blue-300 transition-colors"
          >
            Focus camera
          </button>
        </div>
      )}
    </div>
  );
}
