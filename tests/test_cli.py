import os
import subprocess
import sys

import cli
from tests.conftest import clean


def test_success_exits_zero_and_prints_sources(use_llm, use_search, capsys):
    use_llm([clean()])

    assert cli.main(["port busy"]) == 0

    output = capsys.readouterr().out
    assert "PATCH v1" in output
    assert "http://example.test" in output


def test_failure_exits_non_zero(monkeypatch, capsys):
    def fail(error):
        raise RuntimeError("provider down")

    monkeypatch.setattr(cli, "run_agent", fail)

    assert cli.main(["port busy"]) == 1


def test_import_needs_no_keys_and_survives_legacy_encoding():
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    env["PYTHONIOENCODING"] = "cp1252"

    finished = subprocess.run(
        [sys.executable, "-W", "ignore", "-c", "import agent.graph, cli"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert finished.returncode == 0, finished.stderr
