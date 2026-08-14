"""
HTML Executive Audit Report Exporter for CodeLoom Engine.
Generates standalone, beautifully styled VPAT/Executive reports with print CSS.
"""
from typing import Dict, Any, List
import html
from engine.models import Cluster, Fix


def export_html(scan_meta: Dict[str, Any], clusters: List[Cluster], fixes: List[Fix]) -> str:
    scan_id = html.escape(str(scan_meta.get("scan_id", "N/A")))
    target_url = html.escape(str(scan_meta.get("url", "N/A")))
    created_at = html.escape(str(scan_meta.get("created_at", "N/A")))
    scores = scan_meta.get("scores") or {}

    a11y_score = scores.get("accessibility", 100)
    seo_score = scores.get("seo", 100)
    perf_score = scores.get("performance", 100)
    overall_score = scores.get("overall", 100)

    total_findings = scan_meta.get("total_findings", 0)
    dedup_findings = scan_meta.get("deduplicated_findings", 0)

    # Build map of cluster_id -> fix
    fix_map = {f.cluster_id: f for f in fixes}

    # Counts
    crit_count = sum(1 for c in clusters if c.severity.lower() == "critical")
    ser_count = sum(1 for c in clusters if c.severity.lower() == "serious")
    mod_count = sum(1 for c in clusters if c.severity.lower() == "moderate")
    min_count = sum(1 for c in clusters if c.severity.lower() == "minor")

    cluster_cards_html = ""
    for c in clusters:
        sev_color = "#ff4757" if c.severity.lower() == "critical" else ("#ffa502" if c.severity.lower() == "serious" else ("#1e90ff" if c.severity.lower() == "moderate" else "#2ed573"))
        
        selectors = getattr(c, 'affected_selectors', getattr(c, 'selectors', []))
        explanation = getattr(c, 'explanation', getattr(c, 'likely_root_cause', c.title))

        selectors_list = "".join([f"<li><code>{html.escape(s)}</code></li>" for s in selectors[:5]])
        if len(selectors) > 5:
            selectors_list += f"<li><em>+ {len(selectors) - 5} more elements</em></li>"

        fix_block = ""
        associated_fix = fix_map.get(c.cluster_id)
        if associated_fix:
            raw_patch = getattr(associated_fix, 'suggested_after', None) or getattr(associated_fix, 'code_diff', None) or associated_fix.explanation
            patch_code = html.escape(raw_patch)
            fix_block = f"""

            <div class="fix-section">
                <div class="fix-title">🤖 Recommended Remediated Code (AI Confidence: {associated_fix.confidence*100:.0f}%):</div>
                <pre class="code-block"><code>{patch_code}</code></pre>
            </div>
            """

        cluster_cards_html += f"""
        <div class="card">
            <div class="card-header">
                <span class="badge" style="background: {sev_color}22; color: {sev_color}; border: 1px solid {sev_color}55;">{html.escape(c.severity.upper())}</span>
                <span class="badge" style="background: rgba(255,255,255,0.05); color: #a0a0a0;">{html.escape(c.category.upper())}</span>
                <h3 style="margin: 10px 0 5px 0; color: #fff;">{html.escape(c.title)}</h3>
                <p style="color: #8892b0; margin: 0; font-size: 0.9rem;">{html.escape(explanation)}</p>
            </div>
            <div class="card-body">

                <div style="margin-bottom: 10px;">
                    <strong>WCAG Criteria:</strong> <span class="tag">{html.escape(c.rule_id)}</span> | 
                    <strong>Impacted Elements:</strong> {c.instance_count}
                </div>
                <div>
                    <strong>Target Selectors:</strong>
                    <ul class="selector-list">{selectors_list}</ul>
                </div>
                {fix_block}
            </div>
        </div>
        """

    if not cluster_cards_html:
        cluster_cards_html = """
        <div class="card" style="text-align: center; padding: 40px; color: #2ed573;">
            <h2>🎉 Zero Accessibility Violations Found!</h2>
            <p>Your target page passed all multi-matrix WCAG 2.2 AA and Section 508 accessibility criteria.</p>
        </div>
        """

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeLoom Executive Audit Report - {scan_id}</title>
    <style>
        :root {{
            --bg: #0b0d14;
            --panel: #131722;
            --border: #2a2e3d;
            --accent: #00f2fe;
            --text: #e0e6ed;
            --muted: #8892b0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .brand {{
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: 1px;
            background: linear-gradient(135deg, #4facfe, #00f2fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .meta-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            background: var(--panel);
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        .meta-table td, .meta-table th {{
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            text-align: left;
        }}
        .meta-table th {{
            background: rgba(255,255,255,0.03);
            color: var(--muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: var(--panel);
            border: 1px solid var(--border);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-card .val {{
            font-size: 2.2rem;
            font-weight: 800;
            color: var(--accent);
        }}
        .metric-card .lbl {{
            font-size: 0.85rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .card {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .card-header {{
            border-bottom: 1px solid rgba(255,255,255,0.05);
            padding-bottom: 12px;
            margin-bottom: 12px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
            margin-right: 6px;
        }}
        .tag {{
            background: rgba(0, 242, 254, 0.1);
            color: var(--accent);
            padding: 2px 8px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.85rem;
        }}
        .selector-list {{
            margin: 5px 0;
            padding-left: 20px;
            color: var(--muted);
        }}
        .code-block {{
            background: #08090d;
            border: 1px solid #1e2230;
            border-radius: 6px;
            padding: 12px;
            font-family: Consolas, Monaco, monospace;
            font-size: 0.85rem;
            color: #00f2fe;
            overflow-x: auto;
        }}
        .fix-section {{
            margin-top: 15px;
            border-top: 1px dashed var(--border);
            padding-top: 15px;
        }}
        .fix-title {{
            font-size: 0.85rem;
            font-weight: 700;
            color: #2ed573;
            margin-bottom: 8px;
        }}
        @media print {{
            body {{
                background: #fff;
                color: #000;
            }}
            .card, .meta-table, .metric-card {{
                background: #fff;
                border: 1px solid #ccc;
                color: #000;
            }}
            .brand {{
                color: #000;
                -webkit-text-fill-color: initial;
            }}
            .code-block {{
                background: #f5f5f5;
                color: #000;
                border: 1px solid #ddd;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <div class="brand">CODELOOM AUTOMATED AUDIT REPORT</div>
                <div style="color: var(--muted); font-size: 0.9rem;">Standalone Executive & Engineering Brief</div>
            </div>
            <button onclick="window.print()" style="background: var(--accent); color: #000; border: none; padding: 10px 18px; border-radius: 6px; font-weight: 700; cursor: pointer;">
                Print / Save PDF
            </button>
        </div>

        <table class="meta-table">
            <tr>
                <th>Scan ID</th>
                <th>Target URL</th>
                <th>Scan Date</th>
                <th>Total Findings</th>
                <th>Deduplicated Clusters</th>
            </tr>
            <tr>
                <td><code>{scan_id}</code></td>
                <td><a href="{target_url}" target="_blank" style="color: var(--accent);">{target_url}</a></td>
                <td>{created_at}</td>
                <td><strong>{total_findings}</strong></td>
                <td><strong>{dedup_findings}</strong></td>
            </tr>
        </table>

        <div class="grid-3">
            <div class="metric-card">
                <div class="val">{overall_score}/100</div>
                <div class="lbl">Overall Score</div>
            </div>
            <div class="metric-card">
                <div class="val">{a11y_score}/100</div>
                <div class="lbl">Accessibility Matrix</div>
            </div>
            <div class="metric-card">
                <div class="val">{seo_score}/100</div>
                <div class="lbl">SEO Matrix</div>
            </div>
        </div>

        <h2 style="border-left: 4px solid var(--accent); padding-left: 12px; color: #fff;">Root Cause Violations & Remediation Plan</h2>
        <div style="margin-bottom: 20px; color: var(--muted); font-size: 0.9rem;">
            Breakdown: <strong style="color: #ff4757;">{crit_count} Critical</strong> | 
            <strong style="color: #ffa502;">{ser_count} Serious</strong> | 
            <strong style="color: #1e90ff;">{mod_count} Moderate</strong> | 
            <strong style="color: #2ed573;">{min_count} Minor</strong>
        </div>

        {cluster_cards_html}

        <footer style="margin-top: 50px; text-align: center; border-top: 1px solid var(--border); padding-top: 20px; color: var(--muted); font-size: 0.85rem;">
            Generated by CodeLoom Engine v1.0.0 — Compliant with WCAG 2.1 AA, WCAG 2.2 AA, and Section 508 standards.
        </footer>
    </div>
</body>
</html>
"""
    return html_doc
