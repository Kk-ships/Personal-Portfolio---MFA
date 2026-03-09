import hashlib
from datetime import UTC, datetime
from datetime import date as dt_date
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


def utc_now() -> datetime:
    """Helper function for default_factory to return timezone-aware UTC datetime"""
    return datetime.now(UTC)


# Shared Data
class AMC(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    code: str = Field(unique=True)


class Scheme(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    isin: str = Field(unique=True, index=True)
    amfi_code: str | None = Field(default=None)
    name: str
    type: str  # EQUITY, DEBT, etc.
    advisor: str | None = None  # DIRECT, REGULAR
    amc_id: int | None = Field(default=None, foreign_key="amc.id")

    # Extended Metadata (From MFAPI)
    fund_house: str | None = None
    scheme_category: str | None = None
    scheme_type: str | None = None

    # Caching latest NAV & Valuation
    latest_nav: float | None = None
    latest_nav_date: dt_date | None = None

    # Snapshot from CAS
    valuation_date: dt_date | None = None
    valuation_value: float | None = None

    # Backfill tracking (V1.4.1)
    last_history_sync: dt_date | None = None

    nav_history: list["NavHistory"] = Relationship(back_populates="scheme")


class NavHistory(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("scheme_id", "date", name="uix_scheme_date"),)

    id: int | None = Field(default=None, primary_key=True)
    scheme_id: int = Field(foreign_key="scheme.id")
    date: dt_date
    nav: float

    scheme: Scheme = Relationship(back_populates="nav_history")


# Private Data
class User(SQLModel, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    name: str
    pan: str = Field(index=True, unique=True)
    pin_hash: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utc_now)

    portfolios: list["Portfolio"] = Relationship(back_populates="user")


class Portfolio(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    name: str

    user: User = Relationship(back_populates="portfolios")
    folios: list["Folio"] = Relationship(back_populates="portfolio")


class Folio(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolio.id")
    amc_id: int | None = Field(default=None, foreign_key="amc.id")
    folio_number: str

    portfolio: Portfolio = Relationship(back_populates="folios")
    transactions: list["Transaction"] = Relationship(back_populates="folio")


class Transaction(SQLModel, table=True):
    # Composite Hash ID: PAN + ISIN + Date + Amount + Type + Units
    id: str = Field(primary_key=True)

    folio_id: int = Field(foreign_key="folio.id")
    scheme_id: int = Field(foreign_key="scheme.id")

    date: dt_date
    type: str
    amount: float
    units: float
    nav: float
    balance: float | None = None

    folio: Folio = Relationship(back_populates="transactions")

    @staticmethod
    def generate_id(
        pan: str, isin: str, date: dt_date, amount: float, type: str, units: float
    ) -> str:
        """
        Generates a deterministic hash for deduplication.
        """
        raw = f"{pan}|{isin}|{date.isoformat()}|{amount}|{type}|{units}"
        return hashlib.sha256(raw.encode()).hexdigest()


class SystemState(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str
    updated_at: datetime = Field(default_factory=utc_now)


# Fund Intelligence Extended Data


class FundEnrichment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    scheme_id: int = Field(foreign_key="scheme.id", unique=True)
    fund_name: str | None = Field(default="Unknown Fund")
    fetched_at: datetime = Field(default_factory=utc_now)

    validation_status: int = Field(
        default=0
    )  # 0: Unvalidated, 1: Passed, 2: Partial, 3: Failed
    nav_validation_status: int = Field(default=0)
    name_validation_status: int = Field(default=0)
    freshness_status: int = Field(default=0)

    # --- New API fields (v2 Integration Guide) ---
    # Identifiers
    code: str | None = None  # Moneycontrol code e.g. "MCC519"
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

    # NAV snapshot from API
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

    # KBYI insights (stored as JSON text)
    kbyi: str | None = None

    # API calculation timestamp
    calculated_at: datetime | None = None

    # --- Relationships ---
    performance: Optional["FundPerformance"] = Relationship(
        back_populates="enrichment",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )
    risk_metrics: Optional["FundRiskMetrics"] = Relationship(
        back_populates="enrichment",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )
    holdings: list["FundHolding"] = Relationship(
        back_populates="enrichment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    sectors: list["FundSector"] = Relationship(
        back_populates="enrichment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    peers: list["FundPeer"] = Relationship(
        back_populates="enrichment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    managers: list["FundManager"] = Relationship(
        back_populates="enrichment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class FundPerformance(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    enrichment_id: int = Field(foreign_key="fundenrichment.id", unique=True)
    returns_1y: float | None = None
    returns_3y: float | None = None
    returns_5y: float | None = None
    returns_tooltip: str | None = None
    cagr_1y: float | None = None
    cagr_3y: float | None = None
    cagr_5y: float | None = None
    cagr_10y: float | None = None  # NEW
    cagr_tooltip: str | None = None

    # Category rank fields (NEW)
    cagr_rank_1y: int | None = None
    cagr_rank_3y: int | None = None
    cagr_rank_5y: int | None = None
    cagr_rank_10y: int | None = None

    # Snapshot date (NEW)
    recorded_at: dt_date | None = None

    # Performance history fields (stored as JSON strings)
    quarterly_performance: str | None = None  # JSON array
    best_periods: str | None = None  # JSON object
    worst_periods: str | None = None  # JSON object
    sip_returns: str | None = None  # JSON object
    cagr_cat_avg: str | None = None  # JSON object

    enrichment: FundEnrichment = Relationship(back_populates="performance")


class FundRiskMetrics(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    enrichment_id: int = Field(foreign_key="fundenrichment.id", unique=True)

    cat_avg_1y: float | None = None
    cat_avg_3y: float | None = None
    cat_avg_5y: float | None = None

    cat_min_1y: float | None = None
    cat_min_3y: float | None = None
    cat_min_5y: float | None = None

    cat_max_1y: float | None = None
    cat_max_3y: float | None = None
    cat_max_5y: float | None = None

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

    enrichment: FundEnrichment = Relationship(back_populates="risk_metrics")


class FundHolding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    enrichment_id: int = Field(foreign_key="fundenrichment.id", index=True)
    stock_name: str | None = Field(default="Unknown Stock")
    sector: str | None = None
    weighting: float | None = None
    market_value: float | None = None
    change_1m: float | None = None  # NEW: 1-month weight change
    holdings_history: str | None = None  # NEW: JSON array [{per, weightage}]

    enrichment: FundEnrichment = Relationship(back_populates="holdings")


class FundSector(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    enrichment_id: int = Field(foreign_key="fundenrichment.id", index=True)
    sector_name: str | None = Field(default="Unknown Sector")
    weighting: float | None = None
    market_value: float | None = None
    change_1m: float | None = None

    enrichment: FundEnrichment = Relationship(back_populates="sectors")


class FundPeer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    enrichment_id: int = Field(foreign_key="fundenrichment.id", index=True)
    fund_name: str | None = Field(default="Unknown Peer")
    peer_isin: str | None = None
    peer_amfi_code: str | None = None  # NEW: for frontend navigation
    cagr_1y: float | None = None  # NEW (was absent)
    cagr_3y: float | None = None  # RENAMED from return_3y
    cagr_5y: float | None = None  # NEW
    cagr_10y: float | None = None  # NEW
    yield_to_maturity: float | None = None  # NEW: debt peer
    modified_duration: float | None = None  # NEW: debt peer
    avg_eff_maturity: float | None = None  # NEW: debt peer
    expense_ratio: float | None = None
    portfolio_turnover: float | None = None  # NEW
    std_deviation: float | None = None

    enrichment: FundEnrichment = Relationship(back_populates="peers")


class FundManager(SQLModel, table=True):
    """NEW: Stores fund manager data from the API."""

    id: int | None = Field(default=None, primary_key=True)
    enrichment_id: int = Field(foreign_key="fundenrichment.id", index=True)
    manager_name: str = Field(default="Unknown Manager")
    role: str | None = None
    start_date: dt_date | None = None
    end_date: dt_date | None = None

    enrichment: FundEnrichment = Relationship(back_populates="managers")
