"""render.yaml Blueprint config, parsed with stdlib only (no PyYAML dependency)."""
import re
from pathlib import Path

RENDER_YAML = Path(__file__).resolve().parent.parent / "render.yaml"


def _read():
    assert RENDER_YAML.exists(), "render.yaml must exist at repo root"
    return RENDER_YAML.read_text()


def _service_block(text):
    match = re.search(r"^services:\s*\n(.*)", text, re.DOTALL | re.MULTILINE)
    assert match, "render.yaml must define a services list"
    return match.group(1)


def test_render_yaml_exists():
    _read()


def test_web_service_name_and_type():
    block = _service_block(_read())
    assert re.search(r"-\s*type:\s*web", block)
    assert re.search(r"name:\s*parley-demo", block)


def test_docker_runtime_and_dockerfile_path():
    block = _service_block(_read())
    assert re.search(r"runtime:\s*docker", block)
    assert re.search(r"dockerfilePath:\s*\./Dockerfile", block)


def test_health_check_path():
    block = _service_block(_read())
    assert re.search(r"healthCheckPath:\s*/\s*$", block, re.MULTILINE)


def test_container_binds_publicly_without_overriding_its_port():
    block = _service_block(_read())
    assert re.search(r"key:\s*PARLEY_HOST\s*\n\s*value:\s*0\.0\.0\.0", block)
    assert "PARLEY_PORT" not in block
