const API_BASE = 'http://localhost:8000';

export async function fetchPlanes() {
  const res = await fetch(`${API_BASE}/planes`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Error al obtener planes');
  const data = await res.json();
  return data.planes || [];
}

export async function fetchPlanDetalle(planId) {
  const res = await fetch(`${API_BASE}/planes/${planId}`);
  if (!res.ok) throw new Error('Plan no encontrado');
  return res.json();
}

export async function deletePlan(planId) {
  const res = await fetch(`${API_BASE}/planes/${planId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Error al eliminar plan');
  return res.json();
}

export async function sendChatMessage(message) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error('Error en el chat');
  const data = await res.json();
  return data.response;
}
