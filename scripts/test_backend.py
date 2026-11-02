"""Executa os testes do backend com isolamento de banco de dados."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

TESTS = [
    "test_email_request.py",
    "test_email_confirmation.py",
    "test_email_concurrency.py",
    "test_email_request_concurrency.py",
    "test_email_delivery_failure.py",
    "test_verification_rate_limit.py",
]


def main():
    for test in TESTS:
        print(f"\n=== Executando {test} ===", flush=True)

        with tempfile.TemporaryDirectory(
            prefix="ist-pesquisa-ci-"
        ) as directory:
            env = os.environ.copy()
            env["IST_PESQUISA_DATABASE_PATH"] = str(
                Path(directory) / "test.db"
            )
            env["EMAIL_PROVIDER"] = "disabled"

            result = subprocess.run(
                [sys.executable, str(BACKEND / test)],
                cwd=BACKEND,
                env=env,
                check=False,
            )

            if result.returncode != 0:
                print(f"FALHOU: {test}", flush=True)
                return result.returncode

    print("\nTodos os testes passaram.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
