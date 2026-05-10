import { MapPin, Calendar, Thermometer, Wind, Mountain, Trash2 } from 'lucide-react';

export default function PlansSidebar({
  planes,
  selectedPlanId,
  onSelectPlan,
  onDeletePlan,
  className,
}) {
  return (
    <div className={`sidebar ${className || ''}`}>
      <div className="sidebar-header">
        <h2>
          <Mountain size={16} />
          Planes de Escalada
        </h2>
        {planes.length > 0 && (
          <span className="count-badge">{planes.length}</span>
        )}
      </div>

      <div className="plans-list">
        {planes.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🗺️</div>
            <h3>Sin planes aún</h3>
            <p>Chatea con RockBot para crear tu primer plan de escalada</p>
          </div>
        ) : (
          planes.map((plan) => (
            <div
              key={plan.id}
              className={`plan-card ${selectedPlanId === plan.id ? 'active' : ''}`}
              onClick={() => onSelectPlan(plan.id)}
            >
              <div className="plan-card-name">
                <span>🧗</span>
                {plan.nombre_plan}
              </div>
              <div className="plan-card-meta">
                <span>
                  <MapPin size={12} />
                  {plan.zona_principal}
                </span>
                <span>
                  <Calendar size={12} />
                  {plan.fecha}
                </span>
                {plan.temperatura != null && (
                  <span>
                    <Thermometer size={12} />
                    {plan.temperatura}°C
                  </span>
                )}
                {plan.viento != null && (
                  <span>
                    <Wind size={12} />
                    {plan.viento} m/s
                  </span>
                )}
                {plan.num_vias > 0 && (
                  <span>📌 {plan.num_vias} vías</span>
                )}
              </div>
              <div className="plan-card-actions">
                <button
                  className="btn-delete"
                  title="Eliminar plan"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeletePlan(plan.id);
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
