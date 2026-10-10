from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_local_preprod_has_one_public_http_origin():
    compose = (ROOT / "deploy/compose.preprod-local.yml").read_text(encoding="utf-8")
    assert '"127.0.0.1:8000:80"' in compose
    assert "SITE_BASE_URL: http://127.0.0.1:8000/" in compose
    assert 'CSRF_TRUSTED_ORIGINS: "http://127.0.0.1:8000,http://localhost:8000"' in compose
    assert "ports: !override []" in compose
    assert "8180" not in compose
    assert "8181" not in compose


def test_nginx_preserves_browser_host_port():
    config = (ROOT / "deploy/nginx/nginx.conf").read_text(encoding="utf-8")
    assert config.count("proxy_set_header Host $http_host;") == 2
    assert "proxy_set_header Host $host;" not in config
