import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "escalada.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    # ACTIVAR CLAVES FORÁNEAS (Importante para el ON DELETE CASCADE)
    conn.execute("PRAGMA foreign_keys = ON;") 
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    """Crea las tablas si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── Tabla principal de planes de escalada ─────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS planes_escalada (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_plan     TEXT    NOT NULL DEFAULT 'Mi Plan',
            fecha           TEXT    NOT NULL,
            zona_principal  TEXT    NOT NULL,
            lat             REAL,
            lon             REAL,
            clima           TEXT    DEFAULT '',
            temperatura     REAL,
            viento          REAL,
            dificultad_rango TEXT   DEFAULT '',
            notas           TEXT    DEFAULT '',
            created_at      TEXT    DEFAULT (datetime('now'))
        )
    ''')

    # ── Tabla de vías incluidas en cada plan ──────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vias_plan (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id         INTEGER NOT NULL REFERENCES planes_escalada(id) ON DELETE CASCADE,
            nombre_via      TEXT    NOT NULL,
            zona            TEXT    DEFAULT '',
            sector          TEXT    DEFAULT '',
            dificultad      TEXT    DEFAULT '',
            longitud_m      REAL,
            num_chapas      INTEGER,
            lat             REAL,
            lon             REAL,
            advertencias    TEXT    DEFAULT '',
            fotos_urls      TEXT    DEFAULT '',
            thecrag_url     TEXT    DEFAULT ''
        )
    ''')

    conn.commit()
    conn.close()
    print(f"✅ Base de datos inicializada en: {DB_PATH}")


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
    cursor.execute("DELETE FROM planes_escalada WHERE id = ?", (plan_id,))
    eliminado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return eliminado


if __name__ == "__main__":
    inicializar_db()