from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from agent import run_agent
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


# Seguridad
MAX_PROMPT_LENGTH = 300
MAX_REQUESTS_PER_MINUTE = 3
WINDOW_SECONDS = 120
request_log = defaultdict(list) # Registro de timestamps por IP



def validate_request(prompt: str, ip: str):
    """Validate prompt length and rate limit per IP."""
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=400, detail=f"Prompt exceeds {MAX_PROMPT_LENGTH} characters"
        )
    
    now = time.time()
    # Descarta timestamps fuera de la ventana de tiempo (sliding window) 
    request_log[ip] = [t for t in request_log[ip] if now - t < WINDOW_SECONDS]

    if len(request_log[ip]) >= MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=429, detail="Too many requests. Please wait a moment."
        )
    request_log[ip].append(now)




# Modelo de solicitud
class AgentRequest(BaseModel):
    """Request model for agent invocation."""

    prompt: str


# Modelo de respuesta
class AgentResponse(BaseModel):
    """Response model for agent invocation."""

    response: str



@app.get("/")
async def home(request: Request):
    """Serve the main HTML interface."""
    return templates.TemplateResponse("index.html", {"request": request})



@app.post("/agent", response_model=AgentResponse)
async def invoke_agent(request: AgentRequest, http_request: Request):
    """
    Invoke the AI agent with a prompt.

    The agent can search Wikipedia, GitHub and Stack Overflow.
    """
    try:
        validate_request(request.prompt, http_request.client.host)

        # Ejecutar el agente con el prompt del usuario
        result = run_agent(request.prompt)

        return AgentResponse(response=result)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error invoking agent: {str(e)}")


# uvicorn.run(app, host="0.0.0.0", port=8000)
# uvicorn main:app --reload
