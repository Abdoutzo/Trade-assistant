"""The monthly e-mail as plain text and HTML (inline styles: e-mail clients ignore stylesheets)."""
from __future__ import annotations

from html import escape

from .content import month_label, subject

ACTION_LABELS = {"keep": ("Garder", "#475569", "#f1f5f9"), "update": ("Modifier", "#92400e", "#fef3c7"),
                 "create": ("Créer", "#065f46", "#d1fae5"), "delete": ("Supprimer", "#991b1b", "#fee2e2")}
DISCLAIMER = ("Outil personnel d'aide à la décision, pas un conseil en investissement : tu restes seul décideur, "
              "et tout investissement en actions comporte un risque de perte en capital.")


def eur(x: float | None, digits: int = 0) -> str:
    if x is None:
        return "n.d."
    return f"{x:,.{digits}f} €".replace(",", " ").replace(".", ",")


def pct(x: float | None) -> str:
    return "n.d." if x is None else f"{x * 100:+.1f} %".replace(".", ",")


def _link(site: str, path: str) -> str:
    return f"{site.rstrip('/')}{path}" if site else ""


def _sections(report: dict, site: str) -> list[tuple[str, list[str], str]]:
    """(title, text lines, html body) for each part of the e-mail."""
    out = []
    plan, pf = report["plan"], report["portfolio"]

    lines = [f"Valeur : {eur(pf['total_value'])} pour {eur(pf['contributions'])} versés "
             f"({'+' if pf['gain'] >= 0 else ''}{eur(pf['gain'])}, "
             f"{pct(pf['gain'] / pf['contributions']) if pf['contributions'] else 'n.d.'})."]
    if pf["core_weight"] is not None:
        lines.append(f"Part de l'ETF monde : {pf['core_weight'] * 100:.0f} % (cible {pf['core_target'] * 100:.0f} %).")
    rows = "".join(f"<tr><td style='padding:4px 0'>{escape(p['name'])}</td>"
                   f"<td style='text-align:right'>{p['quantity']:g}</td>"
                   f"<td style='text-align:right'>{eur(p['value'])}</td>"
                   f"<td style='text-align:right;color:{'#047857' if (p['gain'] or 0) >= 0 else '#b91c1c'}'>"
                   f"{pct(p['gain_pct'])}</td></tr>" for p in pf["positions"])
    lines += [f"- {p['name']} : {p['quantity']:g} part(s), {eur(p['value'])} ({pct(p['gain_pct'])})"
              for p in pf["positions"]]
    html = "".join(f"<p style='margin:4px 0'>{escape(line)}</p>" for line in lines[:2])
    if rows:
        html += ("<table style='width:100%;border-collapse:collapse;font-size:14px;margin-top:8px'>"
                 "<tr style='color:#64748b;font-size:12px'><td>Ligne</td><td style='text-align:right'>Parts</td>"
                 f"<td style='text-align:right'>Valeur</td><td style='text-align:right'>+/-</td></tr>{rows}</table>")
    else:
        html += "<p style='color:#64748b'>Aucun achat enregistré pour l'instant.</p>"
    out.append(("Ton portefeuille", lines, html))

    if plan is None:
        out.append(("Plan du mois", ["Aucun plan préparé pour l'instant."], "<p>Aucun plan préparé pour l'instant.</p>"))
        return out

    status = {"draft": "brouillon, à valider sur le site", "approved": "validé", "rejected": "refusé",
              "replaced": "remplacé"}.get(plan["status"], plan["status"])
    lines = [f"Statut : {status}."]
    if plan.get("trade_plans"):
        lines.append("Rien à changer : tes plans en cours correspondent." if not report["changes"]
                     else "Ce qu'il faut faire dans Trade Republic :")
        rows = ""
        actions = {a["isin"]: a for a in plan.get("actions", [])}
        for p in plan["trade_plans"]:
            kind = actions.get(p["isin"], {}).get("kind", "keep")
            label, color, background = ACTION_LABELS[kind]
            lines.append(f"- [{label}] {p['name']} : {eur(p['amount'])} {p['frequency_label']}")
            rows += (f"<tr><td style='padding:4px 0'><span style='background:{background};color:{color};"
                     f"font-size:11px;padding:1px 6px;border-radius:4px'>{label}</span> {escape(p['name'])}</td>"
                     f"<td style='text-align:right;font-weight:600'>{eur(p['amount'])}</td>"
                     f"<td style='padding-left:12px'>{escape(p['frequency_label'])}</td></tr>")
        for a in plan.get("actions", []):
            if a["kind"] == "delete":
                lines.append(f"- [Supprimer] {a['text']}")
                rows += f"<tr><td colspan='3' style='padding:4px 0;color:#991b1b'>{escape(a['text'])}</td></tr>"
        lines += [f"  ({n})" for n in plan.get("plan_notes", [])]
        html = (f"<p style='margin:4px 0'>{escape(lines[0])} {escape(lines[1])}</p>"
                f"<table style='width:100%;border-collapse:collapse;font-size:14px'>{rows}</table>"
                + "".join(f"<p style='margin:4px 0;font-size:12px;color:#64748b'>{escape(n)}</p>"
                          for n in plan.get("plan_notes", [])))
    else:
        lines += [f"- {o['name']} : {eur(o['amount'])} par mois" for o in plan.get("orders", [])]
        html = "".join(f"<p style='margin:4px 0'>{escape(line)}</p>" for line in lines)
    url = _link(site, "/plan")
    if plan["status"] == "draft":
        lines.append(f"Valide ou refuse le plan sur le site{' : ' + url if url else ''}.")
        html += (f"<p style='margin:12px 0'><a href='{escape(url)}' style='background:#0f766e;color:#fff;"
                 "padding:8px 14px;border-radius:6px;text-decoration:none'>Ouvrir le plan du mois</a></p>"
                 if url else "<p>Valide ou refuse le plan sur le site.</p>")
    out.append((f"Plan de {month_label(plan['month'])}", lines, html))

    decision = []
    if plan.get("summary"):
        decision.append(plan["summary"])
    if plan.get("fallback_reason"):
        decision.append(plan["fallback_reason"])
    if plan.get("change_my_mind"):
        decision.append(f"Ce qui ferait changer d'avis : {plan['change_my_mind']}")
    if decision:
        out.append(("La décision de l'agent", decision,
                    "".join(f"<p style='margin:6px 0'>{escape(d)}</p>" for d in decision)))

    if report["objections"]:
        lines = [f"- {o['name']} : {o['text']}" for o in report["objections"]]
        out.append(("Objections graves de l'avocat du diable", lines,
                    "".join(f"<p style='margin:6px 0'><b>{escape(o['name'])}</b> : {escape(o['text'])}</p>"
                            for o in report["objections"])))

    if report["alerts"]:
        lines = [f"- {a['company']} : {a['title']}" for a in report["alerts"]]
        out.append(("Alertes du mois", lines,
                    "".join(f"<p style='margin:6px 0'><b>{escape(a['company'])}</b> : {escape(a['title'])}</p>"
                            for a in report["alerts"])))

    learn, html = [], ""
    if plan.get("lesson"):
        lesson = plan["lesson"]
        learn.append(f"Leçon du mois (rédigée par l'IA, peut contenir des erreurs) : {lesson['title']}. {lesson['text']}")
        html += (f"<p style='margin:6px 0'><b>{escape(lesson['title'])}</b> "
                 "<span style='font-size:11px;color:#6d28d9'>rédigée par l'IA, peut contenir des erreurs</span></p>"
                 f"<p style='margin:6px 0'>{escape(lesson['text'])}</p>")
    nxt = report["guide_next"]
    if nxt:
        url = _link(site, f"/guide/{nxt['id']}")
        line = (f"Guide : {report['guide_read']}/{report['guide_total']} chapitres lus. Prochain : "
                f"« {nxt['title']} » ({nxt['minutes']} min)")
        learn.append(line + (f" : {url}" if url else "."))
        html += (f"<p style='margin:6px 0'>{escape(line)}"
                 + (f" : <a href='{escape(url)}'>le lire</a>" if url else ".") + "</p>")
    if learn:
        out.append(("Apprendre", learn, html))
    return out


def render(report: dict, site: str = "") -> tuple[str, str, str]:
    """(subject, text, html)."""
    sections = _sections(report, site)
    footer = ("Après tes achats, enregistre-les : Portefeuille > Transactions sur le site, ou GitHub > Actions > "
              "« Enregistrer un achat ».")
    text = "\n\n".join(f"{title.upper()}\n" + "\n".join(lines) for title, lines, _ in sections)
    text += f"\n\n{footer}\n\n{DISCLAIMER}\n"
    body = "".join(f"<h2 style='font-size:16px;margin:24px 0 8px;color:#0f172a'>{escape(title)}</h2>{html}"
                   for title, _, html in sections)
    html = (
        "<div style='font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:640px;margin:auto;"
        "color:#334155;font-size:14px;line-height:1.5'>"
        f"<h1 style='font-size:20px;color:#0f766e;margin-bottom:0'>{escape(subject(report))}</h1>{body}"
        f"<p style='margin-top:24px'>{escape(footer)}</p>"
        f"<p style='font-size:12px;color:#94a3b8;margin-top:24px'>{escape(DISCLAIMER)}</p></div>"
    )
    return subject(report), text, html
