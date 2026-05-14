import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_IMPL"] = "None"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from API.agent import agente_escalada
from API.database import (
    inicializar_db,
    obtener_todos_los_planes,
    obtener_plan_detalle,
    eliminar_plan,
)

# Asegurar que la BD existe al arrancar
inicializar_db()

app = FastAPI(
    title="Guía de Escalada Inteligente API",
    description="API para el agente IA de escalada deportiva con soporte de mapas y planificación.",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modelos
class ChatRequest(BaseModel):
    message: str


# Endpoints

@app.get("/", tags=["General"])
def read_root():
    return {"status": "Servidor de Escalada Online", "version": "2.0"}


@app.get("/health", tags=["General"])
def health():
    return {"status": "ok"}


@app.post("/chat", tags=["Agente"])
async def chat_endpoint(request: ChatRequest):
    """Envía un mensaje al agente de escalada y devuelve su respuesta."""
    try:
        # Ejecutamos el agente
        response = agente_escalada.invoke({"input": request.message})
        
        # Si todo va bien, devolvemos la respuesta de la IA
        return {"response": response["output"]}
        
    except Exception as e:
        # Imprimimos el error real en la consola para depurar
        print(f"⚠️ Error detectado en el agente: {e}")
        
        # Verificamos si es un error de formato (Parsing)
        # Esto ocurre cuando el modelo olvida poner "Final Answer:"
        error_str = str(e)
        if "Could not parse LLM output" in error_str:
            # Intentamos extraer lo que el modelo escribió antes de fallar
            # A veces el texto útil está dentro del error
            intentar_recuperar = error_str.split("`")[-2] if "`" in error_str else "Me he liado un poco con el formato, pero casi lo tengo. ¿Podrías repetirme la última instrucción?"
            return {"response": intentar_recuperar}
        
        # Si es otro tipo de error, devolvemos un mensaje controlado en lugar de un 500
        return {
            "response": "Lo siento, he tenido un problema técnico interno. ¿Podemos intentarlo de nuevo?"
        }


@app.get("/planes", tags=["Planes"])
def listar_planes():
    """Lista todos los planes de escalada guardados (con número de vías)."""
    try:
        planes = obtener_todos_los_planes()
        return {"planes": planes, "total": len(planes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/planes/{plan_id}", tags=["Planes"])
def detalle_plan(plan_id: int):
    """Devuelve el detalle completo de un plan, incluyendo todas sus vías."""
    plan = obtener_plan_detalle(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan con id={plan_id} no encontrado.")
    return plan


@app.delete("/planes/{plan_id}", tags=["Planes"])
def borrar_plan(plan_id: int):
    """Elimina un plan de escalada y todas sus vías asociadas."""
    eliminado = eliminar_plan(plan_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail=f"Plan con id={plan_id} no encontrado.")
    return {"message": f"Plan {plan_id} eliminado correctamente."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)