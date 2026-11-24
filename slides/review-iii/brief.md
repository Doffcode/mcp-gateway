# CA649 Review III presentation brief

Build a presentation-ready, editable 16:9 PowerPoint for 25 November 2026 at NIT Tiruchirappalli. Present the current project as a completed Review III prototype. Use measured results from the rough thesis and saved project evidence. Describe independent detection, L3 enforcement, and L4 evaluation as Phase II experiments with explicit outcomes to measure. Reserve 12 minutes for the presentation and fixture walkthrough, then 3 minutes for examiner questions.

| Slide | Takeaway and primary visual | Time |
|---|---|---:|
| 1 | Project title, verified academic details, and a small listing-to-gateway-to-agent diagram | 0:35 |
| 2 | Why metadata must be checked before the agent reads it. Show unfiltered and screened discovery, the three inspected fields, and measurable objectives | 1:00 |
| 3 | L1 and L2 enforce admission. Show the real discovery path, first-sight pinning, and the serve, remove, and quarantine rules at K=2 | 1:10 |
| 4 | Three complementary experiments measure response outcomes, screening, and authentic-tool utility plus local review. Mark who enforces and who advises | 1:00 |
| 5 | Results 1 of 3. A zero-based paired comparison shows 59/300 versus 37/300 judged successes and a 7.3 pp reduction (95% CI 3.3–11.3 pp). Show held-out availability and proxy overhead alongside it | 1:45 |
| 6 | Results 2 of 3. Show the two held-out L3 flows with real denominators and put schema missingness next to them. This is the longest results explanation | 2:25 |
| 7 | Results 3 of 3. Show external authentic-only availability as a branch and L3 flags as a subset of served tools. Show the two illustrative Weather L4 verdicts | 1:50 |
| 8 | Pair completed evidence with three specific Phase II tests. Treat measured baseline, generalization, and routed review as separate questions | 0:45 |
| 9 | Cite only the MCP tool specification, MCPTox, and the repository evidence used on slides | 0:10 |
| 10 | Thank the panel and run the prepared Weather-only proxy walkthrough before the 3-minute Q&A | 1:20 |

Use native shapes for flows, state labels and chart bars. Write evidence denominators on the slide, and use speaker notes for caveats and examiner questions. Label model-output replay, metadata screening, and live fixture evidence so the panel can tell them apart. Distinguish the reported headline ASR from the rough-thesis audit of the nine judged successes after the poisoned tool was removed.

## Build and editing

Open `slides/out/review-iii.pptx` to edit in PowerPoint. To rebuild the native diagrams and slide layout, edit `build.py` and `speaker-notes.md` in this directory. From the repository root, use the Python environment in the installed Report Kit. The local checkout uses `~/Desktop/projects/report-kit/.venv/bin/python slides/review-iii/build.py`. Set `REPORT_KIT_DIR` if Report Kit is installed elsewhere. The builder writes the PowerPoint and, when LibreOffice is available, a PDF preview. The earlier Review II Report Kit deck keeps its original sources and output paths.
