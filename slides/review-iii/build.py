"""Build the native PowerPoint layout for CA649 Review III."""

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pymupdf
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

SLIDES = Path(__file__).resolve().parents[1]
KIT = Path(os.environ.get("REPORT_KIT_DIR", Path.home() / "Desktop/projects/report-kit"))
sys.path.insert(0, str(KIT / "lib"))
from deck import contact_sheet, load_config, render_pdf, rendered_overflow

WIDTH, HEIGHT = 13.333, 7.5
BG, WHITE = "F6F8F7", "FFFFFF"
INK, MUTED, LINE = "102D33", "40575C", "CCDBD8"
DARK, LIGHT = "12363A", "CFDFDB"
TEAL, TEAL_PALE = "076659", "DBEFE8"
RED, RED_PALE = "992F35", "F8E5E3"
PURPLE, PURPLE_PALE = "593B87", "EEE8F7"
NAME = "MCP Metadata Integrity Gateway"


def rgb(value):
    return RGBColor.from_string(value)


def rect(slide, x, y, w, h, fill=WHITE, border=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, *(Inches(n) for n in (x, y, w, h)))
    shape._element.remove(shape._element.find(qn('p:style')))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    if border:
        shape.line.color.rgb = rgb(border)
        shape.line.width = Pt(0.8)
    else:
        shape.line.fill.background()
    return shape


def text(slide, x, y, w, h, content, size=18, color=INK, bold=False, center=False, href=None):
    box = slide.shapes.add_textbox(*(Inches(n) for n in (x, y, w, h)))
    frame = box.text_frame
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    for index, row in enumerate(content.split("\n")):
        para = frame.add_paragraph() if index else frame.paragraphs[0]
        para.alignment = PP_ALIGN.CENTER if center else PP_ALIGN.LEFT
        para.space_before = para.space_after = Pt(0)
        run = para.add_run()
        run.text = row
        if href:
            run.hyperlink.address = href
        run.font.name = "Arial"
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = rgb(color)
    return box


def line(slide, x1, y1, x2, y2, color=LINE, stroke=1, arrow=False):
    shape = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, *(Inches(n) for n in (x1, y1, x2, y2))
    )
    shape._element.remove(shape._element.find(qn('p:style')))
    shape.line.color.rgb = rgb(color)
    shape.line.width = Pt(stroke)
    if arrow:
        end = OxmlElement("a:tailEnd")
        end.set("type", "triangle")
        shape._element.spPr.get_or_add_ln().append(end)
    return shape


def arrow(slide, x1, y1, x2, y2, color=TEAL):
    line(slide, x1, y1, x2, y2, color, 2, arrow=True)


def label(slide, x, y, w, value, color, bg):
    rect(slide, x, y, w, 0.35, bg)
    text(slide, x + 0.05, y, w - 0.1, 0.35, value, 12, color, True, True)


def panel(slide, x, y, w, h, title, body="", fill=WHITE, accent=INK):
    rect(slide, x, y, w, h, fill, LINE if fill == WHITE else None)
    if body:
        text(slide, x + .17, y + .12, w - .34, .36, title, 19, accent, True)
        text(slide, x + .17, y + .49, w - .34, h - .62, body, 16, INK)
    else:
        text(slide, x + .12, y + .04, w - .24, h - .08, title, 19, accent, True, True)


def metric(slide, x, y, w, h, value, caption, fill=WHITE, accent=INK):
    rect(slide, x, y, w, h, fill, LINE if fill == WHITE else None)
    text(slide, x + .16, y + .07, w - .32, .60, value, 32, accent, True)
    text(slide, x + .16, y + .69, w - .32, h - .76, caption, 16, INK)


def base(prs, dark=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = rgb(DARK if dark else BG)
    return slide


def header(slide, category, headline):
    text(slide, .62, .30, 12.05, .28, category, 13, TEAL, True)
    text(slide, .62, .68, 12.05, .74, headline, 34, INK, True)
    line(slide, .62, 1.53, 12.71, 1.53)


def footer(slide, source):
    line(slide, .62, 6.97, 12.71, 6.97)
    text(slide, .62, 7.00, 12.06, .31, source, 12, MUTED)


def compact_flow(slide, x, y):
    items = [("Tool listing", WHITE, INK), ("Gateway", TEAL_PALE, TEAL), ("Agent", WHITE, INK)]
    for index, (title, fill, accent) in enumerate(items):
        col = x + index * 2.20
        panel(slide, col, y, 1.76, .68, title, fill=fill, accent=accent)
        if index < len(items) - 1:
            arrow(slide, col + 1.79, y + .34, col + 2.16, y + .34, "82C6B7")


def slide_1(prs, me):
    s = base(prs, dark=True)
    rect(s, 0, 0, .17, HEIGHT, "82C6B7")
    text(s, .78, .54, 11.75, .35, "CA649 · REVIEW III · 25 NOVEMBER 2026", 16, "A9DED3", True)
    text(s, .78, 1.28, 11.85, 1.63, "MCP Metadata\nIntegrity Gateway", 48, WHITE, True)
    text(s, .80, 3.02, 11.5, .45, "Pre-execution screening of tool metadata for LLM agents", 24, LIGHT)
    compact_flow(s, .81, 3.87)
    line(s, .80, 5.05, 12.53, 5.05, "527874")
    name = me.get("name", "[Student name]")
    roll = me.get("roll", "[Roll number]")
    guide = me.get("guide") or {}
    guide_name = guide.get("name", "[Project guide]")
    text(s, .80, 5.30, 5.6, .43, f"{name}  ·  {roll}", 22, WHITE, True)
    text(s, 6.75, 5.30, 5.65, .43, f"Guide  ·  {guide_name}", 22, WHITE, True)
    text(s, .80, 5.86, 11.7, .66, "Department of Computer Applications\nNational Institute of Technology, Tiruchirappalli", 17, LIGHT)


def slide_2(prs):
    s = base(prs)
    header(s, "PROBLEM AND OBJECTIVES", "The agent reads tool metadata before a call")
    for y, title, fill, accent, payload, agent in [
        (2.11, "Direct discovery", RED_PALE, RED, "Misleading tool description", "Agent reads it"),
        (3.30, "Screened discovery", TEAL_PALE, TEAL, "Gateway checks the same listing", "Agent gets filtered list"),
    ]:
        text(s, .66, y + .17, 1.75, .49, title, 16, accent, True)
        panel(s, 2.46, y, 1.85, .83, "MCP server")
        arrow(s, 4.36, y + .415, 4.74, y + .415, accent)
        panel(s, 4.80, y, 4.25, .83, payload, fill=fill, accent=accent)
        arrow(s, 9.10, y + .415, 9.56, y + .415, accent)
        panel(s, 9.62, y, 3.08, .83, agent)
    text(s, 4.82, 4.22, 7.80, .40, "Inspected fields  ·  Name  /  Description  /  Input schema", 16, MUTED)
    text(s, .66, 4.99, 12, .32, "Evaluation objectives", 17, TEAL, True)
    for x, title, body in [
        (.65, "Detect", "Metadata changes and capability mismatches"),
        (4.75, "Measure", "Effect on judged agent attack success"),
        (8.85, "Quantify", "Authentic tools removed and gateway latency"),
    ]:
        panel(s, x, 5.45, 3.85, 1.26, title, body)
    footer(s, "MCP tool specification [1] · Gateway design [3]")


def slide_3(prs):
    s = base(prs)
    header(s, "METHODOLOGY 1 / 2", "L1 and L2 control which tools are served")
    text(s, .68, 1.70, 11.8, .30, "Discovery response  ·  tools/list", 16, MUTED, True)
    panels = [
        (.68, 1.78, "Upstream\nMCP server", WHITE),
        (2.87, 2.39, "L1 pin check\nL2 consistency", TEAL_PALE),
        (5.67, 2.05, "Decision\nladder", TEAL_PALE),
        (8.13, 2.16, "Filtered\nlisting", TEAL_PALE),
        (10.70, 1.95, "Agent", WHITE),
    ]
    for i, (x, w, title, fill) in enumerate(panels):
        panel(s, x, 2.12, w, .89, title, fill=fill)
        if i + 1 < len(panels):
            arrow(s, x + w + .035, 2.56, panels[i + 1][0] - .04, 2.56)
    text(s, .68, 3.19, 11.8, .35, "L1  ·  Trust on first use. Pin the fingerprint, then compare it on later listings.", 16, MUTED)
    text(s, .68, 3.76, 12, .32, "Decision ladder  ·  Quarantine rules take priority", 17, TEAL, True)
    for x, title, body, fill, accent in [
        (.68, "SERVE TOOL", "Neither check requires removal.", TEAL_PALE, TEAL),
        (4.77, "REMOVE TOOL", "Isolated L2 flag or a changed pin. A changed pin needs reapproval.", RED_PALE, RED),
        (8.86, "QUARANTINE SERVER", "K = 2 L2 flags in a listing, or both an L1 mismatch and L2 flag on one tool.", RED_PALE, RED),
    ]:
        panel(s, x, 4.17, 3.78, 1.74, title, body, fill, accent)
    text(s, .68, 6.23, 11.94, .39, "At invocation, the proxy rejects calls to removed tools before forwarding.", 17, TEAL, True)
    footer(s, "Gateway ladder and stdio proxy [3]")


def slide_4(prs):
    s = base(prs)
    header(s, "METHODOLOGY 2 / 2", "Three experiments measure different outcomes")
    rows = [
        ("L1+L2 · ENFORCES", "Paired MCPTox response replay", "Judged attack success\nGateway off vs. on", TEAL, TEAL_PALE),
        ("L3 · ADVISORY", "Server-grouped training\nFrozen MCPTox holdout", "Additional flags among\ntools still served", PURPLE, PURPLE_PALE),
        ("UTILITY + L4", "External authentic listings\nSelected local review cases", "Tool availability and flags\nIllustrative L4 verdicts", PURPLE, PURPLE_PALE),
    ]
    for index, (tag, experiment, outcome, accent, fill) in enumerate(rows):
        y = 1.94 + index * 1.43
        rect(s, .68, y, 11.94, 1.18, WHITE, LINE)
        label(s, .89, y + .415, 2.23, tag, accent, fill)
        text(s, 3.36, y + .13, 4.35, .92, experiment, 20, INK, True)
        arrow(s, 7.90, y + .59, 8.50, y + .59, accent)
        text(s, 8.76, y + .12, 3.64, .94, outcome, 19)
    text(s, .68, 6.35, 11.95, .35, "L1+L2 sets admission. L3 screening and optional L4 review report findings.", 16, MUTED)
    footer(s, "MCPTox [2] · Frozen split and evaluation protocol [3]")


def slide_5(prs):
    s = base(prs)
    header(s, "RESULTS 1 / 3 · PRELIMINARY", "The gateway reduced judged attack success")
    text(s, .67, 1.73, 11.93, .35, "Qwen3 8B, thinking enabled, single paired run", 18, MUTED, True)
    rect(s, .67, 2.24, 7.90, 3.39, WHITE, LINE)
    text(s, .91, 2.41, 7.42, .35, "Judged attack success rate", 19, INK, True)
    start, width, scale = 2.84, 4.02, 25
    for tick in range(0, 26, 5):
        x = start + width * tick / scale
        line(s, x, 2.94, x, 4.84, LINE, .7)
        text(s, x - .20, 4.88, .40, .30, f"{tick}%", 12, MUTED, center=True)
    for y, title, count, fill in [(3.19, "Gateway off", 59, MUTED), (4.05, "L1+L2 on", 37, TEAL)]:
        percent = 100 * count / 300
        end = start + width * percent / scale
        text(s, .91, y, 1.79, .42, title, 17, INK, True)
        rect(s, start, y, end - start, .42, fill)
        text(s, end + .12, y, 8.42 - end - .12, .42, f"{count}/300  ({percent:.1f}%)", 17, INK, True)
    rect(s, 8.84, 2.24, 3.83, 3.39, TEAL_PALE)
    text(s, 9.10, 2.49, 3.30, .36, "Paired reduction", 19, TEAL, True)
    text(s, 9.10, 3.00, 3.30, .92, "7.3 pp", 48, TEAL, True)
    text(s, 9.10, 4.03, 3.30, .50, "95% CI  ·  3.3–11.3 pp", 19, TEAL, True)
    text(s, 9.10, 4.74, 3.30, .56, "Model responses judged offline", 16, INK)
    panel(s, .67, 5.79, 4.61, .96, "3/128 authentic removals", "Held-out authentic listings", WHITE)
    panel(s, 5.50, 5.79, 7.17, .96, "p95  ·  8.24 ms first sight  /  5.72 ms pinned",
          "2,250 listings per condition · excludes upstream transport", WHITE)
    footer(s, "Paired MCPTox replay [2, 3] · results/results.md and saved pair records [3]")


def slide_6(prs):
    s = base(prs)
    header(s, "RESULTS 2 / 3 · PRELIMINARY", "L3 flagged cases the baseline still served")
    cols = [(.67, 2.04), (3.05, 2.03), (5.42, 2.08)]
    for (x, w), title in zip(cols, ["Held-out total", "L1+L2 served", "L3 flags · advisory"], strict=True):
        text(s, x, 1.85, w, .35, title, 16, PURPLE if x > 5 else INK, True)
    rows = [
        [("498", "Poisoned cases"), ("341/498", "Still served"), ("340/341", "Flagged")],
        [("128", "Authentic tools"), ("125/128", "Still served"), ("1/125", "Flagged")],
    ]
    for i, row in enumerate(rows):
        y = 2.34 + i * 1.47
        for j, ((x, w), (value, caption)) in enumerate(zip(cols, row, strict=True)):
            color, fill = [(INK, WHITE), (TEAL, TEAL_PALE), (PURPLE, PURPLE_PALE)][j]
            metric(s, x, y, w, 1.18, value, caption, fill, color)
            if j < 2:
                arrow(s, x + w + .035, y + .58, cols[j + 1][0] - .035, y + .58, TEAL if j == 0 else PURPLE)

    rect(s, 7.91, 1.87, 4.76, 3.50, WHITE, LINE)
    text(s, 8.18, 2.05, 4.21, .43, "No reconstructed arguments", 21, INK, True)
    for y, count, total, category, paint in [
        (2.75, 492, 498, "poisoned examples", RED),
        (3.68, 8, 128, "authentic tools", TEAL),
    ]:
        text(s, 8.18, y, 4.20, .30, f"{count}/{total}  {category}", 17, INK, True)
        rect(s, 8.18, y + .40, 4.18, .19, "E3EAE8")
        rect(s, 8.18, y + .40, 4.18 * count / total, .19, paint)
    text(s, 8.18, 4.68, 4.20, .42, "All 340 additional poisoned flags came from this group.", 15, MUTED)
    text(s, .67, 5.79, 11.94, .36, "Frozen CPU TF–IDF classifier  ·  Threshold 0.5436877", 17, PURPLE, True)
    text(s, .67, 6.31, 11.94, .36, "Incremental effect on agent attack success remains unmeasured.", 17, INK)
    footer(s, "Held-out MCPTox [2] · results/l3_screening.md and frozen classifier [3]")


def slide_7(prs):
    s = base(prs)
    header(s, "RESULTS 3 / 3 · PRELIMINARY", "Both extra L3 flags were zero-parameter tools")
    text(s, .67, 1.83, 7.70, .31, "External cohort · 19 unfamiliar families · authentic tools only", 18, INK, True)
    metric(s, .67, 2.49, 2.24, 1.30, "334", "Authentic tools")
    line(s, 2.92, 3.14, 3.12, 3.14, TEAL, 2)
    line(s, 3.12, 3.14, 3.12, 4.70, RED, 2)
    arrow(s, 3.12, 3.14, 3.42, 3.14)
    arrow(s, 3.12, 4.70, 3.42, 4.70, RED)
    metric(s, 3.47, 2.49, 2.25, 1.30, "278/334", "Still served", TEAL_PALE, TEAL)
    metric(s, 3.47, 4.07, 2.25, 1.30, "56/334", "Removed by L1+L2", RED_PALE, RED)
    arrow(s, 5.76, 3.14, 6.18, 3.14, PURPLE)
    metric(s, 6.22, 2.49, 2.12, 1.30, "2/278", "Extra L3 flags\nAdvisory", PURPLE_PALE, PURPLE)
    line(s, 7.28, 3.80, 7.28, 4.05, PURPLE, 1.3)
    metric(s, 6.22, 4.07, 2.12, 1.30, "2/12", "Served zero-parameter tools", PURPLE_PALE, PURPLE)

    rect(s, 8.72, 1.82, 3.95, 3.55, WHITE, LINE)
    text(s, 8.93, 2.03, 3.51, .36, "Optional L4 review", 21, PURPLE, True)
    text(s, 8.93, 2.45, 3.50, .30, "Local Weather fixture · illustrative", 14, MUTED)
    panel(s, 8.94, 2.92, 3.51, .78, "Altered weather · flagged", fill=PURPLE_PALE, accent=PURPLE)
    panel(s, 8.94, 3.92, 3.51, .78, "Clean forecast · low risk", fill=PURPLE_PALE, accent=PURPLE)
    text(s, 8.94, 4.83, 3.49, .30, "Local Qwen3 8B · advisory", 14, MUTED)

    text(s, .67, 5.77, 11.94, .36, "Three server quarantines accounted for 52/56 removals.", 17, INK, True)
    text(s, .67, 6.31, 11.94, .36, "The authentic-only cohort measures availability and flags. Independent recall remains open.", 16, MUTED)
    footer(s, "results/l3_external_utility.md · Local L4 review records [3]")


def slide_8(prs):
    s = base(prs)
    header(s, "CONCLUSION AND PHASE II", "Each layer has a distinct next test")
    text(s, .67, 1.79, 5.70, .37, "Evidence today", 22, TEAL, True)
    text(s, 6.70, 1.79, 5.70, .37, "Phase II tests", 22, INK, True)
    rows = [
        ("L1+L2 · Measured baseline", "Pin changes detected locally.\nPaired replay measured a reduction.",
         "Repeat the paired comparison", "Use L1+L2 as the enforced baseline."),
        ("L3 · Strong MCPTox screening", "Schema imbalance limits generalization.",
         "Validate before enforcing", "Test independent labeled metadata with populated schemas, then measure paired impact."),
        ("L4 · Working local review", "Structured verdicts on selected cases.",
         "Evaluate routed cases", "Measure accuracy, latency and added value."),
    ]
    for i, (title, body, next_title, next_body) in enumerate(rows):
        y = 2.30 + i * 1.43
        panel(s, .67, y, 5.47, 1.19, title, body, TEAL_PALE if i == 0 else PURPLE_PALE, TEAL if i == 0 else PURPLE)
        arrow(s, 6.20, y + .60, 6.62, y + .60)
        panel(s, 6.70, y, 5.96, 1.19, next_title, next_body)
    footer(s, "Phase II evaluation plan · CA649 rough thesis [3]")


def slide_9(prs):
    s = base(prs)
    text(s, .62, .68, 12.05, .74, "References", 34, INK, True)
    line(s, .62, 1.53, 12.71, 1.53)
    entries = [
        ("[1]", "Model Context Protocol Specification: Tools",
         "Model Context Protocol, specification revision 2025-11-25.",
         "modelcontextprotocol.io/specification/2025-11-25/server/tools",
         "https://modelcontextprotocol.io/specification/2025-11-25/server/tools"),
        ("[2]", "MCPTox: A Benchmark for Tool Poisoning on Real-World MCP Servers",
         "Z. Wang et al., Proceedings of the AAAI Conference on Artificial Intelligence,\nvol. 40, no. 42, pp. 35811–35819, 2026.",
         "doi:10.1609/aaai.v40i42.40895", "https://doi.org/10.1609/aaai.v40i42.40895"),
        ("[3]", "MCP Metadata Integrity Gateway · Review III evidence",
         "S. Sharma, implementation and results, November 2026. CA649 rough thesis,\nresults/results.md, results/l3_screening.md, results/l3_external_utility.md.",
         "github.com/Doffcode/mcp-gateway", "https://github.com/Doffcode/mcp-gateway"),
    ]
    for i, (number, title, facts, url, href) in enumerate(entries):
        y = 1.77 + i * 1.64
        text(s, .67, y + .05, .64, .39, number, 20, TEAL, True)
        text(s, 1.39, y, 11.12, .40, title, 20, INK, True)
        text(s, 1.39, y + .44, 11.12, .57, facts, 16, MUTED)
        text(s, 1.39, y + 1.04, 11.12, .30, url, 15, TEAL, href=href)
        if i < 2:
            line(s, .67, y + 1.50, 12.67, y + 1.50)


def slide_10(prs):
    s = base(prs, dark=True)
    rect(s, 0, 0, .17, HEIGHT, "82C6B7")
    text(s, .81, 1.38, 11.7, .98, "Thank you", 57, WHITE, True)
    text(s, .81, 2.70, 11.7, .45, NAME, 26, LIGHT)
    compact_flow(s, .81, 3.68)
    text(s, .81, 5.37, 11.7, .44, "Questions  ·  3 minutes", 21, "A9DED3", True)


def verify(notes, pdf):
    timings = [int(m) * 60 + int(s) for m, s in re.findall(r"^## \d+ · (\d+):(\d\d)$", notes, re.M)]
    assert len(timings) == 10 and sum(timings) == 12 * 60
    assert sum(timings[4:7]) == 6 * 60 and timings[5] == max(timings[4:7])
    if pdf is None:
        return
    with pymupdf.open(pdf) as doc:
        assert len(doc) == 10, "PDF slide count"
        required = {
            1: ["Review III".upper(), "Integrity Gateway"],
            3: ["QUARANTINE SERVER", "K = 2", "Trust on first use"],
            5: ["59/300", "19.7%", "37/300", "12.3%", "7.3 pp", "3.3–11.3 pp", "3/128", "8.24 ms", "5.72 ms"],
            6: ["340/341", "1/125", "492/498", "8/128", "0.5436877"],
            7: ["334", "Authentic tools", "56/334", "278/334", "2/278", "2/12", "low risk"],
            9: ["10.1609/aaai.v40i42.40895"],
        }
        for index, phrases in required.items():
            page = doc[index - 1].get_text()
            assert all(phrase in page for phrase in phrases), (index, page)
    issues = rendered_overflow(pdf, 6.95 * 72)
    assert not issues, issues


def main():
    out = SLIDES / "out"
    out.mkdir(exist_ok=True)
    source = Path(__file__).with_name("speaker-notes.md").read_text()
    blocks = re.split(r"^## (\d+ · \d+:\d\d)\n", source, flags=re.M)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(WIDTH), Inches(HEIGHT)
    prs.core_properties.title = NAME
    prs.core_properties.subject = "CA649 Review III"
    me = load_config(SLIDES)["me"]
    prs.core_properties.author = me.get("name", "CA649")
    slide_1(prs, me)
    for draw in (slide_2, slide_3, slide_4, slide_5, slide_6, slide_7, slide_8, slide_9, slide_10):
        draw(prs)
    assert len(prs.slides) == 10 and len(blocks) == 21
    for i, slide in enumerate(prs.slides):
        timing, body = blocks[1 + 2 * i:3 + 2 * i]
        slide.notes_slide.notes_text_frame.text = f"Slide {timing}\n\n{body.strip()}"
    path = out / "review-iii.pptx"
    prs.save(path)
    with tempfile.TemporaryDirectory(prefix="review-iii-") as temporary:
        pdf, warning = render_pdf(path, Path(temporary))
        verify(source, pdf)
        if pdf:
            shutil.copy2(pdf, out / pdf.name)
            contact_sheet(pdf, out / "review-iii-preview.png", cols=2, dpi=64)
        elif warning:
            print(warning)
    print(f"Built and checked {path}")


if __name__ == "__main__":
    main()
