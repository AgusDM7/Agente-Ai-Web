from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
import os
import re
import httpx

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
_gh_headers = {
    "Accept": "application/vnd.github+json",
    **({"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}),
}


def _get(url: str, **kwargs) -> dict:
    """Shared HTTP GET helper with 10 s timeout."""
    with httpx.Client(timeout=10) as client:
        r = client.get(url, **kwargs)
    r.raise_for_status()
    return r.json()


# ── Tools ─────────────────────────────────────────────────────────────────────


@tool
def search_wikipedia(query: str) -> str:
    """Get a concise Wikipedia summary for any programming or CS concept."""
    try:
        # Codifica el query para usarlo en la URL
        d = _get( f"https://en.wikipedia.org/api/rest_v1/page/summary/{httpx.utils.quote(query)}")
        page_url = d.get("content_urls", {}).get("desktop", {}).get("page", "") # Extrae la URL de la versión desktop
        return f"**{d['title']}**\n\n{d.get('extract', 'No summary.')}\n\n{page_url}"
    
    except Exception as e:
        return f"Wikipedia error: {e}"


@tool
def search_github(query: str, language: str = "") -> str:
    """Search GitHub for top repositories by topic and optional programming language filter."""
    try:

        # Query con filtro de lenguaje opcional
        q = f"{query} language:{language}" if language else query

        # repos ordenados por estrellas 
        items = _get(
            "https://api.github.com/search/repositories",
            params={
                "q": q, 
                "sort": "stars", 
                "order": "desc", 
                "per_page": 5},
                
            headers=_gh_headers,

        ).get("items", [])

        if not items:
            return f"No repositories found for '{query}'."
        
        # Lista de 5 repos → itera y formatea cada uno (nombre, estrellas, descripción y URL)
        return "\n\n".join(
            f"• **{r['full_name']}** ⭐{r['stargazers_count']:,}\n"
            f"  {r.get('description') or 'No description'}\n"
            f"  {r['html_url']}"
            for r in items
        )
    
    except Exception as e:
        return f"GitHub error: {e}"


@tool
def search_stackoverflow(query: str) -> str:
    """Search Stack Overflow and return the best answered question with its top answer."""
    try:

        # Primera llamada: busca preguntas relevantes 
        items = _get(
            "https://api.stackexchange.com/2.3/search/advanced",

            # "filter": "!nNPvSNdWme" es un filtro custom de SO que incluye el campo is_answered
            params={
                "q": query,
                "site": "stackoverflow",
                "sort": "relevance",
                "order": "desc",
                "pagesize": 5,
                "filter": "!nNPvSNdWme",
            },

        ).get("items", [])
        
        if not items:
            return f"No Stack Overflow results found for '{query}'."

        # Elige la mejor pregunta respondida o la más relevante si no hay respuestas
        best = next((q for q in items if q.get("is_answered")), items[0])


        # Segunda llamada: obtiene el cuerpo de la respuesta más votada
        answers = _get(
            f"https://api.stackexchange.com/2.3/questions/{best['question_id']}/answers",
            params={
                "site": "stackoverflow",
                "sort": "votes",
                "order": "desc",
                "pagesize": 1,
                "filter": "withbody", # "filter": "withbody" para que la API incluya el HTML del cuerpo
            },

        ).get("items", [])

        # Elimina etiquetas HTML del cuerpo y limita a 2000 caracteres
        body = (
            re.sub(r"<[^>]+>", "", answers[0].get("body", ""))[:2000]
            if answers
            else "No answer body available."
        )
        return (
            f"**{best['title']}**\n{best['link']}\n"
            f"Tags: {', '.join(best.get('tags', []))}\n\n{body}"
        )
    except Exception as e:
        return f"Stack Overflow error: {e}"


# ── Agent ─────────────────────────────────────────────────────────────────────

SYSTEM_MESSAGE = (
    "You are a concise expert programming assistant. Use your tools to answer questions:\n"
    "- search_wikipedia: concepts, theory, data structures, algorithms\n"
    "- search_github: libraries, open-source projects, code examples\n"
    "- search_stackoverflow: errors, how-tos, debugging, best practices\n"
    "Always query tools before relying on training knowledge. Be brief and use markdown."
)


agent = create_react_agent(
    ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=500),
    [search_wikipedia, search_github, search_stackoverflow],
    prompt=SYSTEM_MESSAGE,
)



def run_agent(user_input: str) -> str:
    """Invoke the agent and return the final response string."""
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config={"recursion_limit": 10}, # máximo de pasos del ciclo ReAct
        )
        return result["messages"][-1].content # [-1] porque el agente puede generar varios mensajes internos; el último es la respuesta final
    except Exception as e:
        return f"Agent error: {e}"
