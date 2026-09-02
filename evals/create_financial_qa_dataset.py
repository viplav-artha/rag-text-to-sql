"""Creates/updates the LangSmith dataset used for financial-QA evals
(execution accuracy, retrieval recall, answer groundedness). Safe to
re-run from the terminal any time — syncs the dataset to exactly match
the EXAMPLES defined below: creates new ones, updates changed ones, and
deletes ones no longer listed here.

Matches existing examples by their `question` text (not by a synthetic
ID) — LangSmith never lets you reuse an example ID once assigned, even
after a hard delete, so IDs must always be left for the server to assign.

Run: python -m evals.create_financial_qa_dataset
"""

from dotenv import load_dotenv
from langsmith import Client

load_dotenv()

DATASET_NAME = "financial-qa-eval-futwork"
DATASET_DESCRIPTION = (
    "Financial Q&A eval set for Futwork. Each example's expected_sql is the "
    "ground truth used to check SQL execution accuracy, retrieval recall "
    "(does the right schema column get retrieved?), and answer groundedness "
    "(does the final answer state the correct number/currency?). Kept "
    "deliberately separate from data/companies/futwork.py's few-shot "
    "examples so the eval never trivially matches on an identical question."
)

EXAMPLES = [
    {
        "question": "What was the total revenue in April 2026?",
        "expected_sql": (
            "SELECT total_revenue FROM portfolio.futwork_vs_aop "
            "WHERE year = 2026 AND month_name = 'april';"
        ),
        "expected_columns": ["total_revenue"],
    },
    {
        "question": "How does actual EBITDA compare to the AOP target for June 2026?",
        "expected_sql": (
            "SELECT ebitda, ebitda_targetted FROM portfolio.futwork_vs_aop "
            "WHERE year = 2026 AND month_name = 'june';"
        ),
        "expected_columns": ["ebitda", "ebitda_targetted"],
    },
    {
        "question": "What is the split between HITL and AI revenue for March 2026?",
        "expected_sql": (
            "SELECT hitl, ai_revenue FROM portfolio.futwork_vs_aop "
            "WHERE year = 2026 AND month_name = 'march';"
        ),
        "expected_columns": ["hitl", "ai_revenue"],
    },
    {
        "question": "How much did BharatPe get billed in May 2026?",
        "expected_sql": (
            "SELECT billing_amount_bharatpe FROM portfolio.futwork_vs_aop "
            "WHERE year = 2026 AND month_name = 'may';"
        ),
        "expected_columns": ["billing_amount_bharatpe"],
    },
    {
        "question": "Give me the receivables aging breakdown for March 2026.",
        "expected_sql": (
            "SELECT ar_current, ar_0_to_30_days, ar_30_to_60_days, ar_60_to_90_days, "
            "ar_90_plus_days, ar_total FROM portfolio.futwork_vs_aop "
            "WHERE year = 2026 AND month_name = 'march';"
        ),
        "expected_columns": [
            "ar_current",
            "ar_0_to_30_days",
            "ar_30_to_60_days",
            "ar_60_to_90_days",
            "ar_90_plus_days",
            "ar_total",
        ],
    },
    {
        "question": "How many callers churned during April 2026?",
        "expected_sql": (
            "SELECT churned_callers FROM portfolio.futwork_vs_aop "
            "WHERE year = 2026 AND month_name = 'april';"
        ),
        "expected_columns": ["churned_callers"],
    },
    {
        "question": "What was Futwork's runway in months for June 2026?",
        "expected_sql": (
            "SELECT runway_in_months FROM portfolio.futwork_vs_aop "
            "WHERE year = 2026 AND month_name = 'june';"
        ),
        "expected_columns": ["runway_in_months"],
    },
]


def sync_dataset() -> None:
    client = Client()

    if client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
    else:
        dataset = client.create_dataset(dataset_name=DATASET_NAME, description=DATASET_DESCRIPTION)

    desired_by_question = {
        ex["question"]: {
            "inputs": {"company": "futwork", "question": ex["question"]},
            "outputs": {
                "expected_sql": ex["expected_sql"],
                "expected_columns": ex["expected_columns"],
            },
        }
        for ex in EXAMPLES
    }
    existing_by_question = {
        example.inputs.get("question"): example for example in client.list_examples(dataset_id=dataset.id)
    }

    to_create = [payload for question, payload in desired_by_question.items() if question not in existing_by_question]
    to_update = [
        {"id": existing_by_question[question].id, **payload}
        for question, payload in desired_by_question.items()
        if question in existing_by_question
        and (
            dict(existing_by_question[question].inputs) != payload["inputs"]
            or dict(existing_by_question[question].outputs) != payload["outputs"]
        )
    ]
    to_delete = [
        example.id for question, example in existing_by_question.items() if question not in desired_by_question
    ]

    if to_create:
        client.create_examples(dataset_id=dataset.id, examples=to_create)
    if to_update:
        client.update_examples(dataset_id=dataset.id, updates=to_update)
    if to_delete:
        client.delete_examples(example_ids=to_delete, hard_delete=True)

    print(
        f"Dataset '{DATASET_NAME}': {len(to_create)} created, {len(to_update)} "
        f"updated, {len(to_delete)} deleted. Total examples now: {len(desired_by_question)}."
    )


if __name__ == "__main__":
    sync_dataset()
