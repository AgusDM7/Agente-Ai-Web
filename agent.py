from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from storage import save_note, read_note as storage_read_note

load_dotenv()


# -------- Tool: write note --------
@tool
def write_note(filepath: str, content: str) -> str:
    """
    Guarda una nota en Vercel Blob storage.
    """

    try:
        save_note(filepath, content)

        return f"Note '{filepath}' saved successfully."

    except Exception as e:
        return f"Error writing note: {str(e)}"


# -------- Tool: read note --------
@tool
def read_note(filepath: str) -> str:
    """
    Lee una nota almacenada en Vercel Blob.
    """

    try:
        content = storage_read_note(filepath)

        if content is None:
            return f"Note '{filepath}' not found."

        return f"Contents of '{filepath}':\n{content}"

    except Exception as e:
        return f"Error reading note: {str(e)}"


TOOLS = [read_note, write_note]


SYSTEM_MESSAGE = (
    "You are a helpful note-taking assistant. "
    "You can read and write notes for the user. "
    "Use the tools when necessary."
)


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=300)


# Creación del agente
agent = create_react_agent(llm, TOOLS, prompt=SYSTEM_MESSAGE)


def run_agent(user_input: str) -> str:
    """
    Ejecuta el agente con el prompt del usuario.
    """

    try:

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config={"recursion_limit": 10},
        )

        return result["messages"][-1].content

    except Exception as e:
        return f"Error: {str(e)}"
