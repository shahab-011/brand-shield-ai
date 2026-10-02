import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

load_dotenv()

cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app = FastAPI(
    title="BrandShield AI API",
    version="1.0.0",
    description="Parallel safety analysis for script review workflows using LangGraph.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def merge_score_dicts(existing: dict | None, new_update: dict) -> dict:
    if existing is None:
        return new_update
    return {**existing, **new_update}


class AnalyzerState(TypedDict):
    raw_text: str
    safety_scores: Annotated[dict[str, int], merge_score_dicts]


class ScriptRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class ScriptResponse(BaseModel):
    safety_scores: dict[str, int]
    overall: int
    status: str


def heuristic_score(text: str, key: str) -> int:
    low = text.lower()
    if key == 'toxicity_level':
        terms = ['idiot', 'garbage', 'stupid', 'hate', 'kill', 'damn', 'loser', 'hell']
        score = 6
    elif key == 'copyright_risk':
        terms = ['copied directly', 'copied from', 'brand name', 'trademark', 'lyrics']
        score = 8
    else:
        terms = ['offensive', 'backward', 'primitive', 'crazy', 'illegal alien']
        score = 5

    for term in terms:
        if term in low:
            score += 34 if len(term) > 8 else 27

    if key == 'toxicity_level' and ('idiot' in low or 'garbage' in low):
        score += 15

    return min(score, 96)


llm = None
if os.getenv('GROQ_API_KEY'):
    llm = ChatGroq(
        model=os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b'),
        temperature=0.1,
        api_key=os.getenv('GROQ_API_KEY'),
    )


def evaluate_with_llm(text: str, key: str) -> int:
    if llm is None:
        return heuristic_score(text, key)

    prompt = (
        "Analyze the following text with a strict score from 0 to 100. "
        "Return only a single integer value.\n\n"
        f"Goal: {key}\nText:\n{text}"
    )
    response = llm.invoke(prompt)
    try:
        parsed = int(str(response.content).strip())
        return max(0, min(100, parsed))
    except (TypeError, ValueError):
        return heuristic_score(text, key)


def toxicity_node(state: AnalyzerState) -> dict:
    return {"safety_scores": {"toxicity_level": evaluate_with_llm(state['raw_text'], 'toxicity_level')}}


def copyright_node(state: AnalyzerState) -> dict:
    return {"safety_scores": {"copyright_risk": evaluate_with_llm(state['raw_text'], 'copyright_risk')}}


def culture_node(state: AnalyzerState) -> dict:
    return {"safety_scores": {"cultural_insensitivity": evaluate_with_llm(state['raw_text'], 'cultural_insensitivity')}}


def build_graph() -> StateGraph:
    graph = StateGraph(AnalyzerState)
    graph.add_node('toxicity_node', toxicity_node)
    graph.add_node('copyright_check', copyright_node)
    graph.add_node('culture_node', culture_node)
    graph.add_edge(START, 'toxicity_node')
    graph.add_edge(START, 'copyright_check')
    graph.add_edge(START, 'culture_node')
    graph.add_edge('toxicity_node', END)
    graph.add_edge('copyright_check', END)
    graph.add_edge('culture_node', END)
    return graph


brandshield_graph = build_graph().compile()


@app.get('/health')
def healthcheck() -> dict:
    return {"status": "ok", "service": "brandshield-ai-api"}


@app.post('/api/analyze', response_model=ScriptResponse)
def analyze_script(request: ScriptRequest) -> ScriptResponse:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail='Text cannot be empty.')

    final_state = brandshield_graph.invoke({"raw_text": text, "safety_scores": {}})
    scores = final_state.get('safety_scores', {})
    overall = round(sum(scores.values()) / max(len(scores), 1)) if scores else 0
    status = 'Needs attention' if overall >= 55 else 'Review suggested' if overall >= 25 else 'Looking good'

    return ScriptResponse(safety_scores=scores, overall=overall, status=status)


@app.get('/')
def root() -> dict:
    return {"status": "ok", "message": "BrandShield AI API is running."}
