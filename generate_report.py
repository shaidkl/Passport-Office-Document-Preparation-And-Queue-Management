from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".codex_deps"))

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import (
    WD_ALIGN_PARAGRAPH,
    WD_BREAK,
    WD_LINE_SPACING,
    WD_TAB_ALIGNMENT,
    WD_TAB_LEADER,
)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


OUTPUT = ROOT / "Recommendation Report - Supporting Women Entrepreneurs in Nepal.docx"

NAVY = "17365D"
TEAL = "0E7490"
PALE_BLUE = "EAF3F8"
PALE_TEAL = "E6F4F1"
MID_GREY = "667085"
LIGHT_GREY = "F2F4F7"
WHITE = "FFFFFF"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=100, start=100, bottom=100, end=100):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_border(cell, **kwargs):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_borders = tc_pr.first_child_found_in("w:tcBorders")
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)
    for edge in ("top", "start", "bottom", "end", "insideH", "insideV"):
        if edge not in kwargs:
            continue
        edge_data = kwargs.get(edge)
        tag = "w:{}".format(edge)
        element = tc_borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            tc_borders.append(element)
        for key in ("val", "sz", "space", "color"):
            if key in edge_data:
                element.set(qn(f"w:{key}"), str(edge_data[key]))


def add_bottom_border(paragraph, color=TEAL, size="10"):
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), size)
    bottom.set(qn("w:space"), "5")
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)


def add_hyperlink(paragraph, text, url, color=TEAL):
    part = paragraph.part
    rel_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    new_run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    c = OxmlElement("w:color")
    c.set(qn("w:val"), color)
    r_pr.append(c)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    r_pr.append(underline)
    new_run.append(r_pr)
    text_element = OxmlElement("w:t")
    text_element.text = text
    new_run.append(text_element)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run()
    fld_char_1 = OxmlElement("w:fldChar")
    fld_char_1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char_2 = OxmlElement("w:fldChar")
    fld_char_2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char_1, instr_text, fld_char_2])


def add_toc(paragraph):
    run = paragraph.add_run()
    fld_char = OxmlElement("w:fldChar")
    fld_char.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = 'TOC \\o "1-3" \\h \\z \\u'
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "The table of contents will update when this file is opened in Microsoft Word."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char, instr_text, separate, placeholder, end])


def add_manual_toc(document):
    entries = [
        ("Table of Contents", 2, 0),
        ("Executive Summary", 3, 0),
        ("1. Introduction", 3, 0),
        ("1.1 Purpose and issue", 3, 1),
        ("1.2 Nepal’s present opportunity", 4, 1),
        ("2. Methodology", 4, 0),
        ("3. Findings", 4, 0),
        ("3.1 Participation is visible, but business scale is small", 4, 1),
        ("3.2 Finance exists, but it is not always usable for growth", 4, 1),
        ("3.3 Training is fragmented from the rest of the business journey", 5, 1),
        ("3.4 Formalisation and market access remain difficult", 5, 1),
        ("3.5 Social norms, care and mobility shape business decisions", 5, 1),
        ("3.6 Current support is promising but insufficiently connected", 5, 1),
        ("Key Evidence at a Glance", 5, 1),
        ("4. Recommendations, Analysis and Discussion", 6, 0),
        ("4.1 Create women’s enterprise service desks at local level", 6, 1),
        ("4.2 Build a finance ladder for different stages of growth", 6, 1),
        ("4.3 Replace one-off training with twelve-month growth support", 7, 1),
        ("4.4 Open dependable markets, not only exhibitions", 7, 1),
        ("4.5 Treat care, safety and mobility as business infrastructure", 7, 1),
        ("4.6 Establish shared leadership, definitions and results data", 7, 1),
        ("5. Proposed Next Steps and Conclusion", 8, 0),
        ("5.1 Immediate next steps", 8, 1),
        ("5.2 Conclusion", 8, 1),
        ("Appendix A: Implementation Matrix", 9, 0),
        ("Appendix B: Suggested Monitoring Questions", 9, 0),
        ("References", 10, 0),
    ]
    table = document.add_table(rows=0, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    tbl_layout = tbl_pr.find(qn("w:tblLayout"))
    if tbl_layout is None:
        tbl_layout = OxmlElement("w:tblLayout")
        tbl_pr.append(tbl_layout)
    tbl_layout.set(qn("w:type"), "fixed")

    for title, page, level in entries:
        cells = table.add_row().cells
        cells[0].width = Cm(13.4)
        cells[1].width = Cm(2.4)
        cells[2].width = Cm(1.0)
        for cell in cells:
            set_cell_margins(cell, top=20, start=0, bottom=20, end=0)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP

        title_p = cells[0].paragraphs[0]
        title_p.paragraph_format.left_indent = Cm(0.45 * level)
        title_p.paragraph_format.space_after = Pt(0)
        title_run = title_p.add_run(title)

        dots_p = cells[1].paragraphs[0]
        dots_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        dots_p.paragraph_format.space_after = Pt(0)
        dots_run = dots_p.add_run("........................")

        page_p = cells[2].paragraphs[0]
        page_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        page_p.paragraph_format.space_after = Pt(0)
        page_run = page_p.add_run(str(page))

        for run in (title_run, dots_run, page_run):
            run.font.size = Pt(9.5)
        if level == 0:
            title_run.bold = True
            page_run.bold = True
            title_run.font.color.rgb = RGBColor.from_string(NAVY)
            page_run.font.color.rgb = RGBColor.from_string(NAVY)
    return table


def add_update_fields_setting(document):
    settings = document.settings._element
    update_fields = settings.find(qn("w:updateFields"))
    if update_fields is None:
        update_fields = OxmlElement("w:updateFields")
        settings.append(update_fields)
    update_fields.set(qn("w:val"), "true")


def add_para(document, text="", style=None, align=None, bold_lead=None):
    p = document.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    if bold_lead and text.startswith(bold_lead):
        p.add_run(bold_lead).bold = True
        p.add_run(text[len(bold_lead):])
    else:
        p.add_run(text)
    return p


def add_bullet(document, text, level=0):
    style = "List Bullet" if level == 0 else "List Bullet 2"
    return add_para(document, text, style=style)


def add_number(document, text):
    return add_para(document, text, style="List Number")


def add_callout(document, title, text, fill=PALE_BLUE):
    table = document.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    cell = table.cell(0, 0)
    set_cell_shading(cell, fill)
    set_cell_margins(cell, top=180, start=220, bottom=180, end=220)
    set_cell_border(cell, start={"val": "single", "sz": "18", "color": TEAL})
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(title)
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(NAVY)
    p2 = cell.add_paragraph(text)
    p2.paragraph_format.space_after = Pt(0)
    return table


def add_reference(document, citation, url):
    p = document.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.65)
    p.paragraph_format.first_line_indent = Cm(-0.65)
    p.paragraph_format.space_after = Pt(6)
    p.add_run(citation + " ")
    add_hyperlink(p, "Available online", url)
    return p


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_cant_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def style_table(table, header_fill=NAVY, first_col_bold=False, font_size=9):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for r_idx, row in enumerate(table.rows):
        set_cant_split(row)
        if r_idx == 0:
            set_repeat_table_header(row)
        for c_idx, cell in enumerate(row.cells):
            set_cell_margins(cell, top=90, start=90, bottom=90, end=90)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if r_idx == 0:
                set_cell_shading(cell, header_fill)
            elif r_idx % 2 == 0:
                set_cell_shading(cell, LIGHT_GREY)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                for run in p.runs:
                    run.font.size = Pt(font_size)
                    if r_idx == 0:
                        run.bold = True
                        run.font.color.rgb = RGBColor.from_string(WHITE)
                    elif first_col_bold and c_idx == 0:
                        run.bold = True


doc = Document()
section = doc.sections[0]
section.page_width = Cm(21.0)
section.page_height = Cm(29.7)
section.top_margin = Cm(2.0)
section.bottom_margin = Cm(1.8)
section.left_margin = Cm(2.2)
section.right_margin = Cm(2.0)
section.header_distance = Cm(0.8)
section.footer_distance = Cm(0.8)
section.different_first_page_header_footer = True

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Aptos"
normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Aptos")
normal.font.size = Pt(10.8)
normal.font.color.rgb = RGBColor.from_string("263238")
normal.paragraph_format.line_spacing = 1.15
normal.paragraph_format.space_after = Pt(6)

for style_name in ("List Bullet", "List Bullet 2", "List Number"):
    styles[style_name].font.name = "Aptos"
    styles[style_name].font.size = Pt(10.8)
    styles[style_name].paragraph_format.space_after = Pt(4)

h1 = styles["Heading 1"]
h1.font.name = "Aptos Display"
h1.font.size = Pt(17)
h1.font.bold = True
h1.font.color.rgb = RGBColor.from_string(NAVY)
h1.paragraph_format.space_before = Pt(14)
h1.paragraph_format.space_after = Pt(8)
h1.paragraph_format.keep_with_next = True

h2 = styles["Heading 2"]
h2.font.name = "Aptos Display"
h2.font.size = Pt(13)
h2.font.bold = True
h2.font.color.rgb = RGBColor.from_string(TEAL)
h2.paragraph_format.space_before = Pt(10)
h2.paragraph_format.space_after = Pt(5)
h2.paragraph_format.keep_with_next = True

h3 = styles["Heading 3"]
h3.font.name = "Aptos"
h3.font.size = Pt(11.5)
h3.font.bold = True
h3.font.color.rgb = RGBColor.from_string(NAVY)
h3.paragraph_format.space_before = Pt(7)
h3.paragraph_format.space_after = Pt(4)
h3.paragraph_format.keep_with_next = True

header = section.header
hp = header.paragraphs[0]
hp.text = "RECOMMENDATION REPORT   |   NEPAL"
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
for run in hp.runs:
    run.font.name = "Aptos"
    run.font.size = Pt(8)
    run.font.bold = True
    run.font.color.rgb = RGBColor.from_string(MID_GREY)

footer = section.footer
fp = footer.paragraphs[0]
fp.add_run("Supporting Women Entrepreneurs in Nepal   •   ")
for run in fp.runs:
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor.from_string(MID_GREY)
add_page_number(fp)

add_update_fields_setting(doc)

# Title page
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(70)
p.paragraph_format.space_after = Pt(10)
r = p.add_run("RECOMMENDATION REPORT")
r.font.name = "Aptos"
r.font.size = Pt(12)
r.font.bold = True
r.font.color.rgb = RGBColor.from_string(TEAL)
r.font.letter_spacing = Pt(1)

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(12)
r = p.add_run("Supporting Women\nEntrepreneurs in Nepal")
r.font.name = "Aptos Display"
r.font.size = Pt(28)
r.font.bold = True
r.font.color.rgb = RGBColor.from_string(NAVY)
add_bottom_border(p, color=TEAL, size="18")

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(28)
r = p.add_run("Turning access into sustainable growth, decent work and wider economic participation")
r.font.size = Pt(14)
r.font.color.rgb = RGBColor.from_string(MID_GREY)
r.italic = True

add_callout(
    doc,
    "Central recommendation",
    "Build one connected support pathway that helps women formalise, obtain suitable finance, improve business capability, reach dependable markets and manage care and mobility constraints. Nepal does not need another isolated training scheme; it needs services that follow an enterprise from start-up to growth.",
    fill=PALE_TEAL,
)

doc.add_paragraph().paragraph_format.space_after = Pt(60)
details = doc.add_table(rows=4, cols=2)
details.alignment = WD_TABLE_ALIGNMENT.LEFT
labels = ["Prepared by", "Course / institution", "Submission date", "Approximate length"]
values = ["____________________________", "____________________________", "September 2026", "About 3,000 words (main report)"]
for i, (label, value) in enumerate(zip(labels, values)):
    details.cell(i, 0).text = label
    details.cell(i, 1).text = value
    details.cell(i, 0).paragraphs[0].runs[0].bold = True
    details.cell(i, 0).paragraphs[0].runs[0].font.color.rgb = RGBColor.from_string(NAVY)
    for cell in details.rows[i].cells:
        set_cell_margins(cell, top=70, start=0, bottom=70, end=120)
        set_cell_border(cell, bottom={"val": "single", "sz": "4", "color": "D0D5DD"})

doc.add_page_break()

# Table of contents
p = doc.add_heading("Table of Contents", level=1)
add_bottom_border(p, color=TEAL, size="8")
add_manual_toc(doc)
add_callout(
    doc,
    "Page guide",
    "Each contents entry uses a dotted guide leading to its page number for quick reference.",
    fill=LIGHT_GREY,
)
doc.add_page_break()

# Executive Summary
doc.add_heading("Executive Summary", level=1)
add_para(
    doc,
    "Women already make a substantial contribution to Nepal’s enterprise economy, yet their businesses remain concentrated at the smallest end of the market. The National Economic Census 2018 counted 923,356 establishments. Its later analysis found that 26.9 per cent had female owners and 29.6 per cent had female managers. Women also represented 37.7 per cent of people engaged in establishments. However, 98.3 per cent of establishments managed by women were micro-sized, employing one to nine people. Average sales and profit were far lower in female-managed establishments than in male-managed ones (Central Bureau of Statistics [CBS], 2021). These figures show both strong entrepreneurial activity and a serious problem of scale.",
)
add_para(
    doc,
    "Nepal has a supportive policy base. The Industrial Enterprises Act 2076 (2020) provides a 35 per cent registration-fee exemption for an industry or firm solely owned by a woman, a 20 per cent exemption on industrial-property registration charges, and priority for space in industrial zones or villages. Concessional lending has also reached many women: the Economic Survey 2023/24 reported NPR 46.48 billion in outstanding women-entrepreneur loans held by 76,975 borrowers in mid-March 2024. Even so, collateral, weak credit records, limited information, uneven local services and delayed subsidy processes continue to restrict finance in practice. Business registration involves several offices, and women often receive short training without the mentoring, technology, market linkages or working capital needed afterwards.",
)
add_para(
    doc,
    "This report recommends one connected, locally delivered support pathway. The priority actions are to establish women’s enterprise desks in selected municipalities; expand cash-flow-based loans backed by partial credit guarantees; replace one-off training with twelve-month mentoring and digital support; create supplier-development and procurement routes; include childcare, safe mobility and household engagement in enterprise programmes; and publish a common results dashboard using sex-, province- and enterprise-size-disaggregated data. A phased approach should start with pilots in diverse municipalities, measure business survival, sales, jobs and procurement—not only the number trained—and expand what works. This would help Nepal turn many small, informal or survival-led activities into productive enterprises that create income, decent work and local economic resilience.",
)

# Introduction
doc.add_heading("1. Introduction", level=1)
doc.add_heading("1.1 Purpose and issue", level=2)
add_para(
    doc,
    "The purpose of this report is to recommend practical ways for government, financial institutions, business associations and development partners to support women entrepreneurs in Nepal. The core issue is not a lack of enterprise or ambition. Women operate shops, farms, tourism services, food-processing units, handicraft businesses, digital ventures and home-based enterprises across the country. The difficulty is that many remain informal, under-financed and isolated from larger markets. As a result, they work hard but cannot reliably invest, hire, meet quality standards or protect themselves from shocks.",
)
add_para(
    doc,
    "Supporting women-owned enterprises is therefore both a gender-equality measure and an economic strategy. The World Bank’s analysis of the Nepal Living Standards Survey 2023/24 put women’s paid labour-force participation at 24.4 per cent, compared with 52.7 per cent for men. Entrepreneurship can widen women’s access to income where salaried work is scarce, particularly outside major urban centres. But self-employment should not be treated automatically as empowerment. A low-profit activity carried out around unpaid care work may offer flexibility without providing security, voice or growth. Policy should focus on the quality and sustainability of the enterprise, not simply count a woman as self-employed.",
)

doc.add_heading("1.2 Nepal’s present opportunity", level=2)
add_para(
    doc,
    "Several developments make action timely. Digital payments and branchless services are spreading, and Nepal Rastra Bank’s Financial Inclusion Index rose from 0.47 in 2023/24 to 0.53 in 2024/25. The 2024 Financial Inclusion Policy gives a basis for reaching underserved groups. Nepal also has active organisations such as the Federation of Woman Entrepreneurs’ Associations of Nepal (FWEAN), chambers of commerce, cooperatives and local governments. In February 2026, the World Bank approved a USD 95 million sustainable and inclusive finance operation that includes new credit-guarantee products for underserved groups such as women-led businesses. These measures can be joined into a clearer national-to-local pathway instead of operating as separate opportunities that are difficult for a new entrepreneur to navigate.",
)

# Methodology
doc.add_heading("2. Methodology", level=1)
add_para(
    doc,
    "This is a desk-based recommendation report. It reviews Nepal-specific laws, official statistics and recent policy documents from the National Statistics Office, Ministry of Finance, Nepal Rastra Bank and Department of Industry. It also draws on evidence from the ILO, UN Women and the World Bank. The analysis uses the ILO women’s entrepreneurship development framework, which considers rules and policy coordination, finance, business-development services, markets and technology, and women’s representation. Evidence was compared across sources and converted into actions that can be delivered through Nepal’s federal, provincial and local systems.",
)
add_para(
    doc,
    "The report has two limitations. The latest full economic census evidence is from 2018, so it does not capture every post-pandemic change or the newest digital businesses. In addition, national figures can hide major differences by province, caste and ethnicity, disability, age, marital status, rural location and enterprise type. For that reason, the recommendations call for new disaggregated data and local pilots rather than assuming that one design will suit every woman.",
)

# Findings
doc.add_heading("3. Findings", level=1)
doc.add_heading("3.1 Participation is visible, but business scale is small", level=2)
add_para(
    doc,
    "The economic census confirms that women are not absent from business. It identified 247,880 women-owned establishments and 273,436 establishments with female managers. Yet the same evidence shows a sharp scale and productivity gap. Nearly all female-managed establishments were micro enterprises. Their average annual sales were about NPR 1 million, compared with NPR 4.1 million for male-managed establishments, while average profit was NPR 343,000 versus NPR 1.2 million. Women were more concentrated in retail, accommodation and food, health, education and other services, and less represented in higher-capital or technology-intensive areas. The practical challenge is to help viable firms cross from household activity into stable micro, small and medium enterprises without excluding women who are still at the idea stage.",
)

doc.add_heading("3.2 Finance exists, but it is not always usable for growth", level=2)
add_para(
    doc,
    "Women’s concessional credit is one of Nepal’s most visible support measures. Its reach shows strong demand, but the declining outstanding amount and borrower count reported between mid-2023 and mid-March 2024 also suggest that access can be unstable. Women commonly lack land or buildings registered in their own names, a long formal credit history, audited accounts or a guarantor acceptable to a bank. Microfinance may be easier to reach but often provides smaller, shorter loans than a growing enterprise needs. UN Women’s 2023 policy brief also identifies cultural, structural and institutional barriers, including limited information about suitable services. A scheme can therefore exist on paper while the women most in need of it cannot apply successfully or use it for expansion.",
)

doc.add_heading("3.3 Training is fragmented from the rest of the business journey", level=2)
add_para(
    doc,
    "Many programmes offer a short course in entrepreneurship, bookkeeping or production. Training can build confidence, but information alone does not solve weak product design, irregular cash flow, packaging, certification, digital security, taxation or negotiation with buyers. The ILO’s 2023 study of Kathmandu and Pokhara found gaps across finance, human capital, markets, support, policy and culture, including weak centralised information about government programmes. Women outside provincial capitals face added travel, language and connectivity barriers. Support works better when a named adviser follows the enterprise, helps solve real problems and links training to finance and markets.",
)

doc.add_heading("3.4 Formalisation and market access remain difficult", level=2)
add_para(
    doc,
    "Around half of the establishments in the 2018 Economic Census were not registered. An ILO case from Nepal describes a woman entrepreneur visiting the ward office, Inland Revenue Department and cottage-industry office over several days to formalise a home-based business. The exact process varies by activity and location, but the wider lesson remains: multiple procedures, unclear fees and fear of taxation can discourage registration. Formalisation brings little value if it is not followed by access to credit, government procurement, social protection, larger buyers or export support. Women also have smaller networks and less bargaining power with traders, limiting their ability to move beyond local, low-margin sales.",
)

doc.add_heading("3.5 Social norms, care and mobility shape business decisions", level=2)
add_para(
    doc,
    "Business support is often designed as though entrepreneurs have equal time and freedom to travel. Many Nepali women combine enterprise work with cooking, childcare, elder care and farming. They may need family approval to travel, attend residential training or work late, and can face harassment in transport, marketplaces or online. A 2024 World Bank study covering 2,000 married women and men in four provinces found that social expectations around household roles and women’s presence in public spaces were relevant to women’s work decisions. These constraints are economic, not merely personal: they reduce the hours available for the enterprise, narrow the choice of sector and prevent women from meeting buyers or visiting banks.",
)

doc.add_heading("3.6 Current support is promising but insufficiently connected", level=2)
add_para(
    doc,
    "Nepal’s legal concessions, financial-inclusion agenda, credit programmes and strong women’s business networks form a useful foundation. The gap is coordination and accountability. Different institutions count a “woman entrepreneur” differently, and ownership on a registration certificate does not always mean that the woman controls the business. Programmes commonly report loans issued or people trained, but not whether a business survived, increased sales, entered a new market or created decent jobs. Without a shared referral system and common indicators, entrepreneurs repeat applications while agencies cannot see where women drop out of the support pathway.",
)

doc.add_heading("Key Evidence at a Glance", level=2)
evidence = [
    ("923,356", "Establishments counted nationwide", "National Economic Census 2018"),
    ("26.9%", "Establishments with female owners", "CBS, Women in Business analysis"),
    ("29.6%", "Establishments with female managers", "CBS, Women in Business analysis"),
    ("NPR 46.48bn", "Outstanding women-entrepreneur concessional loans to 76,975 borrowers, mid-March 2024", "Economic Survey 2023/24"),
    ("24.4%", "Women’s paid labour-force participation; men 52.7%, 2023/24", "World Bank analysis of NLSS"),
    ("0.53", "Nepal’s Financial Inclusion Index in 2024/25; 0.47 one year earlier", "Nepal Rastra Bank"),
]
table = doc.add_table(rows=1, cols=3)
table.rows[0].cells[0].text = "Measure"
table.rows[0].cells[1].text = "What it shows"
table.rows[0].cells[2].text = "Source"
for measure, meaning, source in evidence:
    cells = table.add_row().cells
    cells[0].text = measure
    cells[1].text = meaning
    cells[2].text = source
style_table(table, first_col_bold=True, font_size=8.8)

# Recommendations
doc.add_heading("4. Recommendations, Analysis and Discussion", level=1)
add_callout(
    doc,
    "Recommended policy direction",
    "Move from scattered benefits to a single growth pathway: identify → formalise → finance → improve → sell → scale. Each woman should be able to enter at the stage her business has reached, rather than repeat the same beginner training.",
    fill=PALE_TEAL,
)

doc.add_heading("4.1 Create women’s enterprise service desks at local level", level=2)
add_para(
    doc,
    "The Ministry of Industry, Commerce and Supplies should develop a standard service model that provinces and municipalities can adapt. Pilot desks in about fifteen urban and rural local levels should provide a single first point of contact. A trained enterprise adviser would assess the business, explain registration and tax duties in plain Nepali or local language, help prepare documents, and refer the entrepreneur to finance, skills, standards, digital services and buyers. Mobile clinics should visit remote wards. Existing local staff, industry offices, chambers, FWEAN chapters and cooperatives can be connected instead of building an expensive new institution.",
)
add_para(
    doc,
    "This recommendation makes legal benefits usable. A registration-fee concession has little effect when a woman does not know it exists or must visit several offices to claim it. The desk should offer a written cost and timeline, a case number and a grievance route. Formalisation support should be conditional on no unnecessary fee and linked to a clear benefit within three months, such as a bank-ready record, procurement orientation or social-security registration. Success should be measured by completed formalisation and business use of services, not the number of information sessions.",
)

doc.add_heading("4.2 Build a finance ladder for different stages of growth", level=2)
add_para(
    doc,
    "Nepal Rastra Bank, the Deposit and Credit Guarantee Fund and participating banks should create a women-led enterprise window with three levels: small start-up finance; working-capital and equipment loans for established micro firms; and larger growth finance for firms with reliable sales. Credit assessment should use cash flow, digital payment history, purchase orders, movable assets and group guarantees where suitable—not only land. Partial guarantees should absorb part of the lender’s risk while leaving banks responsible for sound appraisal. Transparent eligibility rules and public reporting would reduce the risk that a business is registered in a woman’s name only to obtain a concession.",
)
add_para(
    doc,
    "Finance must be paired with a short diagnostic, bookkeeping support and repayment plans that reflect business cycles in agriculture, tourism and handicrafts. Banks should name trained women-enterprise officers and publish approval time, rejection reasons, average loan size and province-level reach. The newer sustainable-finance operation can support guarantee design and data systems. Grants should be limited to testing products, certification, climate-resilient equipment or the poorest start-ups; normal working capital should use repayable finance so that the programme can continue. This approach addresses the missing middle between small microfinance loans and heavily collateralised commercial lending.",
)

doc.add_heading("4.3 Replace one-off training with twelve-month growth support", level=2)
add_para(
    doc,
    "Provincial and local governments should procure outcome-based business-development services. Each selected entrepreneur would receive a practical package for up to twelve months: business costing, cash-flow records, digital payments, marketing, quality control, customer care, taxation and safe online trading. An adviser should meet the entrepreneur monthly and bring in specialists when needed. Training groups should be separated by business stage and sector, because a woman testing a pickle business needs different support from a registered tourism firm seeking export clients.",
)
add_para(
    doc,
    "Providers should be partly paid when agreed milestones are verified, such as keeping three months of accounts, introducing compliant packaging, obtaining a standard, increasing repeat customers or securing a purchase order. Digital lessons can reduce travel, but offline materials, local language and in-person coaching remain necessary. Partnerships with CTEVT, universities, private service firms and experienced women entrepreneurs would broaden the mentor pool and avoid a Kathmandu-only model.",
)

doc.add_heading("4.4 Open dependable markets, not only exhibitions", level=2)
add_para(
    doc,
    "The Public Procurement Monitoring Office and relevant ministries should test a supplier-diversity programme within existing procurement law. It should define a genuinely women-owned and controlled enterprise, build a verified supplier directory, divide suitable contracts into smaller lots, publish bidding calendars and train procurement officers to apply rules consistently. Early opportunities could include catering, uniforms and textiles, cleaning products, local food, tourism services, digital content and selected professional services. Procurement must remain competitive and quality-based; the purpose is to remove information and scale barriers, not lower standards.",
)
add_para(
    doc,
    "Private anchors—hotels, retailers, banks, hospitals and larger manufacturers—should be invited to run supplier-development cohorts with chambers and FWEAN. Producer groups can aggregate volume, share transport and packaging, and negotiate better prices while preserving each member’s ownership. Support for certification, traceability, branding, e-commerce photography and logistics is more likely to generate repeat sales than a one-day fair. Progress should be measured by the value and recurrence of contracts awarded, including the share reaching businesses outside Bagmati Province.",
)

doc.add_heading("4.5 Treat care, safety and mobility as business infrastructure", level=2)
add_para(
    doc,
    "Every publicly funded enterprise programme should budget for participation costs that commonly exclude women. Options include childcare at training sites, small care vouchers, daytime and local scheduling, safe transport for late or distant events, and mobile advisory visits. Programmes should map harassment risks in markets and online and provide a confidential complaint route. For home-based businesses, advisers should discuss safe workspace, fair division of household responsibilities and the difference between family help and unpaid labour.",
)
add_para(
    doc,
    "Short household orientation sessions can help spouses and other family members understand the enterprise plan, the loan obligation and the benefits of sharing care. This must not make male permission a condition of support. Its purpose is to reduce practical resistance and increase the woman’s control over time, income and decisions. Participation and business outcomes should be checked by care responsibility, disability, location and social group so that the easiest-to-reach women do not receive every opportunity.",
)

doc.add_heading("4.6 Establish shared leadership, definitions and results data", level=2)
add_para(
    doc,
    "A small Women’s Enterprise Coordination Council should be convened by the industry ministry and include Nepal Rastra Bank, finance and labour agencies, provincial and local representatives, the National Statistics Office, FWEAN, other private-sector bodies, banks, cooperatives and representatives of Dalit, Madhesi, Indigenous, disabled and rural women entrepreneurs. Its first tasks should be to agree a definition of a women-owned and women-controlled enterprise, map programmes, assign referrals and publish an annual action plan.",
)
add_para(
    doc,
    "A public dashboard should follow the full pathway: enquiries, registrations, applications, approvals, rejection reasons, mentoring completion, finance received, sales, business survival, jobs, procurement and grievances. Data should be disaggregated while protecting personal information. An independent review after twenty-four months should compare supported firms with similar non-participants and gather women’s own accounts of what changed. Programmes that only produce attendance should be redesigned or closed, while effective local models should receive multi-year funding.",
)

doc.add_heading("5. Proposed Next Steps and Conclusion", level=1)
doc.add_heading("5.1 Immediate next steps", level=2)
add_number(doc, "Within three months, agree the national definition of a women-owned and controlled enterprise and name the lead agencies for each part of the support pathway.")
add_number(doc, "Within six months, select a diverse group of pilot municipalities, map existing services and train local enterprise advisers and bank focal persons.")
add_number(doc, "Within nine months, launch the local desks, finance ladder and first supplier-development cohorts with a common application and referral record.")
add_number(doc, "At twelve months, publish the first dashboard and use entrepreneur feedback to repair delays, exclusion and duplication.")
add_number(doc, "At twenty-four months, complete an independent outcome review and scale only the models that improve survival, sales, jobs, market access and women’s control over business decisions.")

doc.add_heading("5.2 Conclusion", level=2)
add_para(
    doc,
    "Nepal does not begin from zero. Women already own and manage hundreds of thousands of establishments, and the country has laws, financial programmes, networks and digital infrastructure that can support them. The weakness is the space between these pieces. A woman may receive training but no buyer, register but gain no service, or qualify for a subsidised loan but lack acceptable collateral and records. That fragmented experience keeps too many businesses small and insecure.",
)
add_para(
    doc,
    "The recommended response is practical: make local entry simple, finance the right stage, stay with the business long enough to build capability, create repeat markets, recognise care and safety constraints, and hold institutions accountable for outcomes. If pilots are designed with women from different provinces and social groups, Nepal can learn quickly and spend more effectively. The result should not be a larger number of nominal women entrepreneurs, but more women who genuinely control productive businesses, earn stable incomes, create decent jobs and participate in the country’s economic decisions.",
)

# Appendix
doc.add_page_break()
doc.add_heading("Appendix A: Implementation Matrix", level=1)
matrix_rows = [
    ("Local enterprise desks", "MoICS / local governments", "Provinces, industry offices, IRD, FWEAN, chambers", "0–9 months", "Completed registrations; referrals used; time and cost"),
    ("Women-led finance window", "NRB / DCGF", "Banks, MFIs, cooperatives, World Bank operation", "3–12 months", "Applications, approval rate, loan size, repayment, provincial reach"),
    ("Twelve-month growth support", "Provinces / local governments", "CTEVT, universities, private providers, mentors", "6–18 months", "Accounts maintained; sales; repeat customers; standards"),
    ("Supplier development", "PPMO / MoICS", "Public buyers, large firms, chambers, FWEAN", "6–24 months", "Contract value; repeat orders; firms outside Bagmati"),
    ("Care, safety and mobility", "All programme owners", "Local providers, transport and care services", "From launch", "Participation, completion, complaints resolved, control over time"),
    ("Coordination and dashboard", "MoICS / NSO", "NRB, provinces, local levels, women’s groups", "0–24 months", "Common definition; annual data; independent review"),
]
table = doc.add_table(rows=1, cols=5)
for idx, title in enumerate(("Action", "Lead", "Key partners", "Timing", "Core measures")):
    table.rows[0].cells[idx].text = title
for row in matrix_rows:
    cells = table.add_row().cells
    for idx, value in enumerate(row):
        cells[idx].text = value
style_table(table, first_col_bold=True, font_size=7.7)

doc.add_heading("Appendix B: Suggested Monitoring Questions", level=1)
for question in [
    "Did the entrepreneur receive the service in her preferred location and language?",
    "Does she make the main decisions on borrowing, spending, pricing, hiring and use of profit?",
    "Has the enterprise kept basic accounts and separated household and business money?",
    "Did sales, profit, repeat orders or productive assets improve after support?",
    "Did the enterprise create or improve jobs with fair pay and safe working conditions?",
    "Which applicants were rejected or dropped out, and what barriers explain the pattern?",
    "Did benefits reach women across provinces, rural areas and different social groups?",
]:
    add_bullet(doc, question)

# References
doc.add_page_break()
doc.add_heading("References", level=1)
references = [
    (
        "Alaref, J., Patil, A., Rahman, T., & Muñoz Boudet, A. M. (2024). Women’s labor force participation in Nepal: An exploration of the role of social norms (Policy Research Working Paper 10810). World Bank.",
        "https://documents.worldbank.org/en/publication/documents-reports/documentdetail/099816406182414601",
    ),
    (
        "Central Bureau of Statistics. (2021). National Economic Census 2018: Analytical report—Women in business. Government of Nepal.",
        "https://giwmscdnone.gov.np/media/app/public/36/posts/1693998585_42.pdf",
    ),
    (
        "Department of Industry. (2020). The Industrial Enterprises Act, 2076 (2020). Government of Nepal.",
        "https://www.doind.gov.np/detail/5c6a4832-321c-40b9-8b54-a0f4e94edce0",
    ),
    (
        "International Labour Organization. (2020). Assessment of women’s entrepreneurship development: Action-oriented research for a business ecosystem conducive to the empowerment of women entrepreneurs.",
        "https://www.ilo.org/publications/assessment-womens-entrepreneurship-development",
    ),
    (
        "International Labour Organization. (2021). Decent work along the supply chains: Nurturing women’s entrepreneurship in Nepal.",
        "https://www.ilo.org/resource/article/decent-work-along-supply-chains-nurturing-women%E2%80%99s-entrepreneurship-nepal",
    ),
    (
        "International Labour Organization. (2023). Building inclusive entrepreneurship ecosystems in Nepal: An analysis of Kathmandu and Pokhara.",
        "https://www.ilo.org/publications/building-inclusive-entrepreneurship-ecosystems-nepal-analysis-kathmandu-and",
    ),
    (
        "Ministry of Finance. (2024). Economic Survey 2023/24. Government of Nepal.",
        "https://giwmscdntwo.gov.np/media/pdf_upload/MOF_Economic%20Survey%20ENG%202023-24%20book%20Final_for%20WEB_miwtpw0.pdf",
    ),
    (
        "Nepal Rastra Bank. (2026). Financial Inclusion Index for Nepal 2025.",
        "https://www.nrb.org.np/contents/uploads/2026/02/FInancial-Inclusion-Index-2025.pdf",
    ),
    (
        "National Statistics Office. (2019). National Economic Census 2018 data and national reports. Government of Nepal.",
        "https://data.nsonepal.gov.np/organization/economic-census",
    ),
    (
        "UN Women. (2023). Accelerating the financial inclusion of women in Nepal.",
        "https://asiapacific.unwomen.org/en/digital-library/publications/2023/07/accelerating-the-financial-inclusion-of-women-in-nepal",
    ),
    (
        "World Bank. (2025). Nurturing Nepali talent to foster economic growth.",
        "https://thedocs.worldbank.org/en/doc/046021b791dda7b320bc3b778fcd99b6-0310012025/original/Nepal-HCR-long-PPT-Feb-28-2025.pdf",
    ),
    (
        "World Bank. (2026, February 3). Nepal: World Bank approves $95 million to support sustainable and inclusive finance.",
        "https://www.worldbank.org/en/news/press-release/2026/02/03/nepal-world-bank-approves-95-million-to-support-sustainable-and-inclusive-finance",
    ),
]
for citation, url in references:
    add_reference(doc, citation, url)

# Document properties
doc.core_properties.title = "Recommendation Report on Supporting Women Entrepreneurs in Nepal"
doc.core_properties.subject = "Policy recommendations for strengthening women-owned and women-led enterprises in Nepal"
doc.core_properties.author = ""
doc.core_properties.keywords = "Nepal, women entrepreneurs, MSME, financial inclusion, recommendation report"

# Avoid single lines at page breaks and keep headings with following text.
for paragraph in doc.paragraphs:
    paragraph.paragraph_format.widow_control = True

doc.save(OUTPUT)

# Report an approximate main-text word count (Executive Summary through Conclusion; excludes appendices/references).
all_text = []
in_main = False
for p in doc.paragraphs:
    if p.text == "Executive Summary":
        in_main = True
    if p.text == "Appendix A: Implementation Matrix":
        in_main = False
    if in_main:
        all_text.append(p.text)
word_count = len(re.findall(r"\b[\w’'-]+\b", " ".join(all_text), flags=re.UNICODE))
print(f"Created: {OUTPUT}")
print(f"Approximate main-report word count: {word_count}")
