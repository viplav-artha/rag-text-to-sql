import re

from sqlalchemy import delete, inspect

from app.core.db import db_session, engine
from app.rag.company_profile import upsert_company_profile
from app.rag.example_store import FewShotExample, add_example
from app.rag.schema_store import SchemaChunk, add_schema_chunk
from data.companies import futwork as company_data

_PER_CLIENT_PATTERN = re.compile(
    r"^(" + "|".join(re.escape(p) for p in company_data.PER_CLIENT_TEMPLATES) + r")_(.+)$"
)


def _describe_column(column_name: str) -> tuple[str, bool] | None:
    match = _PER_CLIENT_PATTERN.match(column_name)
    if match:
        base_metric, client = match.groups()
        template = company_data.PER_CLIENT_TEMPLATES[base_metric]
        return template.format(client=client), True

    description = company_data.METRIC_DESCRIPTIONS.get(column_name)
    if description is None:
        return None
    return description, False


def ingest() -> None:
    inspector = inspect(engine)
    columns = inspector.get_columns(company_data.TABLE_NAME, schema=company_data.SCHEMA_NAME)

    inserted = 0
    skipped: list[str] = []

    with db_session() as db:
        db.execute(delete(SchemaChunk).where(SchemaChunk.company == company_data.COMPANY))
        db.execute(delete(FewShotExample).where(FewShotExample.company == company_data.COMPANY))

        upsert_company_profile(db, company_data.COMPANY, company_data.PROFILE)

        for column in columns:
            name = column["name"]
            if name in company_data.EXCLUDED_COLUMNS:
                continue

            result = _describe_column(name)
            if result is None:
                skipped.append(name)
                continue
            description, is_per_entity = result

            add_schema_chunk(
                db,
                company_data.COMPANY,
                company_data.SCHEMA_NAME,
                company_data.TABLE_NAME,
                description,
                column_name=name,
                is_per_entity=is_per_entity,
            )
            inserted += 1

        for question, sql in company_data.FEW_SHOT_EXAMPLES:
            add_example(db, company_data.COMPANY, question, sql)

    print(f"Ingested {inserted} schema chunks and {len(company_data.FEW_SHOT_EXAMPLES)} examples "
          f"for company '{company_data.COMPANY}'.")
    if skipped:
        print(f"WARNING: {len(skipped)} column(s) had no description and were skipped: {skipped}")


if __name__ == "__main__":
    ingest()
