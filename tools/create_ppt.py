"""Generate ASTRA SIH 2026 presentation from the template."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

prs = Presentation("SIH2026-IDEA-Presentation-Format.pptx")

# ─── Slide 1: Title Slide ─────────────────────────────────────
slide1 = prs.slides[0]
for shape in slide1.shapes:
    if shape.has_text_frame:
        text = shape.text_frame.text
        if "TITLE PAGE" in text:
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = "ASTRA"
            run.font.size = Pt(44)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
            p2 = shape.text_frame.add_paragraph()
            p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run()
            r2.text = "Adaptive Spectrum Threat Recognition & Analysis"
            r2.font.size = Pt(18)
            r2.font.color.rgb = RGBColor(0x4A, 0x6F, 0x8A)
        elif "Problem Statement ID" in text:
            shape.text_frame.clear()
            lines = [
                ("Problem Statement ID:", "26055"),
                ("Problem Statement Title:", "Smart Scan Strategy for Electronic Warfare"),
                ("Theme:", "Defense Technology"),
                ("PS Category:", "Software"),
                ("Team ID:", "MCS"),
                ("Team Name:", "Team MCS"),
            ]
            for i, (label, value) in enumerate(lines):
                if i == 0:
                    p = shape.text_frame.paragraphs[0]
                else:
                    p = shape.text_frame.add_paragraph()
                p.alignment = PP_ALIGN.LEFT
                r1 = p.add_run()
                r1.text = label + " "
                r1.font.size = Pt(14)
                r1.font.bold = True
                r1.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
                r2 = p.add_run()
                r2.text = value
                r2.font.size = Pt(14)
                r2.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)

# ─── Slide 2: Proposed Solution ────────────────────────────────
slide2 = prs.slides[1]
for shape in slide2.shapes:
    if shape.has_text_frame:
        text = shape.text_frame.text
        if "IDEA TITLE" in text:
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "ASTRA: Smart Scan Strategy for Electronic Warfare"
            r.font.size = Pt(28)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
        elif "Proposed Solution" in text or "Detailed explanation" in text:
            shape.text_frame.clear()
            bullets = [
                "THE PROBLEM:",
                "• ES receivers scan one band at a time — interception is a 2D search (right frequency + right time)",
                "• Current open-loop strategies use fixed pre-mission patterns; they waste time on clutter and miss new threats",
                "",
                "OUR SOLUTION — SmartScan:",
                "• Confidence-multiplexed adaptive scheduler with 5 behaviors: Recon, Cued Pursuit, Predict & Probe, Burst Characterisation, Value Rotation",
                "• Learns emitter rhythms online — no prior intelligence required",
                "• Predicts transmission windows and arrives early — interception becomes schedule, not luck",
                "• Self-validating: stale predictions auto-destruct after 5 misses",
                "",
                "KEY INNOVATIONS:",
                "• SNR + AOA fingerprinting separates co-channel emitters",
                "• Rayleigh significance testing for period estimation",
                "• KPP-gated Mission Effectiveness Score (defence T&E methodology)",
            ]
            for i, line in enumerate(bullets):
                if i == 0:
                    p = shape.text_frame.paragraphs[0]
                else:
                    p = shape.text_frame.add_paragraph()
                r = p.add_run()
                r.text = line
                r.font.size = Pt(11)
                if line.startswith("THE PROBLEM") or line.startswith("OUR SOLUTION") or line.startswith("KEY INNOV"):
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
                else:
                    r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

# ─── Slide 3: Technical Approach ───────────────────────────────
slide3 = prs.slides[2]
for shape in slide3.shapes:
    if shape.has_text_frame:
        text = shape.text_frame.text
        if "TECHNICAL APPROACH" in text:
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "TECHNICAL APPROACH"
            r.font.size = Pt(28)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
        elif "Technologies" in text or "Methodology" in text:
            shape.text_frame.clear()
            bullets = [
                "TECHNOLOGY STACK:",
                "• Core Engine: Python 3.12 + NumPy (simulation, scheduling, metrics)",
                "• ML: NumPy MLP (DQN), Rayleigh period estimator, UCB bandits, Q-learning",
                "• Backend: FastAPI + Uvicorn (REST API + Server-Sent Events)",
                "• Frontend: React 18 + TypeScript + Vite + Canvas API (radar visualization)",
                "• Desktop: PySide6 (Qt) with embedded Qt WebEngine",
                "• Database: SQLite (metrics persistence, mission history)",
                "• Packaging: PyInstaller + Inno Setup (signed Windows installer ~131 MB)",
                "",
                "ARCHITECTURE: 7-layer pipeline",
                "Environment → Receiver Physics → 7 Schedulers → Metrics → KPP Gate → MES Score → Live Arena",
                "",
                "EVALUATION:",
                "• 200-episode Monte Carlo with 95% confidence intervals",
                "• Paired permutation tests + Holm-Bonferroni correction (p < 1e-4)",
                "• Sensitivity sweep across bands, SNR, agility, density",
                "• 62 automated tests · Docker · Reproducible seeds",
            ]
            for i, line in enumerate(bullets):
                if i == 0:
                    p = shape.text_frame.paragraphs[0]
                else:
                    p = shape.text_frame.add_paragraph()
                r = p.add_run()
                r.text = line
                r.font.size = Pt(11)
                if line.startswith("TECHNOLOGY") or line.startswith("ARCHITECTURE") or line.startswith("EVALUATION"):
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
                else:
                    r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

# ─── Slide 4: Feasibility and Viability ────────────────────────
slide4 = prs.slides[3]
for shape in slide4.shapes:
    if shape.has_text_frame:
        text = shape.text_frame.text
        if "FEASIBILITY" in text:
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "FEASIBILITY AND VIABILITY"
            r.font.size = Pt(28)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
        elif "Analysis of" in text or "Potential challenges" in text:
            shape.text_frame.clear()
            bullets = [
                "FEASIBILITY — PROVEN BY RESULTS:",
                "• SmartScan achieves 95.0% threat coverage (vs 77.9% sequential) — exceeds 90% KPP gate",
                "• 2.1× higher reward per dwell than sequential sweep baseline",
                "• 58.1% prediction accuracy (vs 45.8% sequential) — above 50% KPP threshold",
                "• Only mission-capable scheduler in a field of 7 competing policies",
                "• Statistical significance at p < 1e-4 (Holm-corrected paired permutation tests)",
                "",
                "CHALLENGES & MITIGATIONS:",
                "• DQN struggles with sparse rewards → Correctly disclosed as negative result; SmartScan hybrid approach succeeds",
                "• No real SDR hardware validation → UDP bridge exists for future hardware integration",
                "• Synthetic scenarios only → All configs parameterized; real-world data calibration supported",
                "• Self-signed installer → Professional code signing available post-hackathon",
                "",
                "VIABILITY:",
                "• End-to-end prototype: simulation → scheduling → desktop app → presentation website",
                "• 62 automated tests · Docker one-command deployment · Full documentation",
            ]
            for i, line in enumerate(bullets):
                if i == 0:
                    p = shape.text_frame.paragraphs[0]
                else:
                    p = shape.text_frame.add_paragraph()
                r = p.add_run()
                r.text = line
                r.font.size = Pt(11)
                if line.startswith("FEASIBILITY") or line.startswith("CHALLENGES") or line.startswith("VIABILITY"):
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
                else:
                    r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

# ─── Slide 5: Impact and Benefits ──────────────────────────────
slide5 = prs.slides[4]
for shape in slide5.shapes:
    if shape.has_text_frame:
        text = shape.text_frame.text
        if "IMPACT" in text:
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "IMPACT AND BENEFITS"
            r.font.size = Pt(28)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
        elif "Potential impact" in text or "Benefits" in text:
            shape.text_frame.clear()
            bullets = [
                "DEFENSE IMPACT:",
                "• Earlier threat detection → more reaction time for countermeasures",
                "• 95% interception rate vs 78% conventional → near-complete situational awareness",
                "• No prior intelligence needed → works against unknown/new threats",
                "• Multi-receiver scaling: 3 receivers achieve 99.8% coverage",
                "",
                "TECHNOLOGY IMPACT:",
                "• Open-source ML-based ES scheduler — reproducible, auditable, extensible",
                "• Complete evaluation framework: Monte Carlo + significance testing + KPP gating",
                "• Real-time demonstration: two receivers on identical battlefields, side-by-side comparison",
                "",
                "SOCIAL & ECONOMIC BENEFITS:",
                "• Reduces operator workload — automated scheduling replaces manual band selection",
                "• Extends existing receiver capabilities via software upgrade (no hardware changes)",
                "• Educational value — demonstrates ML applied to real defense problems",
                "",
                "SCALABILITY:",
                "• Desktop app for field use, web dashboard for command center",
                "• UDP bridge for real SDR hardware integration",
                "• Configurable for different spectrum environments and threat types",
            ]
            for i, line in enumerate(bullets):
                if i == 0:
                    p = shape.text_frame.paragraphs[0]
                else:
                    p = shape.text_frame.add_paragraph()
                r = p.add_run()
                r.text = line
                r.font.size = Pt(11)
                if any(line.startswith(s) for s in ["DEFENSE", "TECHNOLOGY", "SOCIAL", "SCALABILITY"]):
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
                else:
                    r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

# ─── Slide 6: Research and References ──────────────────────────
slide6 = prs.slides[5]
for shape in slide6.shapes:
    if shape.has_text_frame:
        text = shape.text_frame.text
        if "RESEARCH" in text:
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "RESEARCH AND REFERENCES"
            r.font.size = Pt(28)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
        elif "Details / Links" in text:
            shape.text_frame.clear()
            bullets = [
                "KEY RESEARCH REFERENCES:",
                "• Siouris, G.M. — \"Engineering Handbook of Intelligent Aircraft Systems\" — ES receiver scheduling theory",
                "• Wiley, R.G. — \"Electronic Intelligence: The Analysis of Radar Signals\" — PDW analysis methodology",
                "• Pozza, L. et al. — \"Spectrum Sensing for Cognitive Radio: Architecture and Algorithms\" — bandit approaches",
                "• Sutton, R.S. & Barto, A.G. — \"Reinforcement Learning: An Introduction\" — Q-learning, DQN foundations",
                "",
                "DATASETS:",
                "• Turing Synthetic Radar Dataset (HuggingFace) — PDW calibration reference",
                "• Synthetic RF environment generator — deterministic, seed-reproducible scenarios",
                "",
                "METHODOLOGY REFERENCES:",
                "• DoD Directive 5000.01 — Key Performance Parameters and T&E methodology",
                "• Holm, S. — \"A Simple Sequentially Rejective Bonferroni Test\" — statistical correction",
                "• Rayleigh test for periodicity — period estimation significance testing",
                "",
                "PROJECT URL: github.com/RARPlayzDev/Astra",
            ]
            for i, line in enumerate(bullets):
                if i == 0:
                    p = shape.text_frame.paragraphs[0]
                else:
                    p = shape.text_frame.add_paragraph()
                r = p.add_run()
                r.text = line
                r.font.size = Pt(11)
                if any(line.startswith(s) for s in ["KEY RESEARCH", "DATASETS", "METHODOLOGY", "PROJECT"]):
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(0x12, 0x35, 0x4F)
                else:
                    r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

# Save
output_path = "ASTRA_SIH2026_Presentation.pptx"
prs.save(output_path)
print(f"Saved: {output_path}")
print(f"Slides: {len(prs.slides)}")
