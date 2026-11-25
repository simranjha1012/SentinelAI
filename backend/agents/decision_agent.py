def extract_intent_result(intent_analysis):
    lines = intent_analysis.splitlines()

    intent = "UNKNOWN"
    risk_score = 0
    attack_type = "NONE"

    for line in lines:
        if line.startswith("INTENT:"):
            intent = line.replace("INTENT:", "").strip()

        elif line.startswith("RISK_SCORE:"):
            try:
                risk_score = int(
                    line.replace("RISK_SCORE:", "").strip()
                )
            except ValueError:
                risk_score = 0

        elif line.startswith("ATTACK_TYPE:"):
            attack_type = line.replace("ATTACK_TYPE:", "").strip()

    return intent, risk_score, attack_type


# def make_decision(pattern_result, intent_result):

#     if isinstance(intent_result, dict):
#         intent_analysis = intent_result.get("analysis", "")
#     else:
#         intent_analysis = str(intent_result)

#     intent, intent_score, intent_attack = extract_intent_result(
#         intent_analysis
#     )

#     pattern_score = pattern_result["risk_score"]

#     final_score = max(pattern_score, intent_score)

#     if intent == "PROMPT_INJECTION" or final_score >= 50:
#         decision = "PROMPT_INJECTION"
#     else:
#         decision = "SAFE"

#     return {
#         "final_risk_score": final_score,
#         "decision": decision,
#         "pattern_score": pattern_score,
#         "intent_score": intent_score,
#         "attack_type": intent_attack
#     }
# def make_decision(pattern_result: dict, intent_result: dict) -> dict:
#     pattern_flag = pattern_result.get("risk_score", 0) >= 50 or pattern_result.get("decision") == "BLOCK"
    
#     # Check both structured key and raw analysis text for robustness
#     analysis_text = intent_result.get("analysis", "")
#     intent_flag = (
#         intent_result.get("intent") == "PROMPT_INJECTION" 
#         or "PROMPT_INJECTION" in analysis_text 
#         or intent_result.get("risk_score", 0) >= 50
#     )

#     if pattern_flag or intent_flag:
#         decision = "PROMPT_INJECTION"
#         final_score = max(pattern_result.get("risk_score", 0), intent_result.get("risk_score", 0))
#     else:
#         decision = "SAFE"
#         final_score = 0

#     return {
#         "decision": decision,
#         "final_risk_score": final_score,
#         "attack_type": intent_result.get("attack_type", "NONE")
#     }
def make_decision(pattern_result: dict, intent_result: dict) -> dict:
    pattern_flag = (
        pattern_result.get("decision") == "BLOCK"
        or pattern_result.get("risk_score", 0) >= 50
    )

    intent_analysis = intent_result.get("analysis", "")
    if (
    intent_result.get("intent") == "ERROR"
    or "INTENT: ERROR" in intent_analysis
):
     return {
        "decision": "ERROR",
        "is_injection": None,
        "final_risk_score": None,
        "attack_type": "ERROR",
        "reason": "Intent analysis failed. No classification produced."
     }
    intent_flag = (
        intent_result.get("intent") == "PROMPT_INJECTION"
        or intent_result.get("is_injection") is True
        or "PROMPT_INJECTION" in intent_analysis
        or intent_result.get("risk_score", 0) >= 50
    )

    if pattern_flag or intent_flag:
        decision = "PROMPT_INJECTION"
        final_risk = max(
            pattern_result.get("risk_score", 0),
            intent_result.get("risk_score", 0)
        )
        if pattern_flag and intent_flag:
            reason = "Flagged by both Pattern matching and Semantic Intent analysis."
        elif pattern_flag:
            reason = "Direct signature detected by Pattern matching."
        else:
            reason = "Semantic injection intent detected by Intent analysis."
    else:
        decision = "SAFE"
        final_risk = 0
        reason = "Input passed both Pattern and Intent evaluations."

    return {
        "decision": decision,
        "is_injection": decision == "PROMPT_INJECTION",
        "final_risk_score": final_risk,
        "attack_type": intent_result.get("attack_type", "NONE"),
        "reason": reason
    }