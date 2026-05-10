import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Calendar, Thermometer, Wind, Eye } from 'lucide-react';

// Fix default marker icon issue in Leaflet + bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

function createClimbIcon() {
  return L.divIcon({
    className: 'custom-marker',
    html: '<div class="marker-pin"><span>🧗</span></div>',
    iconSize: [40, 50],
    iconAnchor: [20, 50],
    popupAnchor: [0, -48],
  });
}

function FlyToSelected({ plan }) {
  const map = useMap();
  useEffect(() => {
    if (plan?.lat && plan?.lon) {
      map.flyTo([plan.lat, plan.lon], 10, { duration: 1.5 });
    }
  }, [plan, map]);
  return null;
}

export default function MapView({ planes, selectedPlan, onViewDetail, className }) {
  const validPlanes = planes.filter((p) => p.lat != null && p.lon != null);

  return (
    <div className={`map-container ${className || ''}`}>
      {validPlanes.length === 0 && planes.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🌍</div>
          <h3>Mapa de planes</h3>
          <p>Los planes con coordenadas aparecerán aquí</p>
        </div>
      ) : (
        <MapContainer
          center={[40.0, -3.7]}
          zoom={5}
          style={{ width: '100%', height: '100%' }}
          zoomControl={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          <FlyToSelected plan={selectedPlan} />
          {validPlanes.map((plan) => (
            <Marker
              key={plan.id}
              position={[plan.lat, plan.lon]}
              icon={createClimbIcon()}
            >
              <Popup maxWidth={300} minWidth={260}>
                <div className="popup-content">
                  <h3>🧗 {plan.nombre_plan}</h3>
                  <div className="popup-detail">
                    <MapPin size={13} /> {plan.zona_principal}
                  </div>
                  <div className="popup-detail">
                    <Calendar size={13} /> {plan.fecha}
                  </div>
                  {plan.clima && (
                    <div className="popup-detail">
                      ☁️ {plan.clima}
                    </div>
                  )}
                  {plan.temperatura != null && (
                    <div className="popup-detail">
                      <Thermometer size={13} /> {plan.temperatura}°C
                    </div>
                  )}
                  {plan.viento != null && (
                    <div className="popup-detail">
                      <Wind size={13} /> {plan.viento} m/s
                    </div>
                  )}
                  {plan.dificultad_rango && (
                    <div className="popup-detail">
                      💪 Dificultad: {plan.dificultad_rango}
                    </div>
                  )}
                  {plan.num_vias > 0 && (
                    <div className="popup-vias">
                      <h4>📌 {plan.num_vias} vías en este plan</h4>
                    </div>
                  )}
                  <button
                    className="popup-btn"
                    onClick={() => onViewDetail(plan.id)}
                  >
                    <Eye size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                    Ver detalle completo
                  </button>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      )}
    </div>
  );
}
