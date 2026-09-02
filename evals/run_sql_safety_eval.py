"""Runs the SQL-safety eval experiment in LangSmith: feeds every adversarial
candidate_sql in the sql-safety-eval-futwork dataset (see
create_sql_safety_dataset.py) directly into validate_sql_node, and checks
that it was correctly rejected.

Run: python -m evals.run_sql_safety_eval
"""

from dotenv import load_dotenv
from langsmith import evaluate

load_dotenv()

from app.graph.nodes import validate_sql_node

DATASET_NAME = "sql-safety-eval-futwork"


def run_validation(inputs: dict) -> dict:
    state = {
        "company": inputs["company"],
        "question": "",
        "generated_sql": inputs["candidate_sql"],
        "retry_count": 0,
    }
    result = validate_sql_node(state)
    return {"validation_error": result.get("validation_error")}

# evaluate() expects a function that takes inputs and returns outputs, and an evaluator that takes outputs and reference_outputs and returns a score. The reference_outputs are the ground truth labels for the dataset, which in this case is whether the candidate_sql should be rejected or not.
def safety_rejection(outputs: dict, reference_outputs: dict) -> dict:
    should_be_rejected = reference_outputs.get("should_be_rejected", True)
    was_rejected = outputs.get("validation_error") is not None
    score = 1.0 if was_rejected == should_be_rejected else 0.0
    return {"key": "safety_rejection", "score": score}


if __name__ == "__main__":
    evaluate(
        run_validation,
        data=DATASET_NAME,
        evaluators=[safety_rejection],
        experiment_prefix="sql-safety",
    )
