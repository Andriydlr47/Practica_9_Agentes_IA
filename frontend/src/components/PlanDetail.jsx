import {
  X, MapPin, Calendar, Thermometer, Wind, StickyNote, Mountain,
} from 'lucide-react';

export default function PlanDetail({ plan, onClose }) {
  if (!plan) return null;

  return (
    <div className="detail-overlay" onClick={onClose}>
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        <div className="detail-header">
          <h2>
            <span>🧗</span>
            {plan.nombre_plan}
          </h2>
          <button className="btn-close-detail" onClick={onClose} title="Cerrar">
            <X size={18} />
          </button>
        </div>

        <div className="detail-body">
          <div className="detail-grid">
            <div className="detail-item">
              <div className="detail-item-label">Zona</div>
              <div className="detail-item-value">
                <MapPin size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                {plan.zona_principal || '—'}
              </div>
            </div>
            <div className="detail-item">
              <div className="detail-item-label">Fecha</div>
              <div className="detail-item-value">
                <Calendar size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                {plan.fecha || '—'}
              </div>
            </div>
            <div className="detail-item">
              <div className="detail-item-label">Clima</div>
              <div className="detail-item-value">
                ☁️ {plan.clima || '—'}
              </div>
            </div>
            <div className="detail-item">
              <div className="detail-item-label">Temperatura</div>
              <div className="detail-item-value">
                <Thermometer size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                {plan.temperatura != null ? `${plan.temperatura}°C` : '—'}
              </div>
            </div>
            <div className="detail-item">
              <div className="detail-item-label">Viento</div>
              <div className="detail-item-value">
                <Wind size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                {plan.viento != null ? `${plan.viento} m/s` : '—'}
              </div>
            </div>
            <div className="detail-item">
              <div className="detail-item-label">Dificultad</div>
              <div className="detail-item-value">
                <Mountain size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                {plan.dificultad_rango || '—'}
              </div>
            </div>
            {plan.lat != null && (
              <div className="detail-item">
                <div className="detail-item-label">Coordenadas</div>
                <div className="detail-item-value" style={{ fontSize: '0.8rem' }}>
                  📍 {plan.lat?.toFixed(4)}, {plan.lon?.toFixed(4)}
                </div>
              </div>
            )}
            {plan.notas && (
              <div className="detail-item">
                <div className="detail-item-label">Notas</div>
                <div className="detail-item-value" style={{ fontSize: '0.8rem' }}>
                  <StickyNote size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                  {plan.notas}
                </div>
              </div>
            )}
          </div>

          {plan.vias && plan.vias.length > 0 && (
            <>
              <div className="detail-vias-title">
                📌 Vías del Plan ({plan.vias.length})
              </div>
              {plan.vias.map((via) => (
                <div key={via.id} className="detail-via-card">
                  <div>
                    <div className="detail-via-name">{via.nombre_via}</div>
                    <div className="detail-via-meta">
                      {via.sector && <span>📍 {via.sector}</span>}
                      {via.zona && <span>🏔️ {via.zona}</span>}
                      {via.lat != null && (
                        <span>🗺️ {via.lat?.toFixed(3)}, {via.lon?.toFixed(3)}</span>
                      )}
                    </div>
                  </div>
                  {via.dificultad && (
                    <span className="badge badge-difficulty">{via.dificultad}</span>
                  )}
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
