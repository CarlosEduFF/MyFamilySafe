"""Exporta o contrato OpenAPI da API para openapi.json na raiz do repositório.

O app Flutter (repositório separado) consome este arquivo como contrato, então
ele é versionado aqui: qualquer mudança de rota ou schema aparece no diff do PR.

Uso:
    python scripts/export_openapi.py            # escreve openapi.json
    python scripts/export_openapi.py --check    # falha se estiver desatualizado

O modo --check não escreve nada e serve para CI ou hook de pre-commit.
"""

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "openapi.json"

# app.config exige as variáveis de banco/JWT na importação, mas gerar o schema
# não abre conexão nenhuma. Valores dummy mantêm o script executável sem .env
# e sem Postgres no ar (ex.: num job de CI que só valida o contrato).
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "myfamilysafe")
os.environ.setdefault("DB_SSL", "disable")
os.environ.setdefault("JWT_SECRET", "openapi-export")
os.environ.setdefault("JWT_REFRESH_SECRET", "openapi-export")

sys.path.insert(0, str(REPO_ROOT))

from app.main import app  # noqa: E402


def build_schema() -> dict:
    return app.openapi()


def serialize(schema: dict) -> str:
    # sort_keys mantém o diff estável entre execuções; sem isso a ordem das
    # chaves pode variar e poluir o PR com ruído.
    return json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="não escreve; sai com código 1 se openapi.json estiver desatualizado",
    )
    args = parser.parse_args()

    content = serialize(build_schema())

    if args.check:
        if not OUTPUT.exists():
            print("openapi.json não existe. Rode: python scripts/export_openapi.py")
            return 1
        if OUTPUT.read_text(encoding="utf-8") != content:
            print(
                "openapi.json está desatualizado. "
                "Rode: python scripts/export_openapi.py"
            )
            return 1
        print("openapi.json está atualizado.")
        return 0

    OUTPUT.write_text(content, encoding="utf-8")
    paths = len(json.loads(content)["paths"])
    print(f"openapi.json gerado: {paths} paths -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
