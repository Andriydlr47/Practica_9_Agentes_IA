from langchain_ollama import ChatOllama
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from API.tools import (
    consultar_manual_tecnico,
    obtener_clima,
    buscar_en_8anu,
    guardar_plan_escalada,
)   


def configurar_agente():
    llm = ChatOllama(
        model="gemma4:26b",
        base_url="http://localhost:11434",
        num_ctx=32768,
        temperature=0,
        extra_body={
            "think": False
        }
    )

    tools = [
        consultar_manual_tecnico,
        obtener_clima,
        buscar_en_8anu,
        guardar_plan_escalada,
    ]

    template = """Eres "RockBot", un guía experto en escalada deportiva hispanohablante. \
        Tu misión es ayudar a los escaladores a planificar salidas seguras y disfruta bles, \
        dar consejos técnicos y recomendar vías adaptadas a su nivel.

        Tienes acceso a estas herramientas:
        {tools}

        Usa SIEMPRE el siguiente formato:
        Thought: ¿Necesito usar una herramienta? Sí/No
        Action: <nombre exacto de la herramienta de [{tool_names}]>
        Action Input: <parámetro de entrada>
        Observation: <resultado de la herramienta>
        ... (repite Thought/Action/Action Input/Observation tantas veces como necesites)
        Thought: Ahora tengo suficiente información para responder
        Final Answer: <respuesta completa al usuario>

        REGLAS:
        1. Para preguntas sobre nudos, técnicas, material o maniobras → usa `consultar_manual_tecnico`.
        2. Para preguntas sobre el tiempo o clima en una zona → usa `obtener_clima`.
        3. Si el usuario pregunta por una zona, sector o vía -> usa `buscar_en_8anu`. 
        - Esta herramienta devuelve datos reales de la base de datos mundial de 8a.nu.
        - Si recibes una tabla de sectores, preséntala al usuario y pregúntale cuál le interesa.
        - NO inventes grados ni nombres de vías si no aparecen en la 'Observation'.
        4. Cuando el usuario quiera guardar un plan de escalada → usa `guardar_plan_escalada` con un JSON completo.
        El JSON DEBE incluir:
        - nombre_plan, fecha, zona_principal, lat, lon, clima, temperatura, viento, dificultad_rango, notas
        - vias: lista con nombre_via, zona, sector, dificultad, longitud_m, num_chapas, lat, lon, advertencias, thecrag_url
        5. Responde SIEMPRE en español, de forma amable, clara y profesional.
        6. Cuando propongas un plan de escalada al usuario, incluye SIEMPRE: zona, fecha, vías recomendadas, \
        número de cintas necesarias, longitud total y consejo de seguridad.
        7. Antes de guardar un plan, muéstrale un resumen al usuario y pide confirmación.

        Pregunta del usuario: {input}
    {agent_scratchpad}"""

    prompt = PromptTemplate.from_template(template)
    agent = create_react_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=8,
    )


agente_escalada = configurar_agente()