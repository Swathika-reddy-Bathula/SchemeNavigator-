const BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

async function parseResponse(res, fallbackMessage) {
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || fallbackMessage);
  }
  return data;
}

// Start the pipeline
async function startPipeline(userQuery) {
  const res = await fetch(`${BASE_URL}/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_query: userQuery })
  });

  return parseResponse(res, 'Pipeline start failed');
}

// Continue the pipeline with chat memory
async function continuePipeline(userQuery, userId) {
  const res = await fetch(`${BASE_URL}/continue`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_query: userQuery,
      user_id: userId
    })
  });
  return parseResponse(res, 'Pipeline continuation failed');
}

// Poll the pipeline status
async function getPipelineStatus() {
  const res = await fetch(`${BASE_URL}/status`);
  return parseResponse(res, 'Status fetch failed');
}

async function listHistory() {
  const res = await fetch(`${BASE_URL}/history`);
  return parseResponse(res, 'History fetch failed');
}

async function getHistory(userId) {
  const res = await fetch(`${BASE_URL}/history/${userId}`);
  return parseResponse(res, 'Conversation fetch failed');
}

async function updateHistory(userId, title) {
  const res = await fetch(`${BASE_URL}/history/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  return parseResponse(res, 'Conversation update failed');
}

async function deleteHistory(userId) {
  const res = await fetch(`${BASE_URL}/history/${userId}`, {
    method: 'DELETE',
  });
  return parseResponse(res, 'Conversation delete failed');
}

export default {
  startPipeline,
  continuePipeline,
  getPipelineStatus,
  listHistory,
  getHistory,
  updateHistory,
  deleteHistory,
};
