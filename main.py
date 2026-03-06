from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from agent import run_agent
from storage import list_notes
import uvicorn
import time
from collections import defaultdict

app = FastAPI()

templates = Jinja2Templates(directory="templates")



# máximo tamaño del prompt
MAX_PROMPT_LENGTH = 300

# rate limit
MAX_REQUESTS_PER_MINUTE = 3
WINDOW_SECONDS = 60

# memoria simple para registrar requests por IP
request_log = defaultdict(list)




# -------- Request model --------
class AgentRequest(BaseModel):
    """Modelo de solicitud enviado desde el frontend."""
    prompt: str


# -------- Response model --------
class AgentResponse(BaseModel):
    """Modelo de respuesta del agente."""
    response: str


# -------- Home endpoint --------
@app.get("/")
async def home(request: Request):
    """
    Sirve la interfaz web principal.
    """
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


# -------- Agent endpoint --------
@app.post("/agent", response_model=AgentResponse)
async def invoke_agent(request: AgentRequest, http_request: Request):
    """
    Ejecuta el agente de IA con el prompt del usuario.
    Incluye protecciones para evitar abuso de API.
    """

    try:

        if not request.prompt.strip():
            raise HTTPException(
                status_code=400,
                detail="Prompt cannot be empty"
            )

    
        if len(request.prompt) > MAX_PROMPT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Prompt too long (max {MAX_PROMPT_LENGTH} characters)"
            )

    
        client_ip = http_request.client.host
        now = time.time()

        # eliminar requests viejas fuera de la ventana
        request_log[client_ip] = [
            t for t in request_log[client_ip]
            if now - t < WINDOW_SECONDS
        ]

        if len(request_log[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait before trying again."
            )

        # registrar request actual
        request_log[client_ip].append(now)


        result = run_agent(request.prompt)

        return AgentResponse(response=result)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error invoking agent: {str(e)}"
        )



# -------- Notes endpoint --------
@app.get("/notes")
async def get_notes():
    """
    Devuelve la lista de notas almacenadas en Vercel Blob.
    """

    try:

        notes = list_notes()

        return {"notes": notes}

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)