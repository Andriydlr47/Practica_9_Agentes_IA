import { useState, useEffect, useCallback } from 'react';
import { Map, MessageSquare, Mountain } from 'lucide-react';
import PlansSidebar from './components/PlansSidebar';
import MapView from './components/MapView';
import ChatPanel from './components/ChatPanel';
import PlanDetail from './components/PlanDetail';
import { fetchPlanes, fetchPlanDetalle, deletePlan } from './api';

export default function App() {
  const [planes, setPlanes] = useState([]);
  const [selectedPlanId, setSelectedPlanId] = useState(null);
  const [detailPlan, setDetailPlan] = useState(null);
  const [mobileView, setMobileView] = useState('map'); // 'plans' | 'map' | 'chat'
  const [planToDelete, setPlanToDelete] = useState(null);

  const loadPlanes = useCallback(async () => {
    try {
      const data = await fetchPlanes();
      setPlanes(data);
    } catch (err) {
      console.error('Error cargando planes:', err);
    }
  }, []);

  useEffect(() => {
    loadPlanes();
  }, [loadPlanes]);

  const handleSelectPlan = async (planId) => {
    setSelectedPlanId(planId);
    setMobileView('map');
  };

  const handleViewDetail = async (planId) => {
    try {
      const detail = await fetchPlanDetalle(planId);
      setDetailPlan(detail);
    } catch (err) {
      console.error('Error cargando detalle:', err);
    }
  };

  const handleDeletePlan = (planId) => {
    setPlanToDelete(planId);
  };

  const confirmDelete = async () => {
    if (!planToDelete) return;
    try {
      await deletePlan(planToDelete);
      if (selectedPlanId === planToDelete) setSelectedPlanId(null);
      if (detailPlan?.id === planToDelete) setDetailPlan(null);
      loadPlanes();
    } catch (err) {
      console.error('Error eliminando plan:', err);
    } finally {
      setPlanToDelete(null);
    }
  };

  const selectedPlanData = planes.find((p) => p.id === selectedPlanId) || null;

  return (
    <>
      {/* Header */}
      <header className="app-header">
        <div className="logo">
          <div className="logo-icon">🪨</div>
          <span>RockBot Planner</span>
        </div>
        <div className="header-stats">
          <div className="header-stat">
            <div className="dot" />
            Servidor conectado
          </div>
          <div className="header-stat">
            📌 {planes.length} planes
          </div>
        </div>
      </header>

      {/* Mobile Navigation */}
      <nav className="mobile-nav">
        <button
          className={mobileView === 'plans' ? 'active' : ''}
          onClick={() => setMobileView('plans')}
        >
          <Mountain size={14} /> Planes
        </button>
        <button
          className={mobileView === 'map' ? 'active' : ''}
          onClick={() => setMobileView('map')}
        >
          <Map size={14} /> Mapa
        </button>
        <button
          className={mobileView === 'chat' ? 'active' : ''}
          onClick={() => setMobileView('chat')}
        >
          <MessageSquare size={14} /> Chat
        </button>
      </nav>

      {/* Main Layout: Chat (left) → Map (center) → Plans (right) */}
      <div className="app-layout">
        <ChatPanel
          onPlanCreated={loadPlanes}
          className={mobileView === 'chat' ? 'mobile-visible' : ''}
        />

        <MapView
          planes={planes}
          selectedPlan={selectedPlanData}
          onViewDetail={handleViewDetail}
          className={mobileView === 'map' ? 'mobile-visible' : ''}
        />

        <PlansSidebar
          planes={planes}
          selectedPlanId={selectedPlanId}
          onSelectPlan={(id) => {
            handleSelectPlan(id);
            handleViewDetail(id);
          }}
          onDeletePlan={handleDeletePlan}
          className={mobileView === 'plans' ? 'mobile-visible' : ''}
        />
      </div>

      {/* Detail Modal */}
      {detailPlan && (
        <PlanDetail plan={detailPlan} onClose={() => setDetailPlan(null)} />
      )}

      {/* Confirm Delete Modal */}
      {planToDelete && (
        <div className="detail-overlay" onClick={() => setPlanToDelete(null)} style={{ zIndex: 10000 }}>
          <div className="detail-panel" style={{ maxWidth: '400px' }} onClick={(e) => e.stopPropagation()}>
            <div className="detail-header">
              <h2 style={{ fontSize: '1.1rem' }}>⚠️ Confirmar borrado</h2>
            </div>
            <div className="detail-body">
              <p style={{ marginBottom: '20px', color: 'var(--text-secondary)' }}>
                ¿Estás seguro de que deseas eliminar este plan? Esta acción no se puede deshacer.
              </p>
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  style={{
                    padding: '8px 16px', background: 'var(--bg-glass)', border: '1px solid var(--border-glass)',
                    borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)', cursor: 'pointer'
                  }}
                  onClick={() => setPlanToDelete(null)}
                >
                  Cancelar
                </button>
                <button
                  style={{
                    padding: '8px 16px', background: 'rgba(207, 92, 92, 0.15)', border: '1px solid rgba(207, 92, 92, 0.3)',
                    borderRadius: 'var(--radius-sm)', color: 'var(--accent-rose)', cursor: 'pointer'
                  }}
                  onClick={confirmDelete}
                >
                  Eliminar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
