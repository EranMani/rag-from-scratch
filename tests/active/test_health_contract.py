from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.health import router


def test_health_route_returns_ok():
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_circuit_breaker_route_exposes_status_list():
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).get("/api/health/circuit-breakers")

    assert response.status_code == 200
    payload = response.json()
    assert "circuit_breakers" in payload
    assert isinstance(payload["circuit_breakers"], list)
    assert {item["service"] for item in payload["circuit_breakers"]} >= {
        "chroma",
        "openai",
        "redis",
    }
