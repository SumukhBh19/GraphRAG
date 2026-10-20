import axios from 'axios';

const API_BASE = '/api';

export const fetchPing = async () => {
  const res = await axios.get('/ping');
  return res.data;
};

export const fetchGraph = async () => {
  const res = await axios.get(`${API_BASE}/graph`);
  return res.data;
};

export const fetchGraphStats = async () => {
  const res = await axios.get(`${API_BASE}/graph/stats`);
  return res.data;
};

export const searchGraph = async (q) => {
  const res = await axios.get(`${API_BASE}/graph/search`, { params: { q } });
  return res.data;
};

export const getNodeDetails = async (nodeId) => {
  const res = await axios.get(`${API_BASE}/graph/node/${encodeURIComponent(nodeId)}`);
  return res.data;
};

export const fetchDocuments = async () => {
  const res = await axios.get(`${API_BASE}/ingest/documents`);
  return res.data;
};

export const uploadPDFs = async (files) => {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }
  const res = await axios.post(`${API_BASE}/ingest/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return res.data;
};

export const querySystem = async (query, mode = 'hybrid', topK = 6) => {
  const res = await axios.post(`${API_BASE}/query`, {
    query,
    mode,
    top_k: topK
  });
  return res.data;
};

export const runBenchmark = async (limit = 10) => {
  const res = await axios.post(`${API_BASE}/evaluation/benchmark`, null, {
    params: { limit }
  });
  return res.data;
};
