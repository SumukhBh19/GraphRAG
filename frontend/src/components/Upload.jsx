import React, { useState, useEffect } from 'react';
import { UploadCloud, FileText, CheckCircle2, Clock, AlertCircle, RefreshCw, Layers, Sparkles } from 'lucide-react';
import { fetchDocuments, uploadPDFs } from '../api';

export default function Upload({ onDataUpdated }) {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);

  const loadDocs = async () => {
    try {
      const res = await fetchDocuments();
      setDocuments(res.documents || []);
    } catch (err) {
      console.error('Failed to fetch documents', err);
    }
  };

  useEffect(() => {
    loadDocs();
    const interval = setInterval(loadDocs, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleFiles = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setStatusMsg({ type: 'info', text: `Uploading and analyzing ${fileList.length} regulatory PDF(s)...` });
    try {
      const res = await uploadPDFs(fileList);
      setStatusMsg({ type: 'success', text: res.message || 'Files uploaded and queued for processing!' });
      await loadDocs();
      if (onDataUpdated) onDataUpdated();
    } catch (err) {
      setStatusMsg({ type: 'error', text: err.response?.data?.detail || 'Upload failed. Please ensure file is a valid PDF.' });
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
          dragOver
            ? 'border-blue-500 bg-blue-500/10'
            : 'border-slate-700 hover:border-slate-500 bg-slate-900/40'
        }`}
      >
        <input
          type="file"
          id="file-upload-input"
          multiple
          accept=".pdf"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <label htmlFor="file-upload-input" className="cursor-pointer flex flex-col items-center">
          <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-3 shadow-lg shadow-blue-500/5">
            <UploadCloud className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-semibold text-slate-100 mb-1">
            Upload Regulatory Circulars & Directions
          </h3>
          <p className="text-sm text-slate-400 max-w-md mb-4">
            Drag and drop SEBI circulars or RBI Master Directions (PDF) here, or browse your local storage.
          </p>
          <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-800/80 px-3 py-1.5 rounded-full border border-slate-700/60">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Automatic text parsing, chunking, spaCy NER, and NetworkX Graph construction</span>
          </div>
        </label>

        {uploading && (
          <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-xs rounded-2xl flex items-center justify-center gap-3">
            <RefreshCw className="w-5 h-5 text-blue-400 animate-spin" />
            <span className="text-sm text-blue-300 font-medium">Ingesting and extracting knowledge graph...</span>
          </div>
        )}
      </div>

      {statusMsg && (
        <div
          className={`p-4 rounded-xl text-sm flex items-center justify-between border ${
            statusMsg.type === 'success'
              ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
              : statusMsg.type === 'error'
              ? 'bg-rose-950/40 border-rose-500/30 text-rose-300'
              : 'bg-blue-950/40 border-blue-500/30 text-blue-300'
          }`}
        >
          <span>{statusMsg.text}</span>
          <button onClick={() => setStatusMsg(null)} className="text-xs underline hover:opacity-80">
            Dismiss
          </button>
        </div>
      )}

      {/* Corpus Management Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-slate-400" />
            <h4 className="font-semibold text-slate-200">Indexed Regulatory Corpus</h4>
            <span className="bg-slate-800 text-slate-300 text-xs px-2.5 py-0.5 rounded-full font-mono">
              {documents.length} Files
            </span>
          </div>
          <button
            onClick={loadDocs}
            className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>

        {documents.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm">
            No regulatory circulars uploaded yet. Upload PDFs above to begin building the knowledge graph.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60 max-h-96 overflow-y-auto">
            {documents.map((doc, idx) => (
              <div key={idx} className="p-4 px-6 flex items-center justify-between hover:bg-slate-800/30 transition-colors">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                    doc.regulator === 'SEBI' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  }`}>
                    {doc.regulator || 'DOC'}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-slate-200">{doc.file_name}</div>
                    <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                      {doc.circular_code && <span>Ref: {doc.circular_code}</span>}
                      {doc.circular_date && <span>• Date: {doc.circular_date}</span>}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-xs">
                  {doc.chunks_count > 0 && (
                    <div className="flex items-center gap-1 text-slate-400">
                      <Layers className="w-3.5 h-3.5 text-indigo-400" />
                      <span>{doc.chunks_count} chunks</span>
                    </div>
                  )}
                  {doc.nodes_extracted !== undefined && (
                    <span className="text-slate-400">
                      {doc.nodes_extracted} nodes / {doc.edges_extracted || 0} edges
                    </span>
                  )}
                  <span className={`px-2.5 py-1 rounded-full font-medium flex items-center gap-1 ${
                    doc.status === 'ready'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : doc.status === 'processing'
                      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse'
                      : 'bg-slate-800 text-slate-400'
                  }`}>
                    {doc.status === 'ready' ? <CheckCircle2 className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                    {doc.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
