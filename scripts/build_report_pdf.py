"""ReportLab Academic PDF Report Generator for NUS DSA5101.

Strictly adheres to official formatting specifications:
- A4 page size (595.28 x 841.89 pt)
- Margins >= 2.0 cm (56.7 pt) on all sides (printable width: 481.88 pt)
- Body text font >= 10 pt Times-Roman with proportional leading (13.5 pt)
- Main report (Sections 1-6 + opening summary table) <= 8 pages (Pages 1-7)
- References on a separate final page (Page 8), excluded from the 8-page count
- No appendices
- Selectable PDF text and table content
- Dynamic "Page X of Y" page numbering with section labels
- High-resolution embedded figures with captions kept together
- Crisp mathematically rendered display equations (generated via mathtext)
- Pure HTML entity formatting for all inline math (zero raw LaTeX symbols)
- Anonymous submission: NUS Matriculation A0352547Y, zero personal names
"""

from __future__ import annotations

import os
from pathlib import Path
from PIL import Image as PILImage

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class MarkReferencesPage(Flowable):
    """Zero-size flowable to dynamically record the references start page."""

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        NumberedCanvas.references_start_page = self.canv._pageNumber


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page count."""

    references_start_page = 9999

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(
                56.7,
                841.89 - 38,
                "DSA5101 Project: Beyond Department Boundaries — Email Network Analysis",
            )
            self.drawRightString(
                595.28 - 56.7,
                841.89 - 38,
                "NUS Matriculation: A0352547Y",
            )
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(56.7, 841.89 - 42, 595.28 - 56.7, 841.89 - 42)

        # Running Footer (all pages)
        page_str = f"Page {self._pageNumber} of {page_count}"
        if self._pageNumber >= NumberedCanvas.references_start_page:
            page_label = f"{page_str} (References — Excluded from 8-Page Limit)"
        else:
            page_label = f"{page_str} (Main Report)"

        self.drawString(56.7, 34, "National University of Singapore — Master of Science in Data Science")
        self.drawRightString(595.28 - 56.7, 34, page_label)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(56.7, 44, 595.28 - 56.7, 44)

        self.restoreState()


def ensure_display_equations() -> dict[str, Path]:
    """Generate high-resolution display equation images using Matplotlib mathtext."""
    eq_dir = Path("reports/equations")
    eq_dir.mkdir(parents=True, exist_ok=True)

    eq_specs = {
        "eq1_pagerank": (
            r"\mathbf{r} = d \, \mathbf{P}^T \mathbf{r} + \left( d \, \frac{\mathbf{r}^T \mathbf{d}_{\mathrm{dangle}}}{N} + \frac{1 - d}{N} \right) \mathbf{1}",
            15, (7.2, 1.1)
        ),
        "eq2_modularity": (
            r"Q = \frac{1}{2m} \sum_{i,j} \left( A_{ij} - \gamma \, \frac{k_i k_j}{2m} \right) \delta(c_i, c_j)",
            15, (6.8, 1.1)
        ),
        "eq3_conductance": (
            r"\phi(S) = \frac{|\partial(S)|}{\min\left( \mathrm{vol}(S), \; \mathrm{vol}(V \setminus S) \right)}",
            15, (6.5, 1.1)
        ),
        "eq4_boundary": (
            r"\mathrm{CrossCount}(v) = |\{u \in N(v) : c_u \neq c_v\}|, \quad \mathrm{CrossFraction}(v) = \frac{\mathrm{CrossCount}(v)}{k_v}",
            13.5, (7.8, 1.1)
        ),
        "eq5_null_model": (
            r"p_{\mathrm{null}} = \frac{1}{N(N - 1)} \sum_{d=0}^{41} s_d (s_d - 1)",
            15, (6.2, 1.1)
        ),
    }

    out_paths = {}
    for name, (formula, fsize, fsize_inch) in eq_specs.items():
        out_file = eq_dir / f"{name}.png"
        fig, ax = plt.subplots(figsize=fsize_inch)
        ax.text(0.5, 0.5, f"${formula}$", fontsize=fsize, ha="center", va="center")
        ax.axis("off")
        plt.savefig(out_file, dpi=300, bbox_inches="tight", pad_inches=0.06, facecolor="white")
        plt.close(fig)
        out_paths[name] = out_file

    return out_paths


def make_equation_flowable(eq_path: Path, eq_num: str, printable_width: float, target_width: float = 330.0) -> Table:
    """Create a publication-grade centered equation table with a right-aligned equation number."""
    im = PILImage.open(eq_path)
    aspect = im.width / im.height
    target_height = target_width / aspect

    eq_img = Image(str(eq_path), width=target_width, height=target_height)

    num_style = ParagraphStyle(
        "EqNum",
        fontName="Times-Bold",
        fontSize=10,
        leading=12,
        alignment=2,  # Right-aligned
        textColor=colors.HexColor("#1A202C"),
    )
    num_p = Paragraph(f"<b>({eq_num})</b>", num_style)

    left_space = (printable_width - target_width - 40.0) / 2.0
    right_space = left_space

    tbl_data = [["", eq_img, num_p]]
    tbl = Table(tbl_data, colWidths=[left_space, target_width, 40.0 + right_space])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tbl


def build_pdf_report(output_filename: str = "report.pdf") -> Path:
    output_path = Path(output_filename)

    # 1. Ensure equation images exist
    eq_paths = ensure_display_equations()

    # 2. Page Geometry: A4 (595.28 x 841.89 pt) with exact 2.0 cm (56.7 pt) margins
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=56.7,
        rightMargin=56.7,
        topMargin=56.7,
        bottomMargin=56.7,
    )

    printable_width = 595.28 - 2 * 56.7  # 481.88 pt (6.69 inches)

    # 3. Typography Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15.5,
        leading=19,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=4,
        alignment=0,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=7,
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14.5,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=10,
        leading=13.5,
        textColor=colors.HexColor("#1A202C"),
        alignment=4,  # Justified
        spaceAfter=4.5,
    )

    caption_style = ParagraphStyle(
        "FigCaption",
        parent=styles["Normal"],
        fontName="Times-Italic",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#2D3748"),
        spaceBefore=3,
        spaceAfter=5,
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=8.2,
        leading=10.5,
        textColor=colors.HexColor("#1A202C"),
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Times-Bold",
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=table_cell,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = []

    # =========================================================================
    # PAGE 1: HEADER, SUMMARY TABLE, SECTION 1
    # =========================================================================
    story.append(Paragraph("Beyond Department Boundaries: Centrality and Communication Communities in an Email Network", title_style))
    story.append(Paragraph("<b>Course:</b> DSA5101 Introduction to Big Data &nbsp;|&nbsp; <b>Evaluation:</b> Anonymous Submission &nbsp;|&nbsp; <b>NUS Matriculation:</b> A0352547Y", subtitle_style))

    summary_data = [
        [Paragraph("Project Title", table_header), Paragraph("Beyond Department Boundaries: Centrality and Communication Communities in an Email Network", table_cell_bold)],
        [Paragraph("Dataset & Source", table_header), Paragraph("Email-Eu-core network, Stanford Network Analysis Platform (SNAP) (1,005 members, 42 departments)", table_cell)],
        [Paragraph("Algorithm Classes", table_header), Paragraph("1. PageRank Centrality (Lecture 6)<br/>2. Graph Clustering / Louvain Community Detection (Lecture 7)", table_cell)],
        [Paragraph("Research Question", table_header), Paragraph("To what extent do emergent communication communities align with formal department boundaries, and what structural roles do highly central individuals play in connecting disparate communities?", table_cell)],
    ]
    summary_tbl = Table(summary_data, colWidths=[115, printable_width - 115])
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1A365D")),
        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#F7FAFC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_tbl)
    story.append(Spacer(1, 6))

    story.append(Paragraph("1 Research question and dataset", h1_style))
    story.append(Paragraph(
        "Formal organizational charts reflect institutional hierarchies, administrative responsibilities, and official reporting channels. However, day-to-day operational exchange, collaboration, and information dissemination frequently transcend designated organizational units. Investigating whether emergent communication clusters mirror administrative boundaries—and how centrally positioned individuals bridge or reinforce those clusters—provides critical insights into organizational functioning, cross-departmental silos, and coordination bottlenecks.",
        body_style
    ))
    story.append(Paragraph(
        "This project investigates the <b>Email-Eu-core</b> network published by the Stanford Network Analysis Platform (SNAP) [1]. Generated from email logs of a large European research institution over an 18-month observation window, the dataset captures interactions among researchers, staff, and leadership. Crucially, each individual is labeled with one of 42 ground-truth administrative departments. The network contains 1,005 institution members and 25,571 directed edges (<i>u</i>, <i>v</i>), representing at least one email sent from individual <i>u</i> to individual <i>v</i>. Edge weights representing email frequencies are not provided; edges indicate binary reachability.",
        body_style
    ))
    story.append(Paragraph(
        "We formalize three coherent research questions: "
        "<br/>• <b>RQ1 (Prominence vs. Popularity):</b> How does directed PageRank centrality differ from simple in-degree popularity, and what topological mechanisms govern ranking disagreements? "
        "<br/>• <b>RQ2 (Community-Department Alignment):</b> Do unsupervised communication communities discovered via Louvain modularity optimization follow the 42 administrative department boundaries? "
        "<br/>• <b>RQ3 (Role of Central Individuals & Degree Confounding):</b> Do structurally prominent individuals act as cross-community boundary spanners or insular internal hubs, and does PageRank provide structural information beyond total node degree?",
        body_style
    ))
    story.append(Paragraph(
        "By answering these questions using rigorous graph algorithms, statistical null models, and degree-adjusted controls, this study illuminates the topological interplay between formal hierarchies, informal networks, and individual prominence in complex knowledge institutions.",
        body_style
    ))

    # Force PageBreak so Section 2 starts cleanly on Page 2
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: SECTION 2 (DATA PREPARATION, TABLE 1, FIGURE 1)
    # =========================================================================
    story.append(Paragraph("2 Data preparation", h1_style))
    story.append(Paragraph(
        "<b>Data Integrity and Universe of Nodes:</b> Raw edge and department label files were acquired from SNAP and verified against cryptographic hashes (SHA-256: <code>4b47acdb...</code> for edges, <code>e5abe5b4...</code> for labels). Parsing revealed exactly 25,571 edge rows and 1,005 label rows, with zero malformed entries and zero duplicate directed edges. Department identifiers span 0 &le; dept &le; 41, and node identifiers span 0 &le; node &le; 1004.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Self-Loop Removal and Dual Graph Representation:</b> An edge audit revealed 642 self-loops (<i>u</i>, <i>u</i>), where an individual emailed themselves (draft storage, personal reminders, or automated calendar echoes). Retaining self-loops distorts network analytics: in PageRank, a self-loop traps teleported random walk mass; in community detection, self-loops inflate internal edge density without representing interpersonal exchange. To ensure reproducibility and methodological rigor, we maintain dual representations: "
        "<br/>• <b>(1) <i>G</i><sub>raw</sub>:</b> The raw directed graph containing all 1,005 nodes, 25,571 directed edges, and 642 self-loops, matching published SNAP statistics exactly. "
        "<br/>• <b>(2) <i>G</i><sub>analysis</sub>:</b> The cleaned interpersonal directed graph containing all 1,005 nodes and exactly 24,929 interpersonal directed edges (25,571 &minus; 642). Crucially, the 19 singleton individuals whose only raw edges were self-loops are strictly preserved as degree-0 nodes with their ground-truth department labels to prevent selection bias.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Undirected Projection (<i>G</i><sub>undirected</sub>):</b> Louvain modularity optimization assumes symmetric adjacency. We construct an unweighted undirected projection <i>G</i><sub>undirected</sub> from <i>G</i><sub>analysis</sub>, collapsing reciprocal directed links (<i>u</i>, <i>v</i>) and (<i>v</i>, <i>u</i>) into a single undirected edge {<i>u</i>, <i>v</i>}. This projection preserves all 1,005 nodes (including the 19 isolates) and contains exactly 16,064 undirected edges. Reciprocal links account for 8,865 pairs (17,730 directed edges, 71.12%, matching the 0.7112 directed reciprocity of <i>G</i><sub>analysis</sub>), while 7,199 links are unreciprocated (28.88%). Directional initiation asymmetry is collapsed into binary reachability.",
        body_style
    ))

    # Table 1: Dual Graph Representation Properties (exact printable width: 481.88 pt)
    t1_data = [
        [Paragraph("Network Representation", table_header), Paragraph("Nodes (|V|)", table_header), Paragraph("Edges (|E|)", table_header), Paragraph("Self-Loops", table_header), Paragraph("Directed Density Formula & Value", table_header), Paragraph("WCC Giant", table_header), Paragraph("SCC Giant", table_header), Paragraph("Reciprocity (r)", table_header)],
        [Paragraph("<i>G</i><sub>raw</sub> (Published SNAP)", table_cell_bold), Paragraph("1,005", table_cell), Paragraph("25,571", table_cell), Paragraph("642", table_cell), Paragraph("&rho; = |<i>E</i>| / |<i>V</i>|<sup>2</sup> = 0.025317", table_cell), Paragraph("986 (20 WCCs)", table_cell), Paragraph("803 (203 SCCs)", table_cell), Paragraph("0.6934 (69.3%)", table_cell)],
        [Paragraph("<i>G</i><sub>analysis</sub> (Cleaned Directed)", table_cell_bold), Paragraph("1,005", table_cell), Paragraph("24,929", table_cell), Paragraph("0", table_cell), Paragraph("&rho; = |<i>E</i>| / [|<i>V</i>|(|<i>V</i>|&minus;1)] = 0.024706", table_cell), Paragraph("986 (20 WCCs)", table_cell), Paragraph("803 (203 SCCs)", table_cell), Paragraph("0.7112 (71.1%)", table_cell)],
        [Paragraph("<i>G</i><sub>undirected</sub> (Louvain Projection)", table_cell_bold), Paragraph("1,005", table_cell), Paragraph("16,064", table_cell), Paragraph("0", table_cell), Paragraph("&rho; = 2|<i>E</i>| / [|<i>V</i>|(|<i>V</i>|&minus;1)] = 0.031841", table_cell), Paragraph("986 (20 CCs)", table_cell), Paragraph("— (Undirected)", table_cell), Paragraph("1.0000 (Symmetric)", table_cell)],
    ]
    t1 = Table(t1_data, colWidths=[95, 45, 45, 40, 115, 53, 48, 40.8])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    
    t1_block = KeepTogether([
        t1,
        Paragraph("<b>Table 1:</b> Topological properties and structural invariants across graph representations.", caption_style)
    ])
    story.append(t1_block)
    story.append(Spacer(1, 4))

    # Figure 1: Degree Distributions
    fig1_clean = Path("reports/figures/fig1_degree_distributions_clean.png")
    if fig1_clean.exists():
        fig1_block = KeepTogether([
            Image(str(fig1_clean), width=printable_width, height=158),
            Paragraph("<b>Figure 1:</b> Exploratory degree distributions on <i>G</i><sub>analysis</sub>. (a) Linear in-degree and out-degree histograms (mean = 24.8, medians = 17 and 14). (b) Log-log complementary cumulative distribution function (CCDF) showing heavy-tailed communication activity.", caption_style)
        ])
        story.append(fig1_block)

    # Force PageBreak so Section 3 starts cleanly on Page 3
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: SECTION 3 PART A (PAGERANK, LOUVAIN, CONDUCTANCE)
    # =========================================================================
    story.append(Paragraph("3 Methods and how they connect", h1_style))
    story.append(Paragraph(
        "<b>Algorithm Class 1: PageRank Centrality (Lecture 6):</b> Directed email networks represent endorsement flows where an incoming link (<i>u</i>, <i>v</i>) indicates that sender <i>u</i> acknowledges receiver <i>v</i>. PageRank models a random surfer who follows outgoing links with probability <i>d</i> (damping factor) and teleports uniformly across all |<i>V</i>| = <i>N</i> nodes with probability 1 &minus; <i>d</i>. Dangling nodes (out-degree zero, including the 19 preserved isolates and 15 pure recipients) redistribute their entire random walk probability uniformly across all <i>N</i> nodes at each iteration:",
        body_style
    ))

    # Display Equation (1)
    eq1_tbl = make_equation_flowable(eq_paths["eq1_pagerank"], "1", printable_width, target_width=315.0)
    story.append(KeepTogether([eq1_tbl, Spacer(1, 2)]))

    story.append(Paragraph(
        "where <b>r</b> is the stationary PageRank vector, <b>P</b> is the row-stochastic transition matrix (with <b>P</b><sub><i>uv</i></sub> = <i>A</i><sub><i>uv</i></sub> / <i>d</i><sub>out</sub>(<i>u</i>) for non-dangling nodes), <b>d</b><sub>dangle</sub> is an indicator vector for out-degree zero nodes, and <b>1</b> is a vector of ones. This redistribution guarantees stochasticity and numerical convergence without absorbing stationary probability. Parameters are set to damping factor <i>d</i> = 0.85, uniform personalization, and convergence tolerance tol = 10<sup>&minus;6</sup>. Deterministic tie-breaking is enforced by sorting by score descending, then node ID ascending.",
        body_style
    ))

    story.append(Paragraph(
        "<b>Algorithm Class 2: Louvain Modularity Optimization (Lecture 7):</b> To detect emergent communication communities without supervision, we apply the Louvain algorithm to <i>G</i><sub>undirected</sub>. Louvain greedily optimizes Newman-Girvan modularity:",
        body_style
    ))

    # Display Equation (2)
    eq2_tbl = make_equation_flowable(eq_paths["eq2_modularity"], "2", printable_width, target_width=305.0)
    story.append(KeepTogether([eq2_tbl, Spacer(1, 2)]))

    story.append(Paragraph(
        "where <i>m</i> = 16,064 edges, <i>k</i><sub><i>i</i></sub> is node <i>i</i>'s undirected degree, <i>c</i><sub><i>i</i></sub> is its assigned community, and <i>&gamma;</i> is the resolution parameter (baseline <i>&gamma;</i> = 1.0, random seed 42). Louvain operates in two alternating phases: local modularity-gain node moves, followed by community aggregation into meta-graphs, repeating until modularity plateaus.",
        body_style
    ))

    story.append(Paragraph(
        "<b>Community Quality Metrics:</b> We assess structural cohesion using modularity <i>Q</i> and conductance <i>&phi;</i>(<i>S</i>). For a community <i>S</i>, conductance evaluates boundary cut relative to volume:",
        body_style
    ))

    # Display Equation (3)
    eq3_tbl = make_equation_flowable(eq_paths["eq3_conductance"], "3", printable_width, target_width=285.0)
    story.append(KeepTogether([eq3_tbl, Spacer(1, 2)]))

    story.append(Paragraph(
        "where &part;(<i>S</i>) = {{<i>u</i>, <i>v</i>} &isin; <i>E</i> | <i>u</i> &isin; <i>S</i>, <i>v</i> &notin; <i>S</i>} is the boundary cut, and vol(<i>S</i>) = &sum;<sub><i>u</i> &isin; <i>S</i></sub> <i>k</i><sub><i>u</i></sub> = 2|<i>E</i>(<i>S</i>, <i>S</i>)| + |&part;(<i>S</i>)| is total degree volume. Conductance evaluates boundary cut size relative to total volume (not the fraction of links, since internal edges contribute twice to volume). Lower conductance indicates a sharper, more self-contained boundary.",
        body_style
    ))

    # Force PageBreak so Section 3 Part B starts cleanly on Page 4
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: SECTION 3 PART B (CONNECTING METHODS, NULL MODEL, FIGURE 2)
    # =========================================================================
    story.append(Paragraph("3 Methods and how they connect (continued)", h1_style))
    story.append(Paragraph(
        "<b>How the Methods Connect (Integrated Boundary Analysis):</b> Rather than treating centrality and clustering as isolated exercises, we bridge them directly to answer RQ3. For every node <i>v</i>, we project its PageRank score against its boundary bridging behavior in <i>G</i><sub>undirected</sub>:",
        body_style
    ))

    # Display Equation (4)
    eq4_tbl = make_equation_flowable(eq_paths["eq4_boundary"], "4", printable_width, target_width=345.0)
    story.append(KeepTogether([eq4_tbl, Spacer(1, 2)]))

    story.append(Paragraph(
        "where <i>N</i>(<i>v</i>) denotes the set of undirected neighbors of node <i>v</i>, and <i>c</i><sub><i>v</i></sub> is its assigned community. For isolated singletons (<i>k</i><sub><i>v</i></sub> = 0), the connection fraction is formally undefined and recorded as <code>NaN</code>. By evaluating both absolute count and fraction, we distinguish true global boundary spanners (high PageRank, high count, high fraction) from insular internal hubs (high PageRank, high count, low fraction) and peripheral bridges (low PageRank, low count, high fraction).",
        body_style
    ))

    story.append(Paragraph(
        "<b>Departmental Homophily Null Model Baseline:</b> To evaluate whether within-department communication exceeds chance, we construct a uniform random ordered-pair reference model:",
        body_style
    ))

    # Display Equation (5)
    eq5_tbl = make_equation_flowable(eq_paths["eq5_null_model"], "5", printable_width, target_width=275.0)
    story.append(KeepTogether([eq5_tbl, Spacer(1, 2)]))

    story.append(Paragraph(
        "where <i>s</i><sub><i>d</i></sub> is the size of department <i>d</i> across the institution. For the Email-Eu-core department distribution, <i>p</i><sub>null</sub> = 4.67%. Comparing the observed within-department share (34.68%) against <i>p</i><sub>null</sub> quantifies the institutional homophily enrichment factor (7.43&times;).",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Figure 2: Department Homophily
    fig2_clean = Path("reports/figures/fig2_department_homophily_clean.png")
    if fig2_clean.exists():
        fig2_block = KeepTogether([
            Image(str(fig2_clean), width=printable_width, height=162),
            Paragraph("<b>Figure 2:</b> Department organization and communication composition. (a) Member populations of the 12 largest departments (Median = 14.5). (b) Observed within-department links (34.68%) exceed the uniform random null model baseline (<i>p</i><sub>null</sub> = 4.67%) by 7.43&times;, confirming strong departmental homophily amidst dominant (65.32%) cross-department communication.", caption_style)
        ])
        story.append(fig2_block)

    # Force PageBreak so Section 4 Part A starts cleanly on Page 5
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: SECTION 4 PART A (RQ1, FIGURE 3, RQ2, TABLE 2)
    # =========================================================================
    story.append(Paragraph("4 Evaluation and results", h1_style))
    story.append(Paragraph(
        "<b>RQ1 Results: PageRank vs. In-Degree Centrality:</b> Across all 1,005 nodes, PageRank and in-degree correlate strongly (Spearman <i>&rho;</i><sub><i>s</i></sub> = 0.9828, <i>p</i> &lt; 10<sup>&minus;300</sup>). Top-<i>k</i> set overlap is high: 90.0% for <i>k</i> = 10 (Jaccard = 0.818), 85.0% for <i>k</i> = 20 (0.739), and 92.0% for <i>k</i> = 50 (0.852). Prominence in Email-Eu-core is heavily degree-aligned. However, PageRank reveals critical structural disagreements driven by endorsement quality: "
        "<br/>• <i>PageRank-Boosted (Node 451, Dept 14):</i> Possesses an in-degree of only 8 (rank 659), yet achieves PageRank 0.003117 (rank 37), a shift of &Delta;<i>R</i> = +622. Senders endorsing Node 451 include Node 365 (PR = 0.00306, rank 39, out-degree 1), transferring 100% of its endorsement mass directly to Node 451. PageRank correctly values concentrated endorsements from prominent senders. "
        "<br/>• <i>In-Degree-Boosted (Node 83, Dept 17):</i> Has in-degree 85 (rank 45) but falls to PageRank rank 56. Its senders have a high mean out-degree of 79.1, heavily diluting their endorsement mass (12.8&times; lower contribution per link). "
        "<br/>• <i>Self-Loop Robustness:</i> In <i>G</i><sub>raw</sub>, self-loops artificially elevated the 19 singletons from rank 987 to rank 380 through reflexive trapping (<i>&rho;</i><sub><i>s</i></sub> = 0.8720 between <i>G</i><sub>raw</sub> and <i>G</i><sub>analysis</sub>). Cleaning self-loops is mandatory.",
        body_style
    ))

    # Figure 3: PageRank vs In-Degree
    fig3_clean = Path("reports/figures/fig3_pagerank_vs_indegree_clean.png")
    if fig3_clean.exists():
        fig3_block = KeepTogether([
            Image(str(fig3_clean), width=printable_width, height=153),
            Paragraph("<b>Figure 3:</b> PageRank vs. in-degree centrality on <i>G</i><sub>analysis</sub>. (a) Global scatter plot (Spearman <i>&rho;</i><sub><i>s</i></sub> = 0.9828) highlighting Node 160 (Rank 1 consensus), Node 451 (+622 PageRank boost), and Node 83 (in-degree diluted). (b) Rank shifts &Delta;<i>R</i> = <i>R</i><sub>in</sub> &minus; <i>R</i><sub>PR</sub> for the Top 15 PageRank individuals.", caption_style)
        ])
        story.append(fig3_block)
        story.append(Spacer(1, 4))

    story.append(Paragraph(
        "<b>RQ2 Results: Louvain Communities vs. Administrative Departments:</b> Louvain modularity optimization (<i>&gamma;</i> = 1.0, seed 42) discovers 28 communities: 9 non-trivial cohesive communities spanning 986 nodes, plus 19 isolated singletons (sizes: C0: 190, C1: 157, C2: 145, C3: 127, C4: 125, C5: 109, C6: 91, C7: 32, C8: 10). Louvain achieves modularity <i>Q</i><sub>Louvain</sub> = 0.4130 and median conductance 0.4201 (mean 0.4475, min 0.2780 in C6). "
        "By contrast, partitioning the same graph by official departments yields substantially lower modularity <i>Q</i><sub>dept</sub> = 0.2880 and severe boundary leakage (median departmental conductance 0.8644, mean 0.7871). External concordance is moderate: Normalized Mutual Information NMI = 0.5946, and Adjusted Rand Index ARI = 0.3505. "
        "Organic communication does not adhere to official administrative lines; instead, communication consolidates smaller departments into multi-departmental alliances while fragmenting specific units across clusters.",
        body_style
    ))

    # Table 2: Community Quality Comparison (exact printable width: 481.88 pt)
    t2_data = [
        [Paragraph("Partition Scheme", table_header), Paragraph("Clusters", table_header), Paragraph("Modularity (Q)", table_header), Paragraph("Median Cond (&phi;)", table_header), Paragraph("Mean Cond (&phi;)", table_header), Paragraph("NMI vs. Dept", table_header), Paragraph("ARI vs. Dept", table_header)],
        [Paragraph("Louvain Baseline (&gamma;=1.0, seed 42)", table_cell_bold), Paragraph("9 (+19 isolates)", table_cell), Paragraph("0.4130", table_cell), Paragraph("0.4201 (C6: 0.278)", table_cell), Paragraph("0.4475", table_cell), Paragraph("0.5946", table_cell), Paragraph("0.3505", table_cell)],
        [Paragraph("Official Departments (SNAP)", table_cell_bold), Paragraph("42 departments", table_cell), Paragraph("0.2880", table_cell), Paragraph("0.8644 (Dept 3: 0.30)", table_cell), Paragraph("0.7871", table_cell), Paragraph("1.0000 (Self)", table_cell), Paragraph("1.0000 (Self)", table_cell)],
        [Paragraph("Louvain (&gamma;=0.8, Coarser)", table_cell), Paragraph("6 (+19 isolates)", table_cell), Paragraph("0.4105 (Q_obj: 0.459)", table_cell), Paragraph("0.3812", table_cell), Paragraph("0.4015", table_cell), Paragraph("0.5272", table_cell), Paragraph("0.2223", table_cell)],
        [Paragraph("Louvain (&gamma;=1.2, Finer)", table_cell), Paragraph("10 (+19 isolates)", table_cell), Paragraph("0.4051 (Q_obj: 0.383)", table_cell), Paragraph("0.4410", table_cell), Paragraph("0.4628", table_cell), Paragraph("0.6247", table_cell), Paragraph("0.4321", table_cell)],
    ]
    t2 = Table(t2_data, colWidths=[116, 60, 68, 75, 72, 45, 45.8])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    
    t2_block = KeepTogether([
        t2,
        Paragraph("<b>Table 2:</b> Quality metrics and external alignment across community detection configurations and official departments.", caption_style)
    ])
    story.append(t2_block)

    # Force PageBreak so Section 4 Part B starts cleanly on Page 6
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: SECTION 4 PART B (FIGURE 4, RQ3, FIGURE 5, TABLE 3)
    # =========================================================================
    story.append(Paragraph("4 Evaluation and results (continued)", h1_style))
    
    # Figure 4: Community Department Contingency Heatmap
    fig4_clean = Path("reports/figures/fig4_community_department_clean.png")
    if fig4_clean.exists():
        fig4_block = KeepTogether([
            Image(str(fig4_clean), width=348, height=111, hAlign="CENTER"),
            Paragraph("<b>Figure 4:</b> Community structure and department overlap. (a) Population of the 9 cohesive Louvain communities. (b) Department-community contingency matrix for the 8 largest departments, illustrating how departments consolidate into multi-departmental research groups while certain units fragment across communities.", caption_style)
        ])
        story.append(fig4_block)
        story.append(Spacer(1, 2))

    story.append(Paragraph(
        "<b>RQ3 Results: Central Individuals as Boundary Spanners:</b> Partitioning nodes into the Top 10% PageRank tier (<i>N</i> = 101) and Remaining 90% tier (<i>N</i> = 904): "
        "<br/>• <i>Cross-Community Connections Count:</i> Top 10% maintain a mean of <b>67.88</b> cross-community edges (median 59.0) vs. <b>7.94</b> (median 4.0) for remaining nodes—an <b>8.55&times; higher volume</b> (Mann-Whitney <i>U</i> = 88,970.0, <i>p</i> = 6.88 &times; 10<sup>&minus;56</sup>). "
        "<br/>• <i>Cross-Community Connection Fraction:</i> Top 10% dedicate a mean of <b>55.79%</b> of their links outside their primary community (median 58.10%) vs. <b>26.56%</b> (median 25.00%) for remaining non-isolated nodes (<i>N</i> = 885), more than double the proportion (Mann-Whitney <i>U</i> = 77,037.5, <i>p</i> = 4.59 &times; 10<sup>&minus;33</sup>).",
        body_style
    ))
    story.append(Paragraph(
        "<b>Degree Confounding and Stratified Analysis:</b> Total undirected degree is a major confounder, correlating strongly with PageRank (<i>&rho;</i><sub><i>s</i></sub> = 0.9614) and cross-community count (<i>&rho;</i><sub><i>s</i></sub> = 0.9155). Controlling globally for degree yields a slightly negative partial rank correlation (Partial <i>&rho;</i><sub><i>s</i></sub> = &minus;0.1803, <i>p</i> = 1.15 &times; 10<sup>&minus;8</sup>) because receiving concentrated endorsements inside dense core clusters boosts PageRank without boundary spanning. "
        "However, degree stratification resolves this dynamic: exactly <b>100 of the 101 Top 10% PageRank nodes (99.0%) reside in the highest degree quartile Q4</b> (<i>d</i> &ge; 45, <i>N</i> = 247). Within Q4, Top 10% PageRank nodes exhibit a 2.72&times; higher cross-community count (<b>68.56 vs. 25.17</b>, <i>p</i> = 2.10 &times; 10<sup>&minus;27</sup>) and significantly higher cross-boundary fraction (<b>56.34% vs. 41.30%</b>, <i>p</i> = 5.69 &times; 10<sup>&minus;12</sup>). PageRank reliably distinguishes broad multi-cluster brokers from internal hubs among well-connected individuals.",
        body_style
    ))

    # Figure 5: Integrated Centrality and Boundaries
    fig5_clean = Path("reports/figures/fig5_integrated_centrality_clean.png")
    if fig5_clean.exists():
        fig5_block = KeepTogether([
            Image(str(fig5_clean), width=363, height=111, hAlign="CENTER"),
            Paragraph("<b>Figure 5:</b> Integrated analysis of PageRank vs. boundary connectivity. (a) PageRank vs. cross-community connection share with degree colormap and annotated structural archetypes: Node 160 (Global Boundary Spanner), Node 451 (Internal Hub), and Node 644 (Peripheral Bridge). (b) Degree-stratified boundary spanning across quartiles Q1–Q4, demonstrating that Top 10% PageRank nodes maintain an advantage even when controlling for high degree.", caption_style)
        ])
        story.append(fig5_block)
        story.append(Spacer(1, 2))

    # Table 3: Structural Archetypes Summary (exact printable width: 481.88 pt)
    t3_data = [
        [Paragraph("Structural Archetype", table_header), Paragraph("Focal Node", table_header), Paragraph("Dept / Comm", table_header), Paragraph("PageRank (Score / Rank)", table_header), Paragraph("In-Degree (Rank)", table_header), Paragraph("Undir Deg", table_header), Paragraph("Internal / Cross", table_header), Paragraph("Cross Frac", table_header), Paragraph("Comms Spanned", table_header)],
        [Paragraph("Global Boundary Spanner", table_cell_bold), Paragraph("Node 160", table_cell), Paragraph("Dept 36 / Comm 4", table_cell), Paragraph("0.007495 (Rank 1)", table_cell), Paragraph("211 (Rank 1)", table_cell), Paragraph("345", table_cell), Paragraph("51 / 294", table_cell), Paragraph("85.22%", table_cell_bold), Paragraph("8 external comms", table_cell)],
        [Paragraph("Internal Community Hub", table_cell_bold), Paragraph("Node 451", table_cell), Paragraph("Dept 14 / Comm 6", table_cell), Paragraph("0.003117 (Rank 37)", table_cell), Paragraph("8 (Rank 659)", table_cell), Paragraph("13", table_cell), Paragraph("13 / 0", table_cell), Paragraph("0.00%", table_cell_bold), Paragraph("0 external comms", table_cell)],
        [Paragraph("Peripheral Bridge", table_cell_bold), Paragraph("Node 644", table_cell), Paragraph("Dept 25 / Comm 7", table_cell), Paragraph("0.000514 (Rank 633)", table_cell), Paragraph("11 (Rank 606)", table_cell), Paragraph("15", table_cell), Paragraph("2 / 13", table_cell), Paragraph("86.67%", table_cell_bold), Paragraph("5 external comms", table_cell)],
    ]
    t3 = Table(t3_data, colWidths=[80, 46, 56, 68, 48, 38, 65, 40, 40.8])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.0),
    ]))
    
    t3_block = KeepTogether([
        t3,
        Paragraph("<b>Table 3:</b> Descriptive structural archetypes illustrating distinct topological configurations in Email-Eu-core.", caption_style)
    ])
    story.append(t3_block)

    # Force PageBreak so Section 5 & 6 start cleanly on Page 7
    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: SECTION 5 & SECTION 6
    # =========================================================================
    story.append(Paragraph("5 Insights and limitations", h1_style))
    story.append(Paragraph(
        "<b>Substantive Organizational Insights:</b> Our findings demonstrate that informal communication reorganizes official academic hierarchies. While departmental homophily is strongly enriched (7.43&times; above random expectation), nearly two-thirds (65.32%) of directed communications cross departmental boundaries. Unsupervised community detection reveals that departments consolidate into multi-departmental research clusters with sharp communication boundaries (conductance 0.420 vs. 0.864 for departments). Furthermore, elite prominence is overwhelmingly associated with boundary spanning: individuals in the top 10% PageRank tier maintain an 8.55&times; higher cross-community degree and dedicate more than double their ties across cluster borders. However, this bridging role is not uniform: individuals such as Node 451 achieve high centrality through insular prestige without boundary spanning.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Methodological Limitations:</b> "
        "<br/>1. <i>Network Autocorrelation & Inferential Tests:</i> Network observations violate the independent and identically distributed (i.i.d.) assumption due to dyadic reciprocity (71.12%) and transitive closure. Reported Mann-Whitney U test <i>p</i>-values are descriptive indicators of distributional separation rather than formal causal proofs. "
        "<br/>2. <i>Binary vs. Weighted Edges:</i> The dataset lacks email frequencies, durations, and content. A single administrative announcement is topologically indistinguishable from frequent daily exchanges. "
        "<br/>3. <i>Non-Causal Interpretations:</i> Network position reflects structural embedding, not formal organizational authority, leadership effectiveness, or deliberate brokerage intent. Case studies represent structural archetypes, not verified organizational roles.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Summary Conclusion:</b> In summary, this investigation demonstrates that communication in complex knowledge institutions systematically transcends designated departmental lines. Centrality and community detection techniques provide complementary lenses: PageRank identifies individuals who command structural prominence through high-quality endorsements, while Louvain modularity optimization reveals organic, multi-departmental clusters that govern operational exchange. Crucially, structurally prominent individuals act primarily as inter-community boundary spanners—even after conditioning on high node degree—demonstrating that cross-cluster connectivity is an intrinsic property of institutional prominence.",
        body_style
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("6 Reproducibility information", h1_style))
    story.append(Paragraph(
        "<b>Dataset Acquisition & Cryptographic Hashes:</b> The primary data source is the Stanford Network Analysis Platform (SNAP) Email-Eu-core benchmark. Raw files were downloaded from official URLs: "
        "<br/>• Edges: <code>https://snap.stanford.edu/data/email-Eu-core.txt.gz</code> (SHA-256: <code>4b47acdb80197b085fe63c819c357ae488131ee904ed93d1b219a68b0f9e245f</code>) "
        "<br/>• Department Labels: <code>https://snap.stanford.edu/data/email-Eu-core-department-labels.txt.gz</code> (SHA-256: <code>e5abe5b4581a480032a63adcf2576c161785f45692642c6ebb0b1276f0f33669</code>).",
        body_style
    ))
    story.append(Paragraph(
        "<b>Preprocessing Pipeline:</b> Dual graph representations were constructed: <i>G</i><sub>raw</sub> retains all 1,005 nodes, 25,571 directed edges, and 642 self-loops. <i>G</i><sub>analysis</sub> excludes all 642 self-loops, preserving all 1,005 nodes and 24,929 interpersonal directed edges; 19 singleton nodes with only self-loops are preserved as degree-0 nodes with their official ground-truth department labels. The unweighted undirected projection <i>G</i><sub>undirected</sub> preserves all 1,005 nodes and contains 16,064 undirected edges (8,865 reciprocal pairs, 71.12% reciprocity).",
        body_style
    ))
    story.append(Paragraph(
        "<b>Software and Computing Environment:</b> All analyses were executed under Python 3.10.6 on standard commodity hardware (AMD Ryzen / Intel x86_64, operable on &approx; 8 GB RAM laptops). Exact pinned library versions specified in <code>requirements.txt</code>: NetworkX 3.4.2, SciPy 1.15.3, scikit-learn 1.5.2, pandas 2.3.3, NumPy 1.26.4, matplotlib 3.10.9, seaborn 0.13.2.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Algorithmic Parameters & Random Seeds:</b> PageRank was computed using damping factor <i>d</i> = 0.85, uniform personalization, NetworkX dangling mass redistribution, and convergence tolerance 10<sup>&minus;6</sup>. Louvain modularity optimization was performed with resolution <i>&gamma;</i> = 1.0 and fixed random seed 42. Deterministic tie-breaking is enforced throughout by sorting by metric descending, then node ID ascending.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Execution Instructions:</b> The accompanying <code>analysis.ipynb</code> notebook is completely self-contained and imports no local <code>src/</code> modules. It automatically downloads the raw dataset from SNAP if absent, verifies SHA-256 checksums, executes all analyses, and reproduces all figures and numerical tables from a fresh kernel in under 30 seconds.",
        body_style
    ))

    # =========================================================================
    # PAGE 8: REFERENCES (EXCLUDED FROM 8-PAGE LIMIT PER OFFICIAL SPECIFICATIONS)
    # =========================================================================
    story.append(PageBreak())  # Strictly placed outside the main report page limit
    story.append(MarkReferencesPage())
    story.append(Paragraph("References", h1_style))
    story.append(Paragraph("<i>Note: Per official DSA5101 instructions, the reference list is excluded from the eight-page limit. Appendices are not included.</i>", caption_style))
    story.append(Spacer(1, 6))

    references = [
        "[1] H. Yin, A. R. Benson, J. Leskovec, and D. F. Gleich, 'Local higher-order graph clustering,' in <i>Proceedings of the 23rd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining</i>, 2017, pp. 555–564. [SNAP Email-Eu-core dataset].",
        "[2] L. Page, S. Brin, R. Motwani, and T. Winograd, 'The PageRank citation ranking: Bringing order to the web,' Stanford InfoLab, Technical Report 1999-66, 1999.",
        "[3] V. D. Blondel, J.-L. Guillaume, R. Lambiotte, and E. Lefebvre, 'Fast unfolding of communities in large networks,' <i>Journal of Statistical Mechanics: Theory and Experiment</i>, vol. 2008, no. 10, p. P10008, 2008.",
        "[4] M. E. J. Newman and M. Girvan, 'Finding and evaluating community structure in networks,' <i>Physical Review E</i>, vol. 69, no. 2, p. 026113, 2004.",
        "[5] D. F. Gleich, 'Hierarchical directed spectral graph partitioning,' Department of Computer Science, University of British Columbia, Tech. Rep., 2005. [Conductance in directed and undirected graphs].",
        "[6] D. Garlaschelli and M. I. Loffredo, 'Patterns of link reciprocity in directed networks,' <i>Physical Review Letters</i>, vol. 93, no. 26, p. 268701, 2004.",
        "[7] R. S. Burt, <i>Structural Holes: The Social Structure of Competition</i>. Cambridge, MA: Harvard University Press, 1992.",
        "[8] M. Granovetter, 'The strength of weak ties,' <i>American Journal of Sociology</i>, vol. 78, no. 6, pp. 1360–1380, 1973.",
        "[9] A. Hagberg, P. Swart, and D. S Chult, 'Exploring network structure, dynamics, and function using NetworkX,' in <i>Proceedings of the 7th Python in Science Conference (SciPy 2008)</i>, 2008, pp. 11–15.",
        "[10] F. Pedregosa et al., 'Scikit-learn: Machine learning in Python,' <i>Journal of Machine Learning Research</i>, vol. 12, pp. 2825–2830, 2011.",
    ]

    for ref in references:
        story.append(Paragraph(ref, ParagraphStyle("RefStyle", parent=body_style, fontSize=9, leading=12.5, spaceAfter=5)))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Built PDF successfully at {output_path}")
    return output_path


if __name__ == "__main__":
    build_pdf_report("report.pdf")
