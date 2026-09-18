"""Build the standalone numerical-study page from recorded output."""
from pathlib import Path
from html import escape
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "artifacts/sequence-pair-analysis/summary.json"
data = json.loads(source.read_text(encoding="utf-8"))
data_rows = []
for regime, values in data["regimes"].items():
    for metric, value in values["paired_difference"].items():
        data_rows.append([regime, metric.replace("_", " "), f'{100*value["estimate"]:+.2f} pp', f'[{100*value["ci_low"]:.2f}, {100*value["ci_high"]:.2f}]'])
headers = ["Drift", "Metric", "Temporal − confidence", "95% interval"]
lead = "On unseen drift, temporal CRC has a +2.50 percentage-point difference in sequence false release. The interval includes zero."
explanation = "The analysis resamples both selectors together at the sequence level within each family. Coverage and correct accepted frames are reported alongside false release; discarding every frame therefore has zero measured utility."
limitation = "These are pointwise exploratory intervals for already-recorded synthetic H6 results. They do not prove validity under a new drift distribution."
command = "python scripts/analyze_sequence_pairs.py"
result = "360 paired sequences"
method = "12 dependent frames → sequence loss → family strata → 10,000 paired resamples"
output = ROOT / "web/public"
output.mkdir(parents=True, exist_ok=True)
downloads = output / "study-data"
downloads.mkdir(exist_ok=True)
shutil.copyfile(source, downloads / "summary.json")
shutil.copyfile(ROOT / "artifacts/confirmatory-h6/benchmark_h6.csv", downloads / "trials.csv")
table = "<thead><tr>" + "".join("<th>" + escape(str(x)) + "</th>" for x in headers) + "</tr></thead><tbody>"
for row in data_rows:
    table += "<tr>" + "".join("<td>" + escape(str(x)) + "</td>" for x in row) + "</tr>"
table += "</tbody>"
page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Temporal drift comparison · irforge-sim</title>
<style>
:root{{color-scheme:dark;--accent:#e7be83}}*{{box-sizing:border-box}}
body{{margin:0;background:#08281f;color:#e2ece5;font:16px/1.65 "Segoe UI Variable Text","Aptos",system-ui,sans-serif}}
main{{max-width:1120px;margin:auto;padding:36px 30px 80px}}
nav{{display:flex;justify-content:space-between;gap:24px;border-bottom:1px solid #416356;padding-bottom:20px}}
a{{color:var(--accent);text-underline-offset:5px}}nav a{{text-decoration:none}}.tag{{color:#a0b9ac;font-size:13px}}
header{{padding:62px 0 30px;max-width:840px}}h1{{font:500 clamp(36px,5vw,62px)/1.06 "Segoe UI Variable Display","Aptos Display",system-ui;letter-spacing:-.045em;margin:16px 0 22px}}
header p{{font-size:22px;color:#b6cbbf}}.result{{border-left:3px solid var(--accent);padding:5px 0 5px 24px;margin:22px 0 34px}}
.result strong{{font-size:30px;font-weight:500;color:var(--accent)}}.result p{{max-width:780px;margin:10px 0}}
section{{border-top:1px solid #416356;padding:24px 0}}h2{{font-size:20px;font-weight:500}}
.formula{{padding:18px;background:#12392c;border-radius:6px;font:14px/1.6 Consolas,monospace;color:var(--accent)}}
.table-scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th{{text-align:left;color:#a7c0b2;font-weight:500}}
td,th{{padding:13px 14px;border-bottom:1px solid #2c4e40}}td:not(:first-child){{font-variant-numeric:tabular-nums}}
tr:hover td{{background:#143b2c}}.note{{color:#abc3b5;max-width:800px}}code{{word-break:break-all}}.downloads{{display:flex;gap:24px;flex-wrap:wrap}}
details{{color:#96ad9f;font-size:13px;margin-top:30px}}summary{{cursor:pointer}}@media(max-width:600px){{main{{padding:22px 18px}}header{{padding-top:36px}}}}
</style></head><body><main>
<nav><a href="./">← irforge-sim</a><span class="tag">Exploratory paired analysis</span></nav>
<header><span class="tag">NUMERICAL STUDY / SEPTEMBER 2026</span><h1>Temporal drift comparison</h1><p>Resample sequences, preserve their shared errors.</p></header>
<div class="result"><strong>{escape(result)}</strong><p>{escape(lead)}</p></div>
<section><h2>Method</h2><p>{escape(explanation)}</p><p class="formula">{escape(method)}</p></section>
<section><h2>Recorded results</h2><div class="table-scroll"><table>{table}</table></div></section>
<section><h2>Interpretation</h2><p class="note">{escape(limitation)}</p></section>
<section><h2>Reproduce</h2><p class="formula">{escape(command)}<br>python scripts/render_study.py</p>
<div class="downloads"><a href="study-data/trials.csv" download>Row-level CSV</a><a href="study-data/summary.json" download>Summary JSON</a></div>
<details><summary>Source checksum</summary><p><code>{hashlib.sha256(source.read_bytes()).hexdigest()}</code></p></details></section>
</main></body></html>"""
(output / "study.html").write_text(page, encoding="utf-8")
print(output / "study.html")
