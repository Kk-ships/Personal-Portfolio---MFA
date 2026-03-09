from datetime import date

from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.models import Scheme


class SchemeDTO(BaseModel):
    id: int
    isin: str
    amfi_code: str | None
    name: str
    type: str
    latest_nav: float | None
    latest_nav_date: date | None


def get_scheme_by_id(session: Session, scheme_id: int) -> SchemeDTO | None:
    scheme = session.get(Scheme, scheme_id)
    if not scheme:
        return None
    return SchemeDTO.model_validate(scheme, from_attributes=True)


def get_schemes_by_ids(session: Session, scheme_ids: list[int]) -> list[SchemeDTO]:
    if not scheme_ids:
        return []
    schemes = session.exec(select(Scheme).where(Scheme.id.in_(scheme_ids))).all()
    return [SchemeDTO.model_validate(s, from_attributes=True) for s in schemes]


def get_scheme_by_isin(session: Session, isin: str) -> SchemeDTO | None:
    scheme = session.exec(select(Scheme).where(Scheme.isin == isin)).first()
    if not scheme:
        return None
    return SchemeDTO.model_validate(scheme, from_attributes=True)
