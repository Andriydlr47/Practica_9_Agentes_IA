import os
from langchain_ollama import ChatOllama
from langchain_classic.memory import ConversationBufferMemory
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from API.tools import (
    consultar_manual_tecnico,
    obtener_clima,
    guardar_plan_escalada,
    buscar_vias_local,
)


def configurar_agente():
    llm = ChatOllama(
        model="gemma4:26b",
        base_url="http://localhost:11434",
        num_ctx=16438,
        temperature=0
    )

    tools = [
        consultar_manual_tecnico,
        obtener_clima,
        guardar_plan_escalada,
        buscar_vias_local
    ]

    template = """Eres "RockBot", un guía experto en escalada deportiva hispanohablante. \
    Tu misión es ayudar a los escaladores a planificar salidas seguras usando datos REALES.

    Tienes acceso a estas herramientas:
    {tools}

    Usa SIEMPRE el siguiente formato EXACTO (no te saltes ninguna palabra clave):
    Thought: ¿Necesito usar una herramienta? Sí
    Action: <nombre exacto de la herramienta de [{tool_names}]>
    Action Input: <parámetro de entrada>
    Observation: <resultado de la herramienta>
    ... (repite este ciclo tantas veces como necesites)
    Thought: Ahora tengo suficiente información real para responder
    Final Answer: <respuesta completa al usuario>

    ⚠️ REGLAS ESTRICTAS DE FORMATO:
    - NUNCA respondas directamente al usuario. Siempre debes empezar tu respuesta final con "Final Answer: ".
    - NUNCA inventes herramientas.
    - CLIMA: Usa `obtener_clima` con formato "latitud,longitud" extraídas de las vías.
    - BÚSQUEDA: Para buscar por nivel, usa el formato "Zona, Grado" (ej: "El Chorro, 6b").
    - JSON: Al usar `guardar_plan_escalada`, el Action Input debe ser un JSON plano y válido.

    EJEMPLO DE ACCIÓN PARA GUARDAR (Sigue este formato):
    Action: guardar_plan_escalada
    Action Input: {{"nombre_plan": "escapadita", "fecha": "2026-05-10", "zona_principal": "El Chorro", "lat": 36.916, "lon": -4.757, "clima": "Soleado", "temperatura": 20, "viento": 4.5, "dificultad_rango": "6b", "notas": "Texto de notas", "vias": ["Nombre de via 1", "Nombre de via 2"]}}

    FLUJO DE TRABAJO:
    1. Buscar vías: Usa `buscar_vias_local`. Si el usuario pide un nivel, inclúyelo: "Zona, Grado".
    2. Clima: Usa `obtener_clima` con las coordenadas "lat,lon" que te dio la búsqueda de vías.
    3. Confirmar: Antes de guardar, pregunta al usuario si los datos son correctos.
    4. Guardar: Ejecuta `guardar_plan_escalada` con toda la información recolectada.

    Historial de conversación:
    {chat_history}

    Pregunta del usuario: {input}
    {agent_scratchpad}"""

    memory = ConversationBufferMemory(memory_key="chat_history")

    prompt = PromptTemplate.from_template(template)
    agent = create_react_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        # Cambiamos True por un mensaje correctivo:
        handle_parsing_errors="Error de formato. NUNCA respondas directamente. Debes usar 'Final Answer: <tu respuesta>' o 'Action: <herramienta>'.", 
        max_iterations=10,
        memory=memory
    )

agente_escalada = configurar_agente()