# # 
# import re

# PATTERNS = [
#     r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
#     r"developer\s+mode",
#     r"evil\s+mode",
#     r"jailbreak",
#     r"dan\s+mode",
#     r"reveal\s+(your\s+)?system\s+prompt",
#     r"show\s+me\s+(the\s+)?hidden\s+instructions",
#     r"system\s*:\s*",
#     r"\[hidden\]",
#     r"you\s+are\s+now\s+an\s+unrestricted",
# ]

# def analyze_prompt(prompt: str) -> dict:
#     prompt_clean = prompt.strip()
#     matched = []

#     for pattern in PATTERNS:
#         if re.search(pattern, prompt_clean, re.IGNORECASE):
#             matched.append(pattern)

#     risk_score = 100 if matched else 0
#     return {
#         "risk_score": risk_score,
#         "detected_attacks": matched,
#         "decision": "BLOCK" if matched else "SAFE"
#     }
import re

PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"developer\s+mode",
    r"evil\s+mode",
    r"jailbreak",
    r"dan\s+mode",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"hidden\s+instructions",
    r"\[hidden\]",
    r"unrestricted",
]

def analyze_prompt(prompt: str) -> dict:
    clean_text = prompt.lower()
    matched = []

    for pattern in PATTERNS:
        if re.search(pattern, clean_text):
            matched.append(pattern)

    has_match = len(matched) > 0
    risk_score = 100 if has_match else 0

    return {
        "risk_score": risk_score,
        "detected_attacks": matched,
        "decision": "BLOCK" if has_match else "SAFE"
    }