"""The monthly e-mail from the command line (and from GitHub Actions, right after the monthly plan).

    python -m trade_assistant.report send              send the report of the latest plan
    python -m trade_assistant.report preview [file]    print the text, write the HTML to a file
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_engine, init_db
from . import content, mail, render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m trade_assistant.report")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("send", help="envoyer le rapport du dernier plan")
    preview = sub.add_parser("preview", help="afficher le rapport sans l'envoyer")
    preview.add_argument("file", nargs="?", default="rapport.html")
    args = parser.parse_args(argv)

    init_db()
    with Session(get_engine()) as session:
        subject, text, html = render.render(content.gather(session), get_settings().site_url)
    print(f"Objet : {subject}\n\n{text}")
    if args.command == "preview":
        Path(args.file).write_text(html, encoding="utf-8")
        print(f"HTML écrit dans {args.file}")
        return 0
    try:
        print(f"Envoyé à {mail.send(subject, text, html)}.")
    except mail.NotConfigured as e:
        print(e)  # not an error: the plan exists, only the e-mail is skipped
    except (OSError, mail.smtplib.SMTPException) as e:
        print(f"Échec de l'envoi : {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
