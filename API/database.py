import sqlite3
import os

# Ruta dinámica para la base de datos
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "escalada.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    # Activamos claves foráneas (Fundamental para que el ON DELETE CASCADE funcione)
    conn.execute("PRAGMA foreign_keys = ON;") 
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS planes_escalada (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_plan      TEXT    NOT NULL DEFAULT 'Mi Plan',
            fecha            TEXT    NOT NULL,
            zona_principal   TEXT    NOT NULL,
            comunidad_autonoma TEXT,
            ciudad           TEXT,
            lat              REAL,
            lon              REAL,
            clima            TEXT    DEFAULT '',
            temperatura      REAL,
            viento           REAL,
            dificultad_rango TEXT    DEFAULT '',
            notas            TEXT    DEFAULT '',
            created_at       TEXT    DEFAULT (datetime('now'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vias_plan (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id          INTEGER NOT NULL REFERENCES planes_escalada(id) ON DELETE CASCADE,
            nombre_via       TEXT    NOT NULL,
            zona             TEXT    DEFAULT '',
            sector           TEXT    DEFAULT '',
            dificultad       TEXT    DEFAULT '',
            lat              REAL,
            lon              REAL
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Base de datos inicializada en: {DB_PATH}")

# Insertar Plan Completo desde el Agente

def insertar_plan_completo(datos):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO planes_escalada (
                nombre_plan, fecha, zona_principal, comunidad_autonoma, ciudad, 
                lat, lon, clima, temperatura, viento, dificultad_rango, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datos.get('nombre_plan'),
            datos.get('fecha'),
            datos.get('zona_principal'),
            datos.get('comunidad_autonoma'),
            datos.get('ciudad'),
            datos.get('lat'),
            datos.get('lon'),
            datos.get('clima'),
            datos.get('temperatura'),
            datos.get('viento'),
            datos.get('dificultad_rango'),
            datos.get('notas') or datos.get('nota'),
        ))
        
        plan_id = cursor.lastrowid
        for via in datos.get('vias', []):
            cursor.execute("""
                INSERT INTO vias_plan (plan_id, nombre_via, zona, sector, dificultad, lat, lon)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                plan_id,
                via.get('nombre_via'),
                via.get('zona'),
                via.get('sector'),
                via.get('dificultad') or via.get('grado'),
                via.get('lat'),
                via.get('lon'),
            ))
        
        conn.commit()
        return f"Éxito: Plan guardado con ID {plan_id}."
    except Exception as e:
        conn.rollback()
        return f"Error: {str(e)}"
    finally:
        conn.close()

# FUNCIONES DE CONSULTA

def obtener_todos_los_planes():
    """Devuelve todos los planes con el número de vías de cada uno."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, COUNT(v.id) as num_vias
        FROM planes_escalada p
        LEFT JOIN vias_plan v ON v.plan_id = p.id
        GROUP BY p.id
        ORDER BY p.created_at DESC
    ''')
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def obtener_plan_detalle(plan_id: int):
    """Devuelve un plan completo con todas sus vías."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM planes_escalada WHERE id = ?", (plan_id,))
    plan = cursor.fetchone()
    if not plan:
        conn.close()
        return None

    plan_dict = dict(plan)

    cursor.execute("SELECT * FROM vias_plan WHERE plan_id = ?", (plan_id,))
    vias = [dict(row) for row in cursor.fetchall()]
    plan_dict["vias"] = vias

    conn.close()
    return plan_dict

def eliminar_plan(plan_id: int) -> bool:
    """Elimina un plan y sus vías asociadas (CASCADE)."""
    conn = get_connection()
    cursor = conn.cursor()
    # Gracias al ON DELETE CASCADE en la tabla vias_plan, 
    # al borrar el plan se borran sus vías automáticamente.
    cursor.execute("DELETE FROM planes_escalada WHERE id = ?", (plan_id,))
    eliminado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return eliminado

if __name__ == "__main__":
    inicializar_db()