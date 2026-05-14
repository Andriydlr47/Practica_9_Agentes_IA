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
        num_ctx=32768,
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

    Usa SIEMPRE el siguiente formato EXACTO:
    Thought: ¿Necesito usar una herramienta? Sí
    Action: <nombre exacto de la herramienta de [{tool_names}]>
    Action Input: <parámetro de entrada>
    Observation: <resultado de la herramienta>
    ... (repite este ciclo)
    Thought: Ahora tengo suficiente información real para responder
    Final Answer: <respuesta completa al usuario>

    REGLAS DE BÚSQUEDA GEOGRÁFICA (JERARQUÍA):
    Al buscar vías con `buscar_vias_local`, sigue este orden de prioridad:
    1. **Comunidad Autónoma:** Si el usuario menciona una región (ej: Aragón, Andalucía, Madrid, Cataluña), busca primero por ese nombre, ten en cuenta que están guardados en ingles pero tu tienes que mostrarlos en español.
    2. **Ciudad/Provincia:** Si no hay resultados o pide algo más específico, busca por ciudad (ej: Huesca, Málaga).
    3. **Zona/Sector:** Solo busca por nombre de sector (ej: "El chorro") si el usuario es muy específico o si las búsquedas anteriores fallaron.
    
    *Nota: Evita confundir sectores que contienen el nombre de una región con la región misma. Si buscas "Aragón", prioriza resultados en la Comunidad Autónoma de Aragón.*

    REGLAS DE FORMATO:
    - NUNCA respondas directamente sin usar "Final Answer: ".
    - CLIMA: Usa `obtener_clima` con formato "lat,lon" (extraídas de las vías encontradas).
    - BÚSQUEDA: Formato "Lugar, Grado". Ejemplo: "Aragón, 5".
    - JSON: `guardar_plan_escalada` requiere un JSON plano y válido.

    FLUJO DE TRABAJO:
    1. Buscar vías siguiendo la jerarquía geográfica.
    2. Obtener Clima de la ubicación real de esas vías.
    3. Confirmar con el usuario y guardar.

    Historial:
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
        handle_parsing_errors="Error de formato. NUNCA respondas directamente. Debes usar 'Final Answer: <tu respuesta>' o 'Action: <herramienta>'.", 
        max_iterations=10,
        memory=memory
    )

agente_escalada = configurar_agente()