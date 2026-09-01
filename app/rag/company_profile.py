from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    __table_args__ = {"schema": "rag"}

    company: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile: Mapped[str] = mapped_column(Text)


def get_company_profile(db: Session, company: str) -> CompanyProfile | None:
    return db.get(CompanyProfile, company)


def upsert_company_profile(db: Session, company: str, profile: str) -> CompanyProfile:
    existing = db.get(CompanyProfile, company)
    if existing is not None:
        existing.profile = profile
        db.flush()
        return existing
    new_profile = CompanyProfile(company=company, profile=profile)
    db.add(new_profile)
    db.flush()
    return new_profile
