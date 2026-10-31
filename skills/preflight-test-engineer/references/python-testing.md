# 🐍 Python Testing Reference & Recipes

This guide documents deep patterns, fixture strategies, mocking mechanics, and property-based testing for Python codebases using **Pytest**, **pytest-mock**, **pytest-asyncio**, and **Hypothesis**.

---

## 1. Pytest Test Harness & Directory Structure

Standardized layout for Python test suites:

```text
tests/
├── conftest.py               # Global fixtures, monkeypatches, hermetic guards
├── pytest.ini                # Pytest configuration and marker declarations
├── fixtures/
│   ├── factories.py          # Typed payload and domain model generators
│   └── mock_responses.json   # Recorded static JSON payloads
├── smoke/
│   └── test_preflight_smoke.py # Import sanity & environment safety checks
├── unit/
│   ├── test_auth.py          # Unit tests with isolated domain logic
│   └── test_parser.py
└── integration/
    └── test_api_routes.py    # Database / API client boundary tests
```

---

## 2. Hermetic Fixtures (`conftest.py`)

Prevent unintentional external network calls, environment contamination, and lingering state.

```python
import pytest
import os
from typing import Generator, Any

@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantees tests run against safe in-memory or stubbed configurations."""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("API_SECRET_KEY", "test-secret-key-12345")

@pytest.fixture
def sample_user() -> dict[str, Any]:
    """Returns a deterministic user dictionary fixture."""
    return {
        "id": "usr_98765",
        "username": "tester",
        "email": "tester@example.com",
        "is_active": True,
    }
```

---

## 3. Mocking & Network Interception

Never allow unit tests to hit live HTTP endpoints. Use `pytest-mock` (`mocker`) or `unittest.mock`.

### Mocking External API Clients:
```python
from unittest.mock import MagicMock
import pytest

def test_fetch_weather_success(mocker: Any) -> None:
    # Arrange
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"temp": 72, "city": "San Francisco"}

    # Act
    from my_app.weather import get_temperature
    result = get_temperature("San Francisco")

    # Assert
    assert result == 72
    mock_get.assert_called_once_with("https://api.weather.com/v1/San%20Francisco", timeout=10)
```

---

## 4. Asynchronous Testing (`pytest-asyncio`)

Decorate asynchronous tests or configure `asyncio_mode = auto` in `pytest.ini`.

```python
import pytest
import httpx
from my_app.async_service import AsyncClient

@pytest.mark.asyncio
async def test_async_service_fetch(mocker: Any) -> None:
    client = AsyncClient(base_url="https://api.internal")
    
    mock_response = mocker.AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mocker.patch.object(client.http_client, "get", return_value=mock_response)

    data = await client.get_health()
    assert data["status"] == "ok"
```

---

## 5. FastAPI / Flask Endpoint Testing

Use `TestClient` to test API routes with dependency injection overrides.

```python
from fastapi.testclient import TestClient
from my_app.main import app, get_db

def test_create_item_endpoint(mocker: Any) -> None:
    mock_db = mocker.MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    client = TestClient(app)
    response = client.post("/items", json={"name": "Widget", "price": 19.99})

    assert response.status_code == 201
    assert response.json()["name"] == "Widget"
    app.dependency_overrides.clear()
```

---

## 6. Property-Based & Boundary Testing (`Hypothesis`)

Automatically generate hundreds of edge cases (Unicode, max integers, zero bytes, empty collections).

```python
from hypothesis import given, strategies as st
from my_app.string_utils import slugify

@given(st.text())
def test_slugify_never_crashes(text: str) -> None:
    result = slugify(text)
    assert isinstance(result, str)
    assert " " not in result
```
