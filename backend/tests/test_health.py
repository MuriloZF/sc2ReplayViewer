from backend.app.api.routes.health import health_check
from backend.app.main import app


def test_health_check() -> None:
    response = health_check()

    assert response.model_dump() == {"status": "ok"}


def test_health_route_is_registered() -> None:
    assert str(app.url_path_for("health_check")) == "/api/v1/health"
