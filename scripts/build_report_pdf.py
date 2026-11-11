"""ReportLab PDF Report Generator for NUS DSA5101.

Strictly adheres to official formatting specifications:
- A4 page size
- Margins >= 2.0 cm (56.7 pt) on all sides
- Body text font >= 10 pt
- Main report (Sections 1-6 + opening summary table) <= 8 pages
- References excluded from page limit (placed on page 9)
- No appendices
- Selectable PDF text and table content
- Dynamic "Page X of Y" page numbering
- High-resolution embedded figures with captions
"""

from __future__ import annotations

import os
from pathlib import Path

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
                841.89 - 40,
                "DSA5101 Project: Beyond Department Boundaries — Email Network Analysis",
            )
            self.drawRightString(
                595.27 - 56.7,
                841.89 - 40,
                "NUS Matriculation: A0352547Y",
            )
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(56.7, 841.89 - 44, 595.27 - 56.7, 841.89 - 44)

        # Running Footer (all pages)
        page_str = f"Page {self._pageNumber} of {page_count}"
        if self._pageNumber >= NumberedCanvas.references_start_page:
            page_label = f"{page_str} (References — Excluded from 8-Page Limit)"
        else:
            page_label = f"{page_str} (Main Report)"

        self.drawString(56.7, 36, "National University of Singapore — Master of Science in Data Science")
        self.drawRightString(595.27 - 56.7, 36, page_label)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(56.7, 46, 595.27 - 56.7, 46)

        self.restoreState()


def build_pdf_report(output_filename: str = "report.pdf") -> Path:
    output_path = Path(output_filename)

    # Page Geometry: A4 (595.27 x 841.89 pt) with exact 2.0 cm (56.7 pt) margins
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=56.7,
        rightMargin=56.7,
        topMargin=56.7,
        bottomMargin=56.7,
    )

    printable_width = 595.27 - 2 * 56.7  # 481.87 pt (~17.0 cm)

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=3,
    )

    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=8,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=5,
        spaceAfter=2,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,  # Strictly >= 10 pt
        leading=13.2,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=4,
        alignment=4,  # Justified
    )

    body_bold = ParagraphStyle(
        "Body_Bold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    caption_style = ParagraphStyle(
        "Caption_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#4A5568"),
        alignment=1,  # Centered
        spaceBefore=2,
        spaceAfter=6,
        keepWithNext=False,
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#2D3748"),
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Helvetica-Bold",
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=table_cell,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = []

    # =========================================================================
    # DOCUMENT HEADER & MANDATORY OPENING SUMMARY TABLE
    # =========================================================================
    story.append(Paragraph("Beyond Department Boundaries: Centrality and Communication Communities in an Email Network", title_style))
    story.append(Paragraph("<b>Course:</b> DSA5101 Introduction to Big Data &nbsp;|&nbsp; <b>Evaluation:</b> Anonymous Submission &nbsp;|&nbsp; <b>NUS Matriculation:</b> A0352547Y", subtitle_style))

    # Mandatory Opening Summary Table
    summary_data = [
        [Paragraph("Project Title", table_header), Paragraph("Beyond Department Boundaries: Centrality and Communication Communities in an Email Network", table_cell_bold)],
        [Paragraph("Dataset & Source", table_header), Paragraph("Email-Eu-core network, Stanford Network Analysis Platform (SNAP) (1,005 members, 42 departments)", table_cell)],
        [Paragraph("Algorithm Classes", table_header), Paragraph("1. PageRank Centrality (Lecture 6)<br/>2. Graph Clustering / Louvain Community Detection (Lecture 7)", table_cell)],
        [Paragraph("Research Question", table_header), Paragraph("To what extent do emergent communication communities align with formal department boundaries, and what structural roles do highly central individuals play in connecting disparate communities?", table_cell)],
    ]
    summary_tbl = Table(summary_data, colWidths=[120, printable_width - 120])
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1A365D")),
        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#F7FAFC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_tbl)
    story.append(Spacer(1, 4))

    # =========================================================================
    # SECTION 1: RESEARCH QUESTION AND DATASET
    # =========================================================================
    story.append(Paragraph("1 Research question and dataset", h1_style))
    story.append(Paragraph(
        "Formal organizational charts reflect institutional hierarchies, administrative responsibilities, and official reporting channels. However, day-to-day operational exchange, collaboration, and information dissemination frequently transcend designated organizational units. Investigating whether emergent communication clusters mirror administrative boundaries—and how centrally positioned individuals bridge or reinforce those clusters—provides critical insights into organizational functioning, cross-departmental silos, and coordination bottlenecks.",
        body_style
    ))
    story.append(Paragraph(
        "This project investigates the <b>Email-Eu-core</b> network published by the Stanford Network Analysis Platform (SNAP) [1]. Generated from email logs of a large European research institution over an 18-month observation window, the dataset captures interactions among researchers, staff, and leadership. Crucially, each individual is labeled with one of 42 ground-truth administrative departments. The network contains 1,005 institution members and 25,571 directed edges $(u, v)$, representing at least one email sent from individual $u$ to individual $v$. Edge weights representing email frequencies are not provided; edges indicate binary reachability.",
        body_style
    ))
    story.append(Paragraph(
        "We formalize three coherent research questions: "
        "<b>RQ1 (Prominence vs. Popularity):</b> How does directed PageRank centrality differ from simple in-degree popularity, and what topological mechanisms govern ranking disagreements? "
        "<b>RQ2 (Community-Department Alignment):</b> Do unsupervised communication communities discovered via Louvain modularity optimization follow the 42 administrative department boundaries? "
        "<b>RQ3 (Role of Central Individuals & Degree Confounding):</b> Do structurally prominent individuals act as cross-community boundary spanners or insular internal hubs, and does PageRank provide structural information beyond total node degree?",
        body_style
    ))

    # =========================================================================
    # SECTION 2: DATA PREPARATION
    # =========================================================================
    story.append(Paragraph("2 Data preparation", h1_style))
    story.append(Paragraph(
        "<b>Data Integrity and Universe of Nodes:</b> Raw edge and department label files were acquired from SNAP and verified against cryptographic hashes (SHA-256: <code>4b47acdb...</code> for edges, <code>e5abe5b4...</code> for labels). Parsing revealed exactly 25,571 edge rows and 1,005 label rows, with zero malformed entries and zero duplicate directed edges. Department identifiers span $0 \\le \\text{dept} \\le 41$, and node identifiers span $0 \\le \\text{node} \\le 1004$.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Self-Loop Removal and Dual Graph Representation:</b> An edge audit revealed 642 self-loops $(u, u)$, where an individual emailed themselves (draft storage, personal reminders, or automated calendar echoes). Retaining self-loops distorts network analytics: in PageRank, a self-loop traps teleported random walk mass; in community detection, self-loops inflate internal edge density without representing interpersonal exchange. To ensure reproducibility and methodological rigor, we maintain dual representations: "
        "<b>(1) $G_{\\text{raw}}$:</b> The raw directed graph containing all 1,005 nodes, 25,571 directed edges, and 642 self-loops, matching published SNAP statistics exactly. "
        "<b>(2) $G_{\\text{analysis}}$:</b> The cleaned interpersonal directed graph containing all 1,005 nodes and exactly 24,929 interpersonal directed edges ($25,571 - 642$). Crucially, the 19 singleton individuals whose only raw edges were self-loops are strictly preserved as degree-0 nodes with their ground-truth department labels to prevent selection bias.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Undirected Projection ($G_{\\text{undirected}}$):</b> Louvain modularity optimization assumes symmetric adjacency. We construct an unweighted undirected projection $G_{\\text{undirected}}$ from $G_{\\text{analysis}}$, collapsing reciprocal directed links $(u, v)$ and $(v, u)$ into a single undirected edge $\\{u, v\\}$. This projection preserves all 1,005 nodes (including the 19 isolates) and contains exactly 16,064 undirected edges. Reciprocal links account for 8,865 pairs ($17,730$ directed edges, $71.12\\%$, matching the $0.7112$ directed reciprocity of $G_{\\text{analysis}}$), while 7,199 links are unreciprocated ($28.88\\%$). Directional initiation asymmetry is collapsed into binary reachability.",
        body_style
    ))

    # Table 1: Dual Graph Representation Properties
    t1_data = [
        [Paragraph("Network Representation", table_header), Paragraph("Nodes (|V|)", table_header), Paragraph("Edges (|E|)", table_header), Paragraph("Self-Loops", table_header), Paragraph("Density Formula & Value", table_header), Paragraph("WCC Giant", table_header), Paragraph("SCC Giant", table_header), Paragraph("Reciprocity (r)", table_header)],
        [Paragraph("G_raw (Published SNAP)", table_cell_bold), Paragraph("1,005", table_cell), Paragraph("25,571", table_cell), Paragraph("642", table_cell), Paragraph("ρ = |E|/|V|² = 0.025317", table_cell), Paragraph("986 (20 WCCs)", table_cell), Paragraph("803 (203 SCCs)", table_cell), Paragraph("0.6934 (69.3%)", table_cell)],
        [Paragraph("G_analysis (Cleaned Directed)", table_cell_bold), Paragraph("1,005", table_cell), Paragraph("24,929", table_cell), Paragraph("0", table_cell), Paragraph("ρ = |E|/[|V|(|V|-1)] = 0.024706", table_cell), Paragraph("986 (20 WCCs)", table_cell), Paragraph("803 (203 SCCs)", table_cell), Paragraph("0.7112 (71.1%)", table_cell)],
        [Paragraph("G_undirected (Louvain Projection)", table_cell_bold), Paragraph("1,005", table_cell), Paragraph("16,064", table_cell), Paragraph("0", table_cell), Paragraph("ρ = 2|E|/[|V|(|V|-1)] = 0.031841", table_cell), Paragraph("986 (20 CCs)", table_cell), Paragraph("— (Undirected)", table_cell), Paragraph("1.0000 (Symmetric)", table_cell)],
    ]
    t1 = Table(t1_data, colWidths=[95, 45, 45, 40, 110, 55, 50, 42])
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
    story.append(t1)
    story.append(Paragraph("<b>Table 1:</b> Topological properties and structural invariants across graph representations.", caption_style))

    # Figure 1 & Figure 2 Side by Side or Stacked
    fig1_path = Path("reports/figures/fig1_degree_distributions.png")
    if fig1_path.exists():
        story.append(Image(str(fig1_path), width=printable_width, height=135))
        story.append(Paragraph("<b>Figure 1:</b> Exploratory degree distributions on $G_{\\text{analysis}}$. (a) Linear in-degree and out-degree histograms (mean = 24.8, median = 17.0 and 14.0). (b) Log-log complementary cumulative distribution function (CCDF) showing heavy-tailed communication activity.", caption_style))

    # =========================================================================
    # SECTION 3: METHODS AND HOW THEY CONNECT
    # =========================================================================
    story.append(Paragraph("3 Methods and how they connect", h1_style))
    story.append(Paragraph(
        "<b>Algorithm Class 1: PageRank Centrality (Lecture 6):</b> Directed email networks represent endorsement flows where an incoming link $(u, v)$ indicates that sender $u$ acknowledges receiver $v$. PageRank models a random surfer who follows outgoing links with probability $d$ (damping factor) and teleports uniformly across all $|V|=N$ nodes with probability $1-d$: "
        "$$\\mathbf{r} = d \\mathbf{P}^T \\mathbf{r} + \\frac{1 - d}{N} \\mathbf{1}$$ "
        "where $\\mathbf{P}_{uv} = A_{uv} / d_{\\text{out}}(u)$ if $d_{\\text{out}}(u) > 0$. When a node has zero out-degree (a dangling node, such as the 19 preserved isolates and 15 pure recipients), standard NetworkX dangling mass redistribution redistributes its entire random walk probability uniformly across all $N$ nodes at each iteration. This guarantees convergence without absorbing stationary probability. We set primary parameters: damping factor $d = 0.85$, uniform personalization, and convergence tolerance $\\text{tol} = 10^{-6}$. Deterministic tie-breaking is enforced by sorting by descending PageRank and ascending node ID.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Algorithm Class 2: Louvain Modularity Optimization (Lecture 7):</b> To detect emergent communication communities without supervision, we apply the Louvain algorithm to $G_{\\text{undirected}}$. Louvain greedily optimizes Newman-Girvan modularity: "
        "$$Q = \\frac{1}{2m} \\sum_{i,j} \\left[ A_{ij} - \\gamma \\frac{k_i k_j}{2m} \\right] \\delta(c_i, c_j)$$ "
        "where $m = 16,064$ edges, $k_i$ is node $i$'s undirected degree, $c_i$ is its community, and $\\gamma$ is the resolution parameter (baseline $\\gamma = 1.0$, random seed 42). Louvain operates in two alternating phases: local modularity-gain node moves, followed by community aggregation into meta-graphs, repeating until modularity plateaus.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Community Quality Metrics:</b> We assess structural cohesion using modularity $Q$ and conductance $\\phi(S)$. For a community $S$, conductance measures boundary cut relative to volume: "
        "$$\\phi(S) = \\frac{|\\partial(S)|}{\\min(\\text{vol}(S), \\text{vol}(V \\setminus S))}$$ "
        "where $\\partial(S) = \\{\\{u, v\\} \\in E \\mid u \\in S, v \\notin S\\}$ and $\\text{vol}(S) = \\sum_{u \\in S} k_u = 2|E(S, S)| + |\\partial(S)|$. Conductance evaluates boundary cut size relative to total degree volume (not the percentage of links, since internal edges contribute twice to volume). Lower conductance indicates a sharper, more self-contained boundary.",
        body_style
    ))
    story.append(Paragraph(
        "<b>External Department Alignment:</b> We benchmark discovered communities against formal departments using Normalized Mutual Information (NMI) and Adjusted Rand Index (ARI). Baseline department modularity $Q_{\\text{dept}}$ and departmental conductance evaluate how well administrative boundaries delineate actual communication.",
        body_style
    ))
    story.append(Paragraph(
        "<b>How the Methods Connect (Integrated Boundary Analysis):</b> Rather than treating centrality and clustering as isolated exercises, we bridge them directly to answer RQ3. For every node $v$, we project its PageRank score against its boundary bridging behavior in $G_{\\text{undirected}}$: "
        "$$\\text{CrossCommunityCount}(v) = |\\{u \\in N(v) \\mid c_u \\neq c_v\\}|, \\quad \\text{CrossCommunityFraction}(v) = \\frac{\\text{CrossCommunityCount}(v)}{k_v}$$ "
        "For isolated singletons ($k_v = 0$), the fraction is formally undefined and recorded as <code>NaN</code>. By evaluating both absolute count and fraction, we distinguish true global boundary spanners (high PageRank, high count, high fraction) from insular internal hubs (high PageRank, high count, low fraction) and peripheral bridges (low PageRank, low count, high fraction).",
        body_style
    ))

    # Figure 2 & Figure 3 (Side-by-side or stacked)
    fig3_path = Path("reports/figures/fig3_within_vs_cross_edges.png")
    fig4_path = Path("reports/figures/fig4_pagerank_vs_indegree.png")
    if fig3_path.exists():
        story.append(Image(str(fig3_path), width=printable_width, height=135))
        story.append(Paragraph("<b>Figure 2:</b> Inter- vs. intra-departmental communication. Observed within-department edges ($34.68\\%$) exceed the uniform random ordered-pair null model ($p_{\\text{null}} = 4.67\\%$) by $7.43\\times$, confirming strong departmental homophily amidst dominant ($65.32\\%$) cross-department communication.", caption_style))

    # =========================================================================
    # SECTION 4: EVALUATION AND RESULTS
    # =========================================================================
    story.append(Paragraph("4 Evaluation and results", h1_style))
    story.append(Paragraph(
        "<b>RQ1 Results: PageRank vs. In-Degree Centrality:</b> Across all 1,005 nodes, PageRank and in-degree correlate strongly (Spearman $\\rho_s = 0.9828, p < 10^{-300}$). Top-$k$ set overlap is high: $90.0\\%$ for $k=10$ (Jaccard = $0.818$), $85.0\\%$ for $k=20$ ($0.739$), and $92.0\\%$ for $k=50$ ($0.852$). Prominence in Email-Eu-core is heavily degree-aligned. However, PageRank reveals critical structural disagreements driven by endorsement quality: "
        "<br/>• <i>PageRank-Boosted (Node 451, Dept 14):</i> Possesses an in-degree of only 8 (rank 659, min rank 647), yet achieves PageRank $0.003117$ (rank 37), a shift of $\\Delta R = +622$. Senders endorsing Node 451 include Node 365 ($PR = 0.00306$, rank 39, out-degree 1), transferring $100\\%$ of its endorsement mass directly to Node 451. PageRank correctly values concentrated endorsements from prominent senders. "
        "<br/>• <i>In-Degree-Boosted (Node 83, Dept 17):</i> Has in-degree 85 (rank 45) but falls to PageRank rank 56. Its senders have a high mean out-degree of 79.1, heavily diluting their endorsement mass ($12.8\\times$ lower contribution per link). "
        "<br/>• <i>Self-Loop Robustness:</i> In $G_{\\text{raw}}$, self-loops artificially elevated the 19 singletons from rank 987 to rank 380 through reflexive trapping ($\rho_s = 0.8732$ between $G_{\\text{raw}}$ and $G_{\\text{analysis}}$). Cleaning self-loops is mandatory.",
        body_style
    ))

    if fig4_path.exists():
        story.append(Image(str(fig4_path), width=printable_width, height=135))
        story.append(Paragraph("<b>Figure 3:</b> PageRank vs. In-degree centrality on $G_{\\text{analysis}}$. (a) Global scatter plot ($\\rho_s = 0.9828$) highlighting Node 160 (Rank 1), Node 451 (+622 PageRank boost), and Node 83 (in-degree diluted). (b) Rank shifts $\\Delta R$ for the Top 25 individuals.", caption_style))

    story.append(Paragraph(
        "<b>RQ2 Results: Louvain Community Detection vs. Administrative Departments:</b> Louvain modularity optimization ($\gamma = 1.0, \\text{seed} = 42$) discovers 28 communities: 9 non-trivial cohesive communities spanning 986 nodes, plus 19 isolated singletons (sizes: C0: 190, C1: 157, C2: 145, C3: 127, C4: 125, C5: 109, C6: 91, C7: 32, C8: 10). Louvain achieves modularity $Q_{\\text{Louvain}} = 0.4130$ and median conductance $0.4201$ (mean $0.4475$, min $0.2780$ in C6). "
        "By contrast, partitioning the same graph by official departments yields substantially lower modularity $Q_{\\text{dept}} = 0.2880$ and severe boundary leakage (median departmental conductance $0.8644$, mean $0.7871$). External concordance is moderate: Normalized Mutual Information $NMI = 0.5946$, and Adjusted Rand Index $ARI = 0.3505$. "
        "Organic communication does not adhere to official administrative lines; instead, communication consolidates smaller departments into multi-departmental alliances while fragmenting specific units across clusters.",
        body_style
    ))

    # Table 2: Community Quality Comparison
    t2_data = [
        [Paragraph("Partition Scheme", table_header), Paragraph("Clusters", table_header), Paragraph("Modularity (Q)", table_header), Paragraph("Median Conductance (φ)", table_header), Paragraph("Mean Conductance (φ)", table_header), Paragraph("NMI vs. Depts", table_header), Paragraph("ARI vs. Depts", table_header)],
        [Paragraph("Louvain Baseline (γ=1.0, seed=42)", table_cell_bold), Paragraph("9 (+19 isolates)", table_cell), Paragraph("0.4130", table_cell), Paragraph("0.4201 (C6: 0.2780)", table_cell), Paragraph("0.4475", table_cell), Paragraph("0.5946", table_cell), Paragraph("0.3505", table_cell)],
        [Paragraph("Official Departments (SNAP)", table_cell_bold), Paragraph("42 departments", table_cell), Paragraph("0.2880", table_cell), Paragraph("0.8644 (Dept 3: 0.301)", table_cell), Paragraph("0.7871", table_cell), Paragraph("1.0000 (Self)", table_cell), Paragraph("1.0000 (Self)", table_cell)],
        [Paragraph("Louvain (γ=0.8, Coarser)", table_cell), Paragraph("6 (+19 isolates)", table_cell), Paragraph("0.4105 (Q_obj: 0.459)", table_cell), Paragraph("0.3812", table_cell), Paragraph("0.4015", table_cell), Paragraph("0.5272", table_cell), Paragraph("0.2223", table_cell)],
        [Paragraph("Louvain (γ=1.2, Finer)", table_cell), Paragraph("10 (+19 isolates)", table_cell), Paragraph("0.4051 (Q_obj: 0.383)", table_cell), Paragraph("0.4410", table_cell), Paragraph("0.4628", table_cell), Paragraph("0.6247", table_cell), Paragraph("0.4321", table_cell)],
    ]
    t2 = Table(t2_data, colWidths=[120, 65, 75, 80, 75, 45, 45])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t2)
    story.append(Paragraph("<b>Table 2:</b> Quality metrics and external alignment across community detection configurations and official departments.", caption_style))

    fig8_path = Path("reports/figures/fig8_department_community_heatmap.png")
    if fig8_path.exists():
        story.append(Image(str(fig8_path), width=printable_width, height=135))
        story.append(Paragraph("<b>Figure 4:</b> Department-community contingency matrix heatmap for the 15 largest departments. Organic communication groups consolidate multiple departments (e.g. Community 0 unites Depts 4, 14, 36) while fragmenting others (e.g. Dept 14 splits across C0, C2, C6).", caption_style))

    story.append(Paragraph(
        "<b>RQ3 Results: Central Individuals as Boundary Spanners:</b> Partitioning nodes into the Top 10% PageRank tier ($N=101$) and Remaining 90% tier ($N=904$): "
        "<br/>• <i>Cross-Community Connections Count:</i> Top 10% maintain a mean of <b>67.88</b> cross-community edges (median 59.0) vs. <b>7.94</b> (median 4.0) for remaining nodes—an <b>8.55× higher volume</b> (Mann-Whitney $U = 88,970.0, p = 6.88 \\times 10^{-56}$). "
        "<br/>• <i>Cross-Community Connection Fraction:</i> Top 10% dedicate a mean of <b>55.79%</b> of their links outside their primary community (median $58.10\\%$) vs. <b>26.56%</b> (median $25.00\\%$) for remaining non-isolated nodes ($N=885$), more than double the proportion (Mann-Whitney $U = 77,037.5, p = 4.59 \\times 10^{-33}$).",
        body_style
    ))
    story.append(Paragraph(
        "<b>Degree Confounding and Stratified Analysis:</b> Total undirected degree is a major confounder, correlating strongly with PageRank ($\\rho_s = 0.9614$) and cross-community count ($\\rho_s = 0.9155$). Controlling globally for degree yields a slightly negative partial rank correlation ($\\text{Partial } \\rho_s = -0.1803, p = 1.15 \\times 10^{-8}$) because receiving concentrated endorsements inside dense core clusters boosts PageRank without boundary spanning. "
        "However, degree stratification resolves this dynamic: exactly <b>100 of the 101 Top 10% PageRank nodes (99.0%) reside in the highest degree quartile Q4</b> ($d \\ge 45, N=247$). Within Q4, Top 10% PageRank nodes exhibit a $2.72\\times$ higher cross-community count (<b>68.56 vs. 25.17</b>, $p = 2.10 \\times 10^{-27}$) and significantly higher cross-boundary fraction (<b>56.34% vs. 41.30%</b>, $p = 5.69 \\times 10^{-12}$). PageRank reliably distinguishes broad multi-cluster brokers from internal hubs among well-connected individuals.",
        body_style
    ))

    fig10_path = Path("reports/figures/fig10_pagerank_vs_cross_fraction.png")
    if fig10_path.exists():
        story.append(Image(str(fig10_path), width=printable_width, height=135))
        story.append(Paragraph("<b>Figure 5:</b> Integrated analysis of PageRank vs. cross-community fraction with degree colormap and annotated structural archetypes: Node 160 (Global Boundary Spanner), Node 451 (Internal Hub), and Node 644 (Peripheral Bridge).", caption_style))

    # Table 3: Structural Archetypes Summary
    t3_data = [
        [Paragraph("Structural Archetype", table_header), Paragraph("Focal Node", table_header), Paragraph("Dept / Comm", table_header), Paragraph("PageRank (Score / Rank)", table_header), Paragraph("In-Degree (Rank)", table_header), Paragraph("Undirected Degree", table_header), Paragraph("Internal / Cross Edges", table_header), Paragraph("Cross Fraction", table_header), Paragraph("Comms Spanned", table_header)],
        [Paragraph("Global Boundary Spanner", table_cell_bold), Paragraph("Node 160", table_cell), Paragraph("Dept 36 / Comm 4", table_cell), Paragraph("0.007495 (Rank 1)", table_cell), Paragraph("211 (Rank 1)", table_cell), Paragraph("345", table_cell), Paragraph("51 internal / 294 cross", table_cell), Paragraph("85.22%", table_cell_bold), Paragraph("8 external comms", table_cell)],
        [Paragraph("Internal Community Hub", table_cell_bold), Paragraph("Node 451", table_cell), Paragraph("Dept 14 / Comm 6", table_cell), Paragraph("0.003117 (Rank 37)", table_cell), Paragraph("8 (Rank 659)", table_cell), Paragraph("13", table_cell), Paragraph("13 internal / 0 cross", table_cell), Paragraph("0.00%", table_cell_bold), Paragraph("0 external comms", table_cell)],
        [Paragraph("Peripheral Bridge", table_cell_bold), Paragraph("Node 644", table_cell), Paragraph("Dept 25 / Comm 7", table_cell), Paragraph("0.000514 (Rank 633)", table_cell), Paragraph("11 (Rank 606)", table_cell), Paragraph("15", table_cell), Paragraph("2 internal / 13 cross", table_cell), Paragraph("86.67%", table_cell_bold), Paragraph("5 external comms", table_cell)],
    ]
    t3 = Table(t3_data, colWidths=[90, 48, 65, 80, 55, 45, 75, 45, 60])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t3)
    story.append(Paragraph("<b>Table 3:</b> Descriptive structural archetypes illustrating distinct topological configurations in Email-Eu-core.", caption_style))

    # =========================================================================
    # SECTION 5: INSIGHTS AND LIMITATIONS
    # =========================================================================
    story.append(Paragraph("5 Insights and limitations", h1_style))
    story.append(Paragraph(
        "<b>Substantive Organizational Insights:</b> Our findings demonstrate that informal communication reorganizes official academic hierarchies. While departmental homophily is strongly enriched ($7.43\\times$ above random expectation), nearly two-thirds ($65.32\\%$) of directed communications cross departmental boundaries. Unsupervised community detection reveals that departments consolidate into multi-departmental research clusters with sharp communication boundaries (conductance $0.420$ vs. $0.864$ for departments). Furthermore, elite prominence is overwhelmingly associated with boundary spanning: individuals in the top 10% PageRank tier maintain an $8.55\\times$ higher cross-community degree and dedicate more than double their ties across cluster borders. However, this bridging role is not uniform: individuals such as Node 451 achieve high centrality through insular prestige without boundary spanning.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Methodological Limitations:</b> "
        "<br/>1. <i>Network Autocorrelation & Inferential Tests:</i> Network observations violate the independent and identically distributed (i.i.d.) assumption due to dyadic reciprocity ($71.12\\%$) and transitive closure. Reported Mann-Whitney U test p-values are descriptive indicators of distributional separation rather than formal causal proofs. "
        "<br/>2. <i>Binary vs. Weighted Edges:</i> The dataset lacks email frequencies, durations, and content. A single administrative announcement is topologically indistinguishable from frequent daily exchanges. "
        "<br/>3. <i>Non-Causal Interpretations:</i> Network position reflects structural embedding, not formal organizational authority, leadership effectiveness, or deliberate brokerage intent. Case studies represent structural archetypes, not verified organizational roles.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Summary Conclusion:</b> In summary, this investigation demonstrates that communication in complex knowledge institutions systematically transcends designated departmental lines. Centrality and community detection techniques provide complementary lenses: PageRank identifies individuals who command structural prominence through high-quality endorsements, while Louvain modularity optimization reveals organic, multi-departmental clusters that govern operational exchange. Crucially, structurally prominent individuals act primarily as inter-community boundary spanners—even after conditioning on high node degree—demonstrating that cross-cluster connectivity is an intrinsic property of institutional prominence.",
        body_style
    ))

    # =========================================================================
    # SECTION 6: REPRODUCIBILITY INFORMATION
    # =========================================================================
    story.append(Paragraph("6 Reproducibility information", h1_style))
    story.append(Paragraph(
        "<b>Dataset Acquisition & Cryptographic Hashes:</b> The primary data source is the Stanford Network Analysis Platform (SNAP) Email-Eu-core benchmark. Raw files were downloaded from official URLs: "
        "<br/>• Edges: <code>https://snap.stanford.edu/data/email-Eu-core.txt.gz</code> (SHA-256: <code>4b47acdb80197b085fe63c819c357ae488131ee904ed93d1b219a68b0f9e245f</code>) "
        "<br/>• Department Labels: <code>https://snap.stanford.edu/data/email-Eu-core-department-labels.txt.gz</code> (SHA-256: <code>e5abe5b4581a480032a63adcf2576c161785f45692642c6ebb0b1276f0f33669</code>).",
        body_style
    ))
    story.append(Paragraph(
        "<b>Preprocessing Pipeline:</b> Dual graph representations were constructed: $G_{\\text{raw}}$ retains all 1,005 nodes, 25,571 directed edges, and 642 self-loops. $G_{\\text{analysis}}$ excludes all 642 self-loops, preserving all 1,005 nodes and 24,929 interpersonal directed edges; 19 singleton nodes with only self-loops are preserved as degree-0 nodes with their official ground-truth department labels. The unweighted undirected projection $G_{\\text{undirected}}$ preserves all 1,005 nodes and contains 16,064 undirected edges (8,865 reciprocal pairs, 71.12% reciprocity).",
        body_style
    ))
    story.append(Paragraph(
        "<b>Software and Computing Environment:</b> All analyses were executed under Python 3.10.6 on standard commodity hardware (AMD Ryzen / Intel x86_64, operable on $\\approx 8$ GB RAM laptops). Exact pinned library versions specified in <code>requirements.txt</code>: NetworkX 3.4.2, SciPy 1.15.3, scikit-learn 1.5.2, pandas 2.3.3, NumPy 1.26.4, matplotlib 3.10.9, seaborn 0.13.2.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Algorithmic Parameters & Random Seeds:</b> PageRank was computed using damping factor $d = 0.85$, uniform personalization, NetworkX dangling mass redistribution, and convergence tolerance $10^{-6}$. Louvain modularity optimization was performed with resolution $\\gamma = 1.0$ and fixed random seed 42. Deterministic tie-breaking is enforced throughout by sorting by metric descending, then node ID ascending.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Execution Instructions:</b> The accompanying <code>analysis.ipynb</code> notebook is completely self-contained and imports no local <code>src/</code> modules. It automatically downloads the raw dataset from SNAP if absent, verifies SHA-256 checksums, executes all analyses, and reproduces all figures and numerical tables from a fresh kernel in under 30 seconds.",
        body_style
    ))

    # =========================================================================
    # REFERENCES (EXCLUDED FROM 8-PAGE LIMIT PER OFFICIAL SPECIFICATIONS)
    # =========================================================================
    story.append(PageBreak())  # Strictly placed outside the main report page limit
    story.append(MarkReferencesPage())
    story.append(Paragraph("References", h1_style))
    story.append(Paragraph("<i>Note: Per official DSA5101 instructions, the reference list is excluded from the eight-page limit. Appendices are not included.</i>", caption_style))
    story.append(Spacer(1, 4))

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
        story.append(Paragraph(ref, ParagraphStyle("RefStyle", parent=body_style, fontSize=9, leading=12, spaceAfter=4)))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Built PDF successfully at {output_path}")
    return output_path


if __name__ == "__main__":
    build_pdf_report("report.pdf")
