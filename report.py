"""Downloadable, self-contained HTML reports with interactive Plotly charts."""
import html
from datetime import datetime, timezone


def export_report(title, sections):
    out = ['<!doctype html><html><head><meta charset="utf-8"><title>PrismForge report</title>',
           '<style>body{background:#0d1022;color:#e9eaf7;font:16px Arial;max-width:1100px;margin:40px auto;padding:20px}section{background:#181a35;border:1px solid #323653;border-radius:18px;padding:24px;margin:20px 0}h1{color:#a78bfa}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:12px}td,th{border:1px solid #444;padding:6px}a{color:#22d3ee}</style></head><body>',
           f'<h1>{html.escape(title)}</h1><p>Generated {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} | PrismForge AI</p>']
    include_js = True
    for section in sections:
        out.append('<section><h2>' + html.escape(section.get('title', 'Analysis')) + '</h2>')
        out.append('<pre>' + html.escape(section.get('text', '')) + '</pre>')
        if section.get('sql'):
            out.append('<h3>SQL evidence</h3><pre>' + html.escape(section['sql']) + '</pre>')
        fig = section.get('figure')
        if fig is not None:
            out.append(fig.to_html(full_html=False, include_plotlyjs=True if include_js else False))
            include_js = False
        frame = section.get('frame')
        if frame is not None:
            out.append(f'<p>Table preview: first {min(100, len(frame))} of {len(frame)} returned rows.</p>')
            out.append(frame.head(100).to_html(index=False, escape=True))
        out.append('</section>')
    return ('\n'.join(out) + '</body></html>').encode('utf-8')
