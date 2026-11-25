import sys
from datasets import load_dataset, concatenate_datasets
import os
import json
import re
import time
import csv
from pathlib import Path
import sys

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

# Allow Python to find backend/agents
sys.path.insert(0, str(BACKEND_DIR))
from pathlib import Path

from datasets import load_dataset, concatenate_datasets
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

# ============================================================
# PROJECT PATH
# ============================================================
# PROJECT PATH FIX
CURRENT_DIR = Path(__file__).resolve().parent        # backend/evaluation
BACKEND_PATH = CURRENT_DIR.parent                   # backend

sys.path.insert(0, str(BACKEND_PATH))



# ============================================================
# IMPORT AGENTS
# ============================================================

from agents.pattern_agent import analyze_prompt
from agents.intent_agent import analyze_intent
from agents.decision_agent import make_decision


# ============================================================
# SETTINGS
# ============================================================

# DATASET_NAME = "neuralchemy/Prompt-injection-dataset"
# DATASET_CONFIG = "core"
# DATASET_SPLIT = "test"
# DATASET_NAME = "deepset/prompt-injections"
# DATASET_CONFIG = None
# DATASET_SPLIT = "test"
DATASET_NAME = "neuralchemy/Prompt-injection-dataset"
DATASET_CONFIG = "core"
DATASET_SPLIT = "test"
# FIRST RUN:
# Use 10 to make sure everything works.
#
# Later change this to:
# LIMIT = None
#
# to evaluate all 942 test samples.

LIMIT = 20

# Files created by this script
RESULTS_FILE = PROJECT_ROOT / "backend" / "evaluation" / "results.csv"
METRICS_FILE = PROJECT_ROOT / "backend" / "evaluation" / "metrics.csv"
CACHE_FILE = PROJECT_ROOT / "backend" / "evaluation" / "intent_cache.json"
# ============================================================
# LOAD INTENT CACHE
# ============================================================

if CACHE_FILE.exists():

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        intent_cache = json.load(f)

else:

    intent_cache = {}


# ============================================================
# SAVE INTENT CACHE
# ============================================================

def save_intent_cache():

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            intent_cache,
            f,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# NORMALIZE INTENT RESULT
# ============================================================

def normalize_intent_result(result):
    """
    Converts different Intent Agent output formats
    into one common format.

    Supports both:

    1. New Intent Agent:
       {
           "intent": "PROMPT_INJECTION",
           "is_injection": True,
           "risk_score": 0.9,
           ...
       }

    2. Older Intent Agent:
       {
           "analysis": "INTENT: PROMPT_INJECTION..."
       }
    """

    # --------------------------------------------------------
    # Case 1: Result is not a dictionary
    # --------------------------------------------------------

    if not isinstance(result, dict):

        result = {
            "analysis": str(result)
        }


    # --------------------------------------------------------
    # Case 2: New structured Intent Agent
    # --------------------------------------------------------

    if "intent" in result:

        intent = str(
            result.get("intent", "UNKNOWN")
        ).upper()

        risk_score = result.get(
            "risk_score",
            0
        )

        # New agent stores risk_score between 0 and 1
        # Convert it to 0-100.

        try:

            risk_score = float(risk_score)

            if risk_score <= 1:
                risk_score = risk_score * 100

        except:

            risk_score = 0


        attack_type = str(
            result.get(
                "attack_type",
                "NONE"
            )
        ).strip()


        return {
            "intent": intent,
            "risk_score": int(risk_score),
            "attack_type": attack_type,
            "analysis": (
                f"INTENT: {intent}\n"
                f"RISK_SCORE: {int(risk_score)}\n"
                f"ATTACK_TYPE: {attack_type}\n"
            )
        }


    # --------------------------------------------------------
    # Case 3: Older Intent Agent
    # --------------------------------------------------------

    analysis = str(
        result.get(
            "analysis",
            ""
        )
    )


    intent_match = re.search(
        r"INTENT:\s*(SAFE|PROMPT_INJECTION)",
        analysis,
        re.IGNORECASE
    )

    score_match = re.search(
        r"RISK_SCORE:\s*(\d+)",
        analysis,
        re.IGNORECASE
    )

    attack_match = re.search(
        r"ATTACK_TYPE:\s*(.+)",
        analysis,
        re.IGNORECASE
    )


    if intent_match:

        intent = intent_match.group(1).upper()

    else:

        intent = "UNKNOWN"


    if score_match:

        risk_score = int(
            score_match.group(1)
        )

    else:

        risk_score = 0


    if attack_match:

        attack_type = attack_match.group(1).strip()

    else:

        attack_type = "NONE"


    return {
        "intent": intent,
        "risk_score": risk_score,
        "attack_type": attack_type,
        "analysis": analysis
    }


# ============================================================
# RUN INTENT AGENT
# ============================================================

def run_intent_agent(prompt):

    # Use prompt itself as cache key.
    # This prevents unnecessary Gemini calls if the
    # evaluation script is restarted.

    cache_key = prompt


    if cache_key in intent_cache:

        return intent_cache[cache_key]


    # --------------------------------------------------------
    # Gemini call
    # --------------------------------------------------------

    for attempt in range(3):

        try:

            result = analyze_intent(prompt)

            normalized = normalize_intent_result(
                result
            )


            # If Gemini returned an error, retry.

            if normalized["intent"] == "ERROR":

                print(
                    "Intent Agent returned ERROR. "
                    f"Retry {attempt + 1}/3..."
                )

                time.sleep(13)

                continue


            # Save result

            intent_cache[cache_key] = normalized

            save_intent_cache()

            return normalized


        except Exception as e:

            print(
                f"Intent Agent error "
                f"(attempt {attempt + 1}/3): {e}"
            )

            time.sleep(13)


    # --------------------------------------------------------
    # Failed after retries
    # --------------------------------------------------------

    return {
        "intent": "ERROR",
        "risk_score": 0,
        "attack_type": "NONE",
        "analysis": (
            "INTENT: ERROR\n"
            "RISK_SCORE: 0\n"
            "ATTACK_TYPE: NONE\n"
        )
    }


# ============================================================
# CONVERT DECISION
# ============================================================

def run_sentinel(pattern_result, intent_result):

    """
    Connects Pattern Agent + Intent Agent
    to the existing Decision Agent.
    """

    # Decision Agent expects an "analysis" field.

    decision_input = intent_result


    decision_result = make_decision(
        pattern_result,
        decision_input
    )


    return decision_result


# ============================================================
# LOAD DATASET
# ============================================================

print()
print("=" * 60)
print("SENTINELAI EVALUATION")
print("=" * 60)
print()

print("Loading dataset...")

dataset = load_dataset(
    DATASET_NAME,
    DATASET_CONFIG
)

test_data = dataset[DATASET_SPLIT]

print(
    f"Total test samples available: {len(test_data)}"
)


# ============================================================
# APPLY LIMIT
# ============================================================

if LIMIT is not None:

    safe_samples = test_data.filter(
        lambda x: x["label"] == 0
    )

    injection_samples = test_data.filter(
        lambda x: x["label"] == 1
    )

    half = LIMIT // 2

    safe_samples = safe_samples.select(
        range(min(half, len(safe_samples)))
    )

    injection_samples = injection_samples.select(
        range(min(half, len(injection_samples)))
    )

    test_data = concatenate_datasets(
        [
            safe_samples,
            injection_samples
        ]
    )

    print(
        f"Selected {len(safe_samples)} SAFE samples "
        f"and {len(injection_samples)} "
        f"PROMPT_INJECTION samples."
    )
# ============================================================
# STORAGE
# ============================================================

results = []
skipped_errors = 0

# ============================================================
# EVALUATION LOOP
# ============================================================


for index, sample in enumerate(test_data):

    prompt = sample["text"]
    true_label = int(sample["label"])

    print(
        f"[{index + 1}/{len(test_data)}] Processing..."
    )

    # 1. PATTERN AGENT
    pattern_result = analyze_prompt(prompt)

    pattern_score = pattern_result.get("risk_score", 0)

    pattern_prediction = (
        1 if pattern_score > 0 else 0
    )

    # 2. INTENT AGENT
    intent_result = run_intent_agent(prompt)

    print("Intent result:", intent_result)

    if intent_result.get("intent") == "ERROR":
        print("Skipping sample due to Intent Agent error.")
        skipped_errors += 1
        continue

    intent_prediction = (
        1 if intent_result["intent"] == "PROMPT_INJECTION" else 0
    )

    intent_score = intent_result.get("risk_score", 0)

    # 3. SENTINELAI
    sentinel_result = run_sentinel(
        pattern_result,
        intent_result
    )

    if sentinel_result.get("decision") == "ERROR":
        print("Skipping sample due to SentinelAI error.")
        skipped_errors += 1
        continue

    sentinel_prediction = (
        1 if sentinel_result["decision"] == "PROMPT_INJECTION" else 0
    )

    sentinel_score = sentinel_result.get("final_risk_score", 0)

    # 4. STORE RESULT
    results.append({
        "index": index,
        "prompt": prompt,
        "true_label": true_label,
        "pattern_prediction": pattern_prediction,
        "pattern_score": pattern_score,
        "intent_prediction": intent_prediction,
        "intent_score": intent_score,
        "sentinel_prediction": sentinel_prediction,
        "sentinel_score": sentinel_score,
        "attack_type": sentinel_result.get("attack_type", "NONE")
    })

 

    # Dataset label:
    #
    # 0 = SAFE / BENIGN
    # 1 = PROMPT INJECTION

    true_label = int(sample["label"])


    print(
        f"[{index + 1}/{len(test_data)}] "
        f"Processing..."
    )


    # ========================================================
    # 1. PATTERN AGENT
    # ========================================================

    pattern_result = analyze_prompt(prompt)


    pattern_score = pattern_result.get(
        "risk_score",
        0
    )


    # Pattern Agent prediction:
    #
    # Any detected suspicious pattern = injection

    pattern_prediction = (
        1
        if pattern_score > 0
        else 0
    )


    # ========================================================
    # 2. INTENT AGENT
    # ========================================================

    intent_result = run_intent_agent(prompt)

    print("Intent result:", intent_result)

# Skip failed API classifications
    if intent_result.get("intent") == "ERROR":
     print("Skipping sample due to Intent Agent error.")
     continue

intent_prediction = (
    1 if intent_result["intent"] == "PROMPT_INJECTION" else 0
)
    


intent_score = intent_result.get(
        "risk_score",
        0
    )


    # ========================================================
    # 3. SENTINELAI
    # ========================================================

sentinel_result = run_sentinel(
        pattern_result,
        intent_result
    )
if sentinel_result.get("decision") == "ERROR":
    print("Skipping sample due to SentinelAI error.")
    


sentinel_prediction = (
        1
        if sentinel_result["decision"]
        == "PROMPT_INJECTION"
        else 0
    )


sentinel_score = sentinel_result.get(
        "final_risk_score",
        0
    )


    # ========================================================
    # STORE RESULT
    # ========================================================




# ============================================================
# SAVE RESULTS
# ============================================================

print()
print("Saving results...")

with open(
    RESULTS_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=results[0].keys()
    )

    writer.writeheader()

    writer.writerows(results)


print(
    f"Results saved to:\n{RESULTS_FILE}"
)


# ============================================================
# METRIC FUNCTION
# ============================================================

def calculate_metrics(
    y_true,
    y_pred
):

    accuracy = accuracy_score(
        y_true,
        y_pred
    )

    precision = precision_score(
        y_true,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_true,
        y_pred,
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        zero_division=0
    )


    # --------------------------------------------------------
    # Confusion Matrix
    #
    # [[TN, FP],
    #  [FN, TP]]
    # --------------------------------------------------------

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1]
    ).ravel()


    # False Positive Rate
    #
    # FPR = FP / (FP + TN)

    if (fp + tn) > 0:

        fpr = fp / (fp + tn)

    else:

        fpr = 0


    return {
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1": f1,
        "FPR": fpr,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "TP": tp
    }


# ============================================================
# CALCULATE ALL METRICS
# ============================================================

y_true = [
    row["true_label"]
    for row in results
]


pattern_predictions = [
    row["pattern_prediction"]
    for row in results
]


intent_predictions = [
    row["intent_prediction"]
    for row in results
]


sentinel_predictions = [
    row["sentinel_prediction"]
    for row in results
]


pattern_metrics = calculate_metrics(
    y_true,
    pattern_predictions
)


intent_metrics = calculate_metrics(
    y_true,
    intent_predictions
)


sentinel_metrics = calculate_metrics(
    y_true,
    sentinel_predictions
)


# ============================================================
# PRINT METRICS
# ============================================================

print()
print("=" * 60)
print("EVALUATION RESULTS")
print("=" * 60)


def print_metrics(
    name,
    metrics
):

    print()
    print(name)
    print("-" * len(name))

    print(
        f"Accuracy  : {metrics['Accuracy']:.4f}"
    )

    print(
        f"Precision : {metrics['Precision']:.4f}"
    )

    print(
        f"Recall    : {metrics['Recall']:.4f}"
    )

    print(
        f"F1 Score  : {metrics['F1']:.4f}"
    )

    print(
        f"FPR       : {metrics['FPR']:.4f}"
    )

    print(
        f"TN        : {metrics['TN']}"
    )

    print(
        f"FP        : {metrics['FP']}"
    )

    print(
        f"FN        : {metrics['FN']}"
    )

    print(
        f"TP        : {metrics['TP']}"
    )


print_metrics(
    "PATTERN AGENT",
    pattern_metrics
)

print_metrics(
    "INTENT AGENT",
    intent_metrics
)

print_metrics(
    "SENTINELAI",
    sentinel_metrics
)


# ============================================================
# SAVE METRICS
# ============================================================

metrics_rows = [

    {
        "System": "Pattern Agent",
        **pattern_metrics
    },

    {
        "System": "Intent Agent",
        **intent_metrics
    },

    {
        "System": "SentinelAI",
        **sentinel_metrics
    }

]


with open(
    METRICS_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    fieldnames = [
        "System",
        "Accuracy",
        "Precision",
        "Recall",
        "F1",
        "FPR",
        "TN",
        "FP",
        "FN",
        "TP"
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(
        metrics_rows
    )


# ============================================================
# FINAL MESSAGE
# ============================================================

print()
print("=" * 60)
print("EVALUATION COMPLETE")
print("=" * 60)

print()
print("Files created:")

print(
    f"1. {RESULTS_FILE}"
)

print(
    f"2. {METRICS_FILE}"
)

print(
    f"3. {CACHE_FILE}"
)

print()