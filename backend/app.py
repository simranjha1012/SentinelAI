from fastapi import FastAPI
from pydantic import BaseModel

from backend.agents.pattern_agent import analyze_prompt
from backend.agents.intent_agent import analyze_intent
from backend.agents.decision_agent import make_decision


app = FastAPI(title="SentinelAI")


class PromptRequest(BaseModel):
    prompt: str


@app.get("/")
def home():
    return {
        "message": "SentinelAI backend is running"
    }


@app.post("/analyze")
def analyze(request: PromptRequest):

    pattern_result = analyze_prompt(request.prompt)

    intent_result = analyze_intent(request.prompt)

    decision_result = make_decision(
        pattern_result,
        intent_result
    )

    return {
        "prompt": request.prompt,
        "pattern_analysis": pattern_result,
        "intent_analysis": intent_result,
        "decision": decision_result
    }