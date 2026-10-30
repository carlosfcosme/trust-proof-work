"""Public scorecard page (credential schemas section 5 rendering contract).

Self-contained HTML, no external assets. Renders the agent's DID and its
resolution, base vs effective tier with the reason for any drop, every
skill verdict with its cited findings, and the credential/settlement
state - including permanent Do-Not-Install marks.
"""
import html


def _e(x) -> str:
    return html.escape(str(x))


def render(agent_view: dict, audits: list[dict], credentials: list[dict],
           gauntlet: dict | None = None) -> str:
    a = agent_view
    rows = []
    for au in audits:
        finds = "".join(
            f"<li><b>{_e(f['ruleId'])}</b> ({_e(f['severity'])}) - "
            f"{_e(f['summary'])}<br><code>{_e(f['citation']['file'])}:"
            f"{_e(f['citation']['line'])}</code></li>"
            for f in au.get("findings", []))
        rows.append(
            f"<tr><td>{_e(au['skill'])}</td><td>{_e(au['verdict'])}</td>"
            f"<td><ul>{finds}</ul></td></tr>")
    cred_rows = "".join(
        f"<tr><td>{_e(' / '.join(c.get('type', [])))}</td>"
        f"<td>{_e(c.get('issuanceDate', ''))}</td>"
        f"<td>{_e(c.get('expirationDate', 'permanent'))}</td></tr>"
        for c in credentials)
    g = ""
    if gauntlet:
        g = (f"<h2>Audit benchmark (gauntlet, 20 fixtures)</h2>"
             f"<p>Baseline frozen machinery: {gauntlet['baseline_exact']}/20 "
             f"exact, burns caught {gauntlet['baseline_burns']}/6. "
             f"With the Day-4 rule fixes: {gauntlet['after_exact']}/20 exact, "
             f"burns caught {gauntlet['after_burns']}/6, clean false "
             f"positives {gauntlet['after_clean_fp']}/8.</p>")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Trust. Proof. Work. - Agent Scorecard</title>
<style>body{{font-family:system-ui;background:#0b1220;color:#e6edf3;margin:2rem}}
table{{border-collapse:collapse}}td,th{{border:1px solid #2a3a55;padding:.4rem .6rem;vertical-align:top}}
code{{color:#7ee787}}h1,h2{{color:#fff}}.tier{{font-size:1.4rem}}</style></head>
<body>
<h1>Trust. Proof. Work.</h1>
<p>The credit bureau, the safety inspector, and the escrow agent for the
agent economy. This page is the public trust scorecard for one agent:
its identity, its audited skills, and what it is allowed to do with money.</p>
<h2>Agent</h2>
<p>DID: <code>{_e(a['did'])}</code></p>
<p class="tier">Base tier T{a['base_tier']} &rarr; effective tier
<b>T{a['effective_tier']}</b> (per-job cap ${a['caps']['per_job']},
per-day cap ${a['caps']['per_day']})</p>
<p>{_e(a.get('tier_note', ''))}</p>
<h2>Skill audits</h2>
<table><tr><th>Skill</th><th>Verdict</th><th>Findings (with citations)</th></tr>
{''.join(rows)}</table>
{g}
<h2>Credentials</h2>
<table><tr><th>Type</th><th>Issued</th><th>Expires</th></tr>{cred_rows}</table>
</body></html>"""
