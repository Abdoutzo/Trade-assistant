"""Check the API keys: ask each LLM role a one-word question and show which model answered.

    uv run python -m trade_assistant.check_llm

Also runs from GitHub (Actions > Vérifier les clés LLM > Run workflow), with the keys stored as
repository secrets. Prints providers and models, never a key.
"""
from __future__ import annotations

import sys

from . import llm
from .db import init_db


def main() -> int:
    init_db()
    failures = 0
    for role in llm.ROLES:
        entries = llm.chain(role)
        if not entries:
            print(f"[--] {role}: aucune clé configurée pour ce rôle")
            continue
        try:
            answer = llm.ask(role, "Réponds seulement : OK", system="Tu es un test de connexion.")
        except llm.NoModelAvailable as e:
            failures += 1
            print(f"[KO] {role}: {e}")
            continue
        print(f"[OK] {role}: {answer.provider} / {answer.model} -> {answer.text.strip()[:40]!r}")
    if all(not llm.chain(role) for role in llm.ROLES):
        print("Aucune clé trouvée : ajoute au moins NVIDIA_API_KEY.")
        return 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
