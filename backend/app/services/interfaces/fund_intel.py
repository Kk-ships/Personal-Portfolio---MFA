from datetime import date as dt_date
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.models import (
    FundEnrichment,
)


class PerformanceDTO(BaseModel):
    returns_1y: float | None = None
    returns_3y: float | None = None
    returns_5y: float | None = None
    returns_tooltip: str | None = None
    cagr_1y: float | None = None
    cagr_3y: float | None = None
    cagr_5y: float | None = None
    cagr_10y: float | None = None
    cagr_tooltip: str | None = None
    cagr_rank_1y: int | None = None
    cagr_rank_3y: int | None = None
    cagr_rank_5y: int | None = None
    cagr_rank_10y: int | None = None
    recorded_at: dt_date | None = None

    # Performance history fields (stored as JSON strings)
    quarterly_performance: str | None = None
    best_periods: str | None = None
    worst_periods: str | None = None
    sip_returns: str | None = None
    cagr_cat_avg: str | None = None


class RiskMetricsDTO(BaseModel):
    cat_avg_1y: float | None = None
    cat_avg_3y: float | None = None
    cat_avg_5y: float | None = None
    cat_min_1y: float | None = None
    cat_max_1y: float | None = None
    cat_max_3y: float | None = None
    sharpe_ratio_1y: float | None = None
    sharpe_ratio_3y: float | None = None
    sharpe_ratio_5y: float | None = None
    sharpe_ratio_tooltip: str | None = None
    sortino_ratio_1y: float | None = None
    sortino_ratio_3y: float | None = None
    sortino_ratio_5y: float | None = None
    sortino_ratio_tooltip: str | None = None
    risk_std_dev_1y: float | None = None
    risk_std_dev_3y: float | None = None
    risk_std_dev_5y: float | None = None
    risk_std_dev_tooltip: str | None = None
    beta_1y: float | None = None
    beta_3y: float | None = None
    beta_5y: float | None = None
    beta_tooltip: str | None = None


class HoldingDTO(BaseModel):
    stock_name: str | None = None
    sector: str | None = None
    weighting: float | None = None
    market_value: float | None = None
    change_1m: float | None = None
    holdings_history: str | None = None  # JSON text


class SectorDTO(BaseModel):
    sector_name: str | None = None
    weighting: float | None = None
    market_value: float | None = None
    change_1m: float | None = None


class PeerDTO(BaseModel):
    fund_name: str | None = None
    peer_isin: str | None = None
    peer_amfi_code: str | None = None
    cagr_1y: float | None = None
    cagr_3y: float | None = None
    cagr_5y: float | None = None
    cagr_10y: float | None = None
    yield_to_maturity: float | None = None
    modified_duration: float | None = None
    avg_eff_maturity: float | None = None
    expense_ratio: float | None = None
    portfolio_turnover: float | None = None
    std_deviation: float | None = None


class ManagerDTO(BaseModel):
    manager_name: str | None = None
    role: str | None = None
    start_date: dt_date | None = None
    end_date: dt_date | None = None


class EnrichmentDTO(BaseModel):
    id: int
    scheme_id: int
    isin: Optional[str] = None
    scheme_name: Optional[str] = None
    fund_name: Optional[str] = None
    fetched_at: datetime
    validation_status: int
    nav_validation_status: int
    name_validation_status: int
    freshness_status: int
    is_sectors_normalized: bool = False
    is_holdings_normalized: bool = False
    is_asset_normalized: bool = False
    is_cap_normalized: bool = False

    # Identifiers
    code: str | None = None
    morningstar_id: str | None = None

    # Fund metadata
    scheme_short_name: str | None = None
    category: str | None = None
    sub_category: str | None = None
    fund_type: str | None = None
    plan_name: str | None = None
    option_name: str | None = None
    payout_freq: str | None = None
    inception_date: dt_date | None = None
    benchmark: str | None = None
    riskometer: str | None = None
    investment_style: str | None = None
    rating: str | None = None
    objective: str | None = None
    is_active: bool | None = None

    # NAV snapshot
    latest_nav_api: float | None = None
    nav_change: float | None = None
    nav_change_percent: float | None = None
    nav_date: dt_date | None = None

    # AUM & Cost
    aum_cr: float | None = None
    expense_ratio: float | None = None
    turnover_ratio: float | None = None
    turnover_ratio_cat_avg: float | None = None
    exit_load: str | None = None
    lockin_period: str | None = None

    # Valuation Ratios
    pe: float | None = None
    cat_avg_pe: float | None = None
    pb: float | None = None
    cat_avg_pb: float | None = None
    price_sale: float | None = None
    cat_avg_price_sale: float | None = None
    price_cash_flow: float | None = None
    cat_avg_price_cash_flow: float | None = None
    dividend_yield: float | None = None
    cat_avg_dividend_yield: float | None = None
    roe: float | None = None
    cat_avg_roe: float | None = None

    # Debt fund metrics
    yield_to_maturity: float | None = None
    modified_duration: float | None = None
    avg_eff_maturity: float | None = None
    avg_credit_quality_name: str | None = None

    # Asset Allocation
    equity_alloc: float | None = None
    debt_alloc: float | None = None
    cash_alloc: float | None = None
    other_alloc: float | None = None

    # Cap-weight breakdown
    large_cap_wt: float | None = None
    mid_cap_wt: float | None = None
    small_cap_wt: float | None = None
    others_cap_wt: float | None = None

    # Concentration metrics
    number_of_holdings: int | None = None
    avg_market_cap_cr: float | None = None
    top_3_sectors_weight: float | None = None
    top_5_stocks_weight: float | None = None
    top_10_stocks_weight: float | None = None

    # KBYI insights (JSON text)
    kbyi: str | None = None

    # API calculation timestamp
    calculated_at: datetime | None = None

    # Relationships
    performance: PerformanceDTO | None = None
    risk_metrics: RiskMetricsDTO | None = None
    holdings: list[HoldingDTO] = []
    sectors: list[SectorDTO] = []
    peers: list[PeerDTO] = []
    managers: list[ManagerDTO] = []


def get_enrichment_for_scheme(session: Session, scheme_id: int) -> EnrichmentDTO | None:
    enrichment = session.exec(
        select(FundEnrichment).where(FundEnrichment.scheme_id == scheme_id)
    ).first()
    if not enrichment:
        return None

    dto = EnrichmentDTO.model_validate(enrichment, from_attributes=True)

    # Manually populate the relationships since we are avoiding SQLAlchemy lazy loading where possible
    if enrichment.performance:
        dto.performance = PerformanceDTO.model_validate(
            enrichment.performance, from_attributes=True
        )
    if enrichment.risk_metrics:
        dto.risk_metrics = RiskMetricsDTO.model_validate(
            enrichment.risk_metrics, from_attributes=True
        )

    dto.holdings = [
        HoldingDTO.model_validate(h, from_attributes=True) for h in enrichment.holdings
    ]
    dto.sectors = [
        SectorDTO.model_validate(s, from_attributes=True) for s in enrichment.sectors
    ]
    dto.peers = [
        PeerDTO.model_validate(p, from_attributes=True) for p in enrichment.peers
    ]
    dto.managers = [
        ManagerDTO.model_validate(m, from_attributes=True) for m in enrichment.managers
    ]

    return dto
