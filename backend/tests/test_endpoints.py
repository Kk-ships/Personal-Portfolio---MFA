import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel, select
from sqlmodel.pool import StaticPool
from uuid import uuid4, UUID
from datetime import date, datetime, timedelta
import hashlib
import io
from unittest.mock import Mock, patch, MagicMock

from main import app
from app.db.engine import get_session
from app.models.models import (
    User,
    Portfolio,
    Folio,
    Scheme,
    Transaction,
    NavHistory,
    SystemState,
    FundEnrichment,
)


# Test database setup
@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh test database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with overridden dependencies."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create a test user."""
    user = User(id=uuid4(), name="Test User", pan="TEST123456", pin_hash=None)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="test_user_with_pin")
def test_user_with_pin_fixture(session: Session):
    """Create a test user with PIN."""
    pin = "1234"
    pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    user = User(
        id=uuid4(), name="Test User with PIN", pan="TEST789012", pin_hash=pin_hash
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user, pin


@pytest.fixture(name="test_scheme")
def test_scheme_fixture(session: Session):
    """Create a test scheme."""
    scheme = Scheme(
        amfi_code="119551",
        name="HDFC Flexi Cap Fund - Direct Plan - Growth",
        isin="INF179K01VT8",
        type="EQUITY",
        fund_house="HDFC Mutual Fund",
        scheme_category="Equity Scheme - Flexi Cap Fund",
        scheme_type="Open Ended Schemes",
        latest_nav=850.50,
        latest_nav_date=date.today(),
    )
    session.add(scheme)
    session.commit()
    session.refresh(scheme)
    return scheme


@pytest.fixture(name="test_portfolio")
def test_portfolio_fixture(session: Session, test_user, test_scheme):
    """Create test portfolio with transactions."""
    portfolio = Portfolio(user_id=test_user.id, name="Test Portfolio")
    session.add(portfolio)
    session.commit()
    session.refresh(portfolio)

    folio = Folio(
        portfolio_id=portfolio.id,
        folio_number="12345/67",
    )
    session.add(folio)
    session.commit()
    session.refresh(folio)

    # Add test transactions
    transactions = [
        Transaction(
            id=f"txn-{test_user.pan}-{test_scheme.isin}-1",
            folio_id=folio.id,
            scheme_id=test_scheme.id,
            date=date.today() - timedelta(days=365),
            type="PURCHASE",
            amount=10000.0,
            nav=800.0,
            units=12.5,
        ),
        Transaction(
            id=f"txn-{test_user.pan}-{test_scheme.isin}-2",
            folio_id=folio.id,
            scheme_id=test_scheme.id,
            date=date.today() - timedelta(days=180),
            type="PURCHASE_SIP",
            amount=5000.0,
            nav=820.0,
            units=6.097,
        ),
        Transaction(
            id=f"txn-{test_user.pan}-{test_scheme.isin}-3",
            folio_id=folio.id,
            scheme_id=test_scheme.id,
            date=date.today() - timedelta(days=30),
            type="REDEMPTION",
            amount=5000.0,
            nav=840.0,
            units=-5.952,
        ),
    ]
    for txn in transactions:
        session.add(txn)
    session.commit()

    return portfolio, folio


# ================================
# Health Check Tests
# ================================


def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "mfa-backend"}


# ================================
# Analytics Endpoint Tests
# ================================


def test_get_summary_success(
    client: TestClient, test_user, test_scheme, test_portfolio
):
    """Test getting portfolio summary with valid user ID."""
    response = client.get(
        "/api/analytics/summary", headers={"x-user-id": str(test_user.id)}
    )
    assert response.status_code == 200
    data = response.json()
    assert "invested_value" in data
    assert "total_value" in data
    assert "xirr" in data
    assert "holdings" in data


def test_get_summary_missing_header(client: TestClient):
    """Test getting summary without user ID header."""
    response = client.get("/api/analytics/summary")
    assert response.status_code == 400
    assert "x-user-id header is required" in response.json()["detail"]


def test_get_summary_invalid_uuid(client: TestClient):
    """Test getting summary with invalid UUID format."""
    response = client.get(
        "/api/analytics/summary", headers={"x-user-id": "invalid-uuid"}
    )
    assert response.status_code == 400
    assert "Invalid x-user-id format" in response.json()["detail"]


def test_get_summary_user_not_found(client: TestClient):
    """Test getting summary for non-existent user."""
    random_uuid = str(uuid4())
    response = client.get("/api/analytics/summary", headers={"x-user-id": random_uuid})
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


# ================================
# Users Endpoint Tests
# ================================


def test_list_users_empty(client: TestClient):
    """Test listing users when database is empty."""
    response = client.get("/api/users")
    assert response.status_code == 200
    assert response.json() == []


def test_list_users_with_data(client: TestClient, test_user, test_user_with_pin):
    """Test listing users with data."""
    user_with_pin, _ = test_user_with_pin
    response = client.get("/api/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 2
    # Check that is_pin_set flag is correct
    for user in users:
        if user["id"] == str(test_user.id):
            assert user["is_pin_set"] is False
        elif user["id"] == str(user_with_pin.id):
            assert user["is_pin_set"] is True


def test_verify_pin_no_pin_set(client: TestClient, test_user):
    """Test verifying PIN when no PIN is set."""
    response = client.post(
        f"/api/users/{test_user.id}/verify-pin", json={"pin": "1234"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_verify_pin_correct(client: TestClient, test_user_with_pin):
    """Test verifying correct PIN."""
    user, pin = test_user_with_pin
    response = client.post(f"/api/users/{user.id}/verify-pin", json={"pin": pin})
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_verify_pin_incorrect(client: TestClient, test_user_with_pin):
    """Test verifying incorrect PIN."""
    user, _ = test_user_with_pin
    response = client.post(f"/api/users/{user.id}/verify-pin", json={"pin": "9999"})
    assert response.status_code == 401
    assert "Invalid PIN" in response.json()["detail"]


def test_verify_pin_user_not_found(client: TestClient):
    """Test verifying PIN for non-existent user."""
    random_uuid = str(uuid4())
    response = client.post(f"/api/users/{random_uuid}/verify-pin", json={"pin": "1234"})
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_set_pin_success(client: TestClient, test_user):
    """Test setting a valid PIN."""
    response = client.post(f"/api/users/{test_user.id}/set-pin", json={"pin": "5678"})
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify PIN was set
    verify_response = client.post(
        f"/api/users/{test_user.id}/verify-pin", json={"pin": "5678"}
    )
    assert verify_response.status_code == 200


def test_set_pin_invalid_length(client: TestClient, test_user):
    """Test setting PIN with invalid length."""
    response = client.post(f"/api/users/{test_user.id}/set-pin", json={"pin": "123"})
    assert response.status_code == 400
    assert "PIN must be exactly 4 digits" in response.json()["detail"]


def test_set_pin_non_numeric(client: TestClient, test_user):
    """Test setting non-numeric PIN."""
    response = client.post(f"/api/users/{test_user.id}/set-pin", json={"pin": "abcd"})
    assert response.status_code == 400
    assert "PIN must be exactly 4 digits" in response.json()["detail"]


def test_set_pin_user_not_found(client: TestClient):
    """Test setting PIN for non-existent user."""
    random_uuid = str(uuid4())
    response = client.post(f"/api/users/{random_uuid}/set-pin", json={"pin": "1234"})
    assert response.status_code == 404


def test_remove_pin_success(client: TestClient, test_user_with_pin):
    """Test removing PIN with correct verification."""
    user, pin = test_user_with_pin
    response = client.post(f"/api/users/{user.id}/remove-pin", json={"pin": pin})
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify PIN was removed - should allow access without PIN
    verify_response = client.post(
        f"/api/users/{user.id}/verify-pin", json={"pin": "0000"}
    )
    assert verify_response.status_code == 200


def test_remove_pin_incorrect(client: TestClient, test_user_with_pin):
    """Test removing PIN with incorrect verification."""
    user, _ = test_user_with_pin
    response = client.post(f"/api/users/{user.id}/remove-pin", json={"pin": "9999"})
    assert response.status_code == 401
    assert "Incorrect PIN" in response.json()["detail"]


def test_remove_pin_no_pin_set(client: TestClient, test_user):
    """Test removing PIN when no PIN is set."""
    response = client.post(f"/api/users/{test_user.id}/remove-pin", json={"pin": "1234"})
    assert response.status_code == 200
    assert response.json()["success"] is True


# ================================
# Status Endpoint Tests
# ================================


def test_get_sync_status_no_data(client: TestClient):
    """Test getting sync status when no sync has run."""
    response = client.get("/api/status/sync")
    assert response.status_code == 200
    data = response.json()
    assert data["is_syncing"] is False
    assert data["last_synced"] is None
    assert data["progress"] == "0/0"


def test_get_sync_status_with_data(client: TestClient, session: Session):
    """Test getting sync status with existing state."""
    # Create system state entries
    session.add(SystemState(key="nav_sync_status", value="IN_PROGRESS"))
    session.add(
        SystemState(key="nav_sync_last_run", value="2026-03-08T10:30:00")
    )
    session.add(SystemState(key="nav_sync_progress", value="100/200"))
    session.commit()

    response = client.get("/api/status/sync")
    assert response.status_code == 200
    data = response.json()
    assert data["is_syncing"] is True
    assert data["last_synced"] == "2026-03-08T10:30:00"
    assert data["progress"] == "100/200"


def test_get_sync_status_completed(client: TestClient, session: Session):
    """Test getting sync status when sync is completed."""
    session.add(SystemState(key="nav_sync_status", value="COMPLETED"))
    session.add(
        SystemState(key="nav_sync_last_run", value="2026-03-08T12:00:00")
    )
    session.commit()

    response = client.get("/api/status/sync")
    assert response.status_code == 200
    data = response.json()
    assert data["is_syncing"] is False
    assert data["last_synced"] == "2026-03-08T12:00:00"


# ================================
# Scheme Endpoint Tests
# ================================


def test_get_scheme_details_success(
    client: TestClient, test_user, test_scheme, test_portfolio
):
    """Test getting scheme details with valid data."""
    response = client.get(
        f"/api/scheme/{test_scheme.amfi_code}",
        headers={"x-user-id": str(test_user.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "scheme" in data
    assert "kpis" in data
    assert "ledger" in data
    assert data["scheme"]["amfi_code"] == test_scheme.amfi_code
    assert data["scheme"]["name"] == test_scheme.name


def test_get_scheme_details_missing_header(client: TestClient, test_scheme):
    """Test getting scheme details without user ID header."""
    response = client.get(f"/api/scheme/{test_scheme.amfi_code}")
    assert response.status_code == 400
    assert "x-user-id header is required" in response.json()["detail"]


def test_get_scheme_details_invalid_user_id(client: TestClient, test_scheme):
    """Test getting scheme details with invalid user ID."""
    response = client.get(
        f"/api/scheme/{test_scheme.amfi_code}", headers={"x-user-id": "invalid"}
    )
    assert response.status_code == 400
    assert "Invalid user id" in response.json()["detail"]


def test_get_scheme_details_not_found(client: TestClient, test_user):
    """Test getting details for non-existent scheme."""
    response = client.get(
        "/api/scheme/999999", headers={"x-user-id": str(test_user.id)}
    )
    assert response.status_code == 404
    assert "Scheme not found" in response.json()["detail"]


def test_get_scheme_history_success(client: TestClient, test_scheme, session: Session):
    """Test getting scheme NAV history."""
    # Add some NAV history
    history = [
        NavHistory(
            scheme_id=test_scheme.id,
            date=date.today() - timedelta(days=i),
            nav=800.0 + i * 0.5,
        )
        for i in range(10)
    ]
    for h in history:
        session.add(h)
    session.commit()

    response = client.get(f"/api/scheme/{test_scheme.amfi_code}/history")
    assert response.status_code == 200
    data = response.json()
    assert "scheme_name" in data
    assert "data" in data
    assert len(data["data"]) == 10
    assert data["amfi_code"] == test_scheme.amfi_code


def test_get_scheme_history_not_found(client: TestClient):
    """Test getting history for non-existent scheme."""
    response = client.get("/api/scheme/999999/history")
    assert response.status_code == 404
    assert "Scheme not found" in response.json()["detail"]


@patch("app.api.scheme.fetch_scheme_data")
def test_get_scheme_history_empty_with_mfapi_fallback(
    mock_fetch, client: TestClient, test_scheme
):
    """Test getting history when empty - should trigger MFAPI fallback."""
    mock_fetch.return_value = None
    response = client.get(f"/api/scheme/{test_scheme.amfi_code}/history")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []


@patch("app.services.nav.backfill_historical_nav")
def test_trigger_scheme_backfill_success(
    mock_backfill, client: TestClient, test_scheme
):
    """Test triggering scheme backfill successfully."""
    mock_backfill.return_value = True
    response = client.post(f"/api/scheme/{test_scheme.amfi_code}/backfill")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_backfill.assert_called_once()


@patch("app.services.nav.backfill_historical_nav")
def test_trigger_scheme_backfill_failure(
    mock_backfill, client: TestClient, test_scheme
):
    """Test triggering scheme backfill when it fails."""
    mock_backfill.return_value = False
    response = client.post(f"/api/scheme/{test_scheme.amfi_code}/backfill")
    assert response.status_code == 500
    assert "Backfill failed" in response.json()["detail"]


def test_trigger_scheme_backfill_not_found(client: TestClient):
    """Test triggering backfill for non-existent scheme."""
    response = client.post("/api/scheme/999999/backfill")
    assert response.status_code == 404


@patch("app.api.scheme.fetch_fund_intelligence")
@patch("app.api.scheme.get_enrichment_for_scheme")
def test_get_scheme_enrichment_success(
    mock_get_enrichment, mock_fetch, client: TestClient, test_scheme, session: Session
):
    """Test getting scheme enrichment data successfully."""
    # Create cached enrichment
    enrichment = FundEnrichment(
        scheme_id=test_scheme.id,
        fetched_at=datetime.now(),
        aum=1000.0,
        expense_ratio=0.5,
        exit_load="1% if redeemed within 1 year",
        min_sip=100.0,
        min_lumpsum=5000.0,
    )
    session.add(enrichment)
    session.commit()

    mock_dto = {
        "aum": 1000.0,
        "expense_ratio": 0.5,
        "exit_load": "1% if redeemed within 1 year",
    }
    mock_get_enrichment.return_value = mock_dto

    response = client.get(f"/api/scheme/{test_scheme.amfi_code}/enrichment")
    assert response.status_code == 200
    assert response.json() == mock_dto


def test_get_scheme_enrichment_not_found(client: TestClient):
    """Test getting enrichment for non-existent scheme."""
    response = client.get("/api/scheme/999999/enrichment")
    assert response.status_code == 404


@patch("app.api.scheme.fetch_fund_intelligence")
def test_get_scheme_enrichment_daas_processing(
    mock_fetch, client: TestClient, test_scheme
):
    """Test getting enrichment when DaaS is still processing."""
    from app.services.fund_intelligence import DaasProcessingException

    mock_fetch.side_effect = DaasProcessingException(5)
    response = client.get(f"/api/scheme/{test_scheme.amfi_code}/enrichment")
    assert response.status_code == 503


# ================================
# NAV Endpoint Tests
# ================================


@patch("app.api.nav.subprocess.run")
@patch("app.api.nav.sync_navs")
@patch("app.api.nav.get_portfolio_summary")
def test_sync_nav_success(
    mock_summary, mock_sync, mock_subprocess, client: TestClient, test_user
):
    """Test triggering NAV sync successfully."""
    mock_sync.return_value = {"synced": 10, "failed": 0}
    mock_summary.return_value = {
        "total_invested": 10000.0,
        "current_value": 12000.0,
        "total_gain": 2000.0,
    }

    response = client.post(
        "/api/sync-nav", headers={"x-user-id": str(test_user.id)}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert data["data"]["current_value"] == 12000.0


def test_sync_nav_missing_header(client: TestClient):
    """Test triggering NAV sync without user ID header."""
    response = client.post("/api/sync-nav")
    assert response.status_code == 400
    assert "User ID header is required" in response.json()["detail"]


@patch("app.api.nav.subprocess.run")
@patch("app.api.nav.sync_navs")
def test_sync_nav_failure(mock_sync, mock_subprocess, client: TestClient, test_user):
    """Test NAV sync when it fails."""
    mock_sync.side_effect = Exception("Sync failed")
    response = client.post(
        "/api/sync-nav", headers={"x-user-id": str(test_user.id)}
    )
    assert response.status_code == 500
    assert "Sync failed" in response.json()["detail"]


# ================================
# CAS Upload Endpoint Tests
# ================================


@patch("app.services.fund_intelligence.trigger_bulk_daas_prefetch")
@patch("app.api.cas.backfill_all_schemes")  # Mock at import location
@patch("app.api.cas.trigger_background_sync")
@patch("app.api.cas.process_cas_data")
def test_upload_cas_success(
    mock_process, mock_bg_sync, mock_backfill, mock_prefetch, client: TestClient, test_user
):
    """Test uploading CAS file successfully."""
    mock_process.return_value = {
        "status": "success",
        "message": "CAS processed successfully",
        "isins": ["INF179K01VT8"],
    }

    # Create a fake PDF file
    pdf_content = b"%PDF-1.4\n%fake pdf content"
    files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"password": "testpass"}

    response = client.post(
        "/api/upload",
        files=files,
        data=data,
        headers={"x-user-id": str(test_user.id)},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_upload_cas_invalid_file_type(client: TestClient, test_user):
    """Test uploading non-PDF file."""
    files = {"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")}
    data = {"password": "testpass"}

    response = client.post(
        "/api/upload",
        files=files,
        data=data,
        headers={"x-user-id": str(test_user.id)},
    )
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


def test_upload_cas_file_too_large(client: TestClient, test_user):
    """Test uploading file that's too large."""
    # Create a file larger than 10MB
    large_content = b"x" * (11 * 1024 * 1024)
    files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
    data = {"password": "testpass"}

    response = client.post(
        "/api/upload",
        files=files,
        data=data,
        headers={"x-user-id": str(test_user.id)},
    )
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]


@patch("app.api.cas.process_cas_data")
def test_upload_cas_processing_error(mock_process, client: TestClient, test_user):
    """Test CAS upload when processing fails."""
    mock_process.side_effect = Exception("Processing failed")

    pdf_content = b"%PDF-1.4\n%fake pdf content"
    files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"password": "testpass"}

    response = client.post(
        "/api/upload",
        files=files,
        data=data,
        headers={"x-user-id": str(test_user.id)},
    )
    assert response.status_code == 500


# ================================
# Integration Tests
# ================================


def test_full_user_workflow(client: TestClient, session: Session):
    """Test complete user workflow: create user, set PIN, verify, remove PIN."""
    # Create user
    user = User(id=uuid4(), name="Integration Test User", pan="INT123456")
    session.add(user)
    session.commit()

    # List users
    response = client.get("/api/users")
    assert response.status_code == 200
    users = response.json()
    assert any(u["id"] == str(user.id) for u in users)

    # Set PIN
    response = client.post(f"/api/users/{user.id}/set-pin", json={"pin": "9876"})
    assert response.status_code == 200

    # Verify correct PIN
    response = client.post(f"/api/users/{user.id}/verify-pin", json={"pin": "9876"})
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify incorrect PIN
    response = client.post(f"/api/users/{user.id}/verify-pin", json={"pin": "0000"})
    assert response.status_code == 401

    # Remove PIN
    response = client.post(f"/api/users/{user.id}/remove-pin", json={"pin": "9876"})
    assert response.status_code == 200

    # Verify no PIN is set anymore
    response = client.post(f"/api/users/{user.id}/verify-pin", json={"pin": "0000"})
    assert response.status_code == 200


def test_scheme_workflow_with_transactions(
    client: TestClient, test_user, test_scheme, test_portfolio, session: Session
):
    """Test scheme workflow with transactions and calculations."""
    # Add NAV history
    history = [
        NavHistory(
            scheme_id=test_scheme.id,
            date=date.today() - timedelta(days=i * 30),
            nav=800.0 + i * 5,
        )
        for i in range(12)
    ]
    for h in history:
        session.add(h)
    session.commit()

    # Get scheme details
    response = client.get(
        f"/api/scheme/{test_scheme.amfi_code}",
        headers={"x-user-id": str(test_user.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["kpis"]["units"] > 0
    assert data["kpis"]["invested_value"] > 0
    assert data["kpis"]["current_value"] > 0

    # Get scheme history
    response = client.get(f"/api/scheme/{test_scheme.amfi_code}/history")
    assert response.status_code == 200
    history_data = response.json()
    assert len(history_data["data"]) == 12

    # Get analytics summary
    response = client.get(
        "/api/analytics/summary", headers={"x-user-id": str(test_user.id)}
    )
    assert response.status_code == 200
