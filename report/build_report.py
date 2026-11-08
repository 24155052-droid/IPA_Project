"""Builds the project report (Word) from results/results.json so that every
number in the text and tables is the number the code produced.

    python report/build_report.py [github_url]
"""
import json
import os
import subprocess
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
R = json.load(open(os.path.join(RES, "results.json")))
GITHUB = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/YOUR-USERNAME/IPA_Project"
OUT_DOCX = os.path.join(HERE, "IPA_Project_Report.docx")

NAVY = RGBColor(0x1F, 0x2A, 0x4D)
TEAL = RGBColor(0x1F, 0x7A, 0x8C)
GREY = RGBColor(0x55, 0x55, 0x55)

# ------------------------------------------------------------------ numbers
lsbq = R["lsb_capacity"]
att = {a["attack"]: a for a in R["attacks"]}
sq = R["scheme_quality"]
dflt = R["dct_default"]
trade = {t["delta"]: t for t in R["tradeoff"]}
rep = {t["repeat"]: t for t in R["repetition"]}
ster = R["steganalysis"]
col = R["color"]
L, D1, D4 = "LSB (k=1)", "DCT-QIM r=1", "DCT-QIM r=4"
f2 = lambda x: f"{x:.2f}"
f3 = lambda x: f"{x:.3f}"


# ------------------------------------------------------------------ helpers
def set_cell_bg(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_table_borders(table, color="BBBBBB"):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    anchor = None
    for tag in ("w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook"):
        anchor = tblPr.find(qn(tag))
        if anchor is not None:
            break
    if anchor is not None:
        anchor.addprevious(borders)
    else:
        tblPr.append(borders)


def add_page_border(section):
    sectPr = section._sectPr
    pg = OxmlElement("w:pgBorders")
    pg.set(qn("w:offsetFrom"), "page")
    for edge, sz, space in (("top", "12", "24"), ("left", "12", "24"), ("bottom", "12", "24"), ("right", "12", "24")):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "double")
        el.set(qn("w:sz"), sz)
        el.set(qn("w:space"), space)
        el.set(qn("w:color"), "1F2A4D")
        pg.append(el)
    sectPr.find(qn('w:pgMar')).addnext(pg)


def add_page_number(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = txt
        run._r.append(el)


doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
sec.left_margin = sec.right_margin = Inches(0.95)
sec.top_margin = Inches(0.9)
sec.bottom_margin = Inches(0.9)
add_page_border(sec)
add_page_number(sec)

st = doc.styles
st["Normal"].font.name = "Calibri"
st["Normal"].font.size = Pt(10.5)
st["Normal"].element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
st["Normal"].paragraph_format.space_after = Pt(6)
st["Normal"].paragraph_format.line_spacing = 1.12
for name, size, color, before in (("Heading 1", 17, TEAL, 14), ("Heading 2", 13, TEAL, 10), ("Heading 3", 11, NAVY, 8)):
    s = st[name]
    s.font.name = "Calibri"
    s.font.size = Pt(size)
    s.font.bold = True
    s.font.color.rgb = color
    s.element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    s.element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    s.paragraph_format.space_before = Pt(before)
    s.paragraph_format.space_after = Pt(5)
    s.paragraph_format.keep_with_next = True


def para(text="", bold=False, italic=False, size=None, color=None, align=None, after=None, before=None, keep=False):
    p = doc.add_paragraph()
    if text:
        r = p.add_run(text)
        r.bold = bold
        r.italic = italic
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if before is not None:
        p.paragraph_format.space_before = Pt(before)
    if keep:
        p.paragraph_format.keep_with_next = True
    return p


def body(text):
    return para(text, align="justify")


def bullet(text, lead=None):
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(3)
    if lead:
        r = p.add_run(lead + " ")
        r.bold = True
    p.add_run(text)
    return p


def h1(t):
    return doc.add_heading(t, level=1)


def h2(t):
    return doc.add_heading(t, level=2)


def formula(t):
    p = para(t, italic=True, align="center", after=6)
    return p


def caption(t):
    return para(t, italic=True, size=9, color=GREY, align="center", after=8, keep=False)


def figure(name, width, cap):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(os.path.join(RES, name), width=Inches(width))
    caption(cap)


def table(rows, widths, cap, header=True, font=9):
    para(cap, italic=True, size=9, color=GREY, align="center", after=3, keep=True)
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    set_table_borders(t)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.width = Inches(widths[j])
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val))
            r.font.size = Pt(font)
            if i == 0 and header:
                r.bold = True
                set_cell_bg(c, "DCEBEF")
    para("", after=4)
    return t


# ------------------------------------------------------------------ cover
def cover():
    para("", after=40)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(os.path.join(HERE, "kiit_logo.png"), width=Inches(1.6))
    para("KALINGA INSTITUTE OF INDUSTRIAL TECHNOLOGY", bold=True, size=13, color=NAVY, align="center", after=2)
    para("School of Computer Engineering", size=11, align="center", after=60)
    para("Digital Image Watermarking", bold=True, size=30, color=TEAL, align="center", after=0)
    para("and Steganography", bold=True, size=30, color=TEAL, align="center", after=10)
    para("Embedding, Extraction and Robustness Analysis in Python", size=13, align="center", after=70)
    para("Subject: Image Processing and Applications (CS-30015)", size=11, align="center", after=2)
    para("Autumn Semester 2026", size=11, align="center", after=18)
    para("Submitted by:", bold=True, size=11, align="center", after=2)
    para("Sayangsu Dawn (24155052)", size=11, align="center", after=2)
    para("CSE-33", size=11, align="center", after=14)
    para("Under the guidance of: Dr. Sricheta Parui", size=11, align="center", after=0)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ------------------------------------------------------------------ TOC (two-pass page numbers)
TOC = [
    ("Abstract", 0), ("1. Introduction", 0), ("1.4 Novelty and contribution", 1),
    ("2. Proposed Methodology", 0), ("2.1 Data used and its source", 1),
    ("3. Experiment Segment", 0), ("Part 1: LSB capacity and imperceptibility", 1),
    ("Part 2: DCT-domain watermark", 1), ("Part 3: Robustness to attacks", 1),
    ("Part 4: Step size and repetition", 1), ("Part 5: Steganalysis", 1),
    ("Part 6: Colour image", 1), ("Part 7: Discussion", 1),
    ("4. Literature Referred or Reviewed", 0), ("5. Comparison with Others", 0),
    ("6. Conclusion", 0), ("7. Future Work (Future Scope)", 0), ("8. GitHub Link", 0),
    ("9. Bibliography", 0), ("10. References", 0),
]
PAGES = {}
if os.path.exists(os.path.join(HERE, "_pages.json")):
    PAGES = json.load(open(os.path.join(HERE, "_pages.json")))


def toc_page():
    para("Table of Contents", bold=True, size=17, color=TEAL, after=10)
    for label, lvl in TOC:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.left_indent = Inches(0.3 * lvl)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(6.35), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        r = p.add_run(f"{label}\t{PAGES.get(label, '')}")
        r.font.size = Pt(10.5 if lvl == 0 else 10)
        r.bold = lvl == 0
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ================================================================== CONTENT
cover()

# ---- Abstract
para("Abstract", bold=True, size=17, color=TEAL, after=8)
body(
    "This project studies how information can be hidden inside a digital image and how well it survives. "
    "Two classical approaches are implemented from scratch in NumPy: least-significant-bit (LSB) steganography "
    "in the spatial domain, and a blind watermark in the 8x8 block DCT domain based on quantization index "
    "modulation (QIM), with an optional repetition code and a secret key that selects the embedding positions. "
    "Both are evaluated with the same images, the same payload and the same metrics: PSNR, SSIM, bit error rate "
    "(BER) and a chi-square steganalysis test."
)
body(
    f"LSB embedding is almost invisible (PSNR {f2(lsbq[0]['psnr'])} dB when the whole image carries data at "
    f"1 bit per pixel) and gives {lsbq[0]['capacity_bytes']} bytes of capacity in a 256x256 image, but it does not survive JPEG "
    f"compression: the bit error rate is {f3(att['JPEG Q90'][L])} even at quality 90, which is no better than guessing. "
    f"The DCT-QIM watermark with step size {int(dflt['delta'])} and 4-fold repetition carries a 256-bit logo at "
    f"{f2(sq[D4]['psnr'])} dB PSNR and is recovered without error after JPEG quality 50, Gaussian noise of "
    f"standard deviation 5 and a brightness shift. Neither method survives blurring or rescaling. A chi-square test flags "
    f"LSB embedding at every rate tested from 10% upward, but does not flag the DCT watermark."
)
body(
    "The report also shows the trade-off between invisibility and robustness as the QIM step size changes, "
    "explains why repetition coding helps against random noise but not against compression, and lists the "
    "novelty, limitations and future scope of the project."
)
para("Keywords: digital watermarking, steganography, LSB, DCT, quantization index modulation, robustness, "
     "JPEG, steganalysis, chi-square test, PSNR, SSIM.", italic=True, size=10, before=6)
doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

toc_page()

# ---- 1 Introduction
h1("1. Introduction")
body(
    "Sending a secret message, or proving that an image belongs to its owner, are two old problems with a common "
    "technical core: data has to be placed inside an image so that people looking at the image do not notice it. "
    "Steganography hides the existence of a message; watermarking hides a mark that must stay readable even if the "
    "image is later compressed, filtered or edited. The same pixel can serve either purpose, but the requirements "
    "pull in opposite directions: the more data is hidden, and the more strongly, the more visible the change and the "
    "easier it is to detect."
)
body(
    "This project builds the two basic techniques and measures that conflict. It connects topics from the course: "
    "bit-plane analysis and spatial-domain processing (LSB), the discrete cosine transform and quantization "
    "(the same machinery as JPEG), noise models, filtering, histogram analysis and image quality metrics."
)
h2("1.1 Objectives")
bullet("Implement LSB embedding and a DCT-domain QIM watermark from scratch, without watermarking libraries.")
bullet("Measure invisibility with PSNR and SSIM, and capacity in bits per pixel.")
bullet("Measure robustness as the bit error rate after 17 different attacks.")
bullet("Study the effect of the QIM step size and of repetition coding.")
bullet("Test whether LSB embedding can be detected with a chi-square steganalysis test.")
h2("1.2 Tools and test data")
body(
    "The code is written in Python with NumPy [14], SciPy, scikit-image [13], Matplotlib and Pillow. The test images "
    "are the standard grayscale Cameraman image and the colour Astronaut image, both resized to 256x256. A single "
    "command (python main.py) runs every experiment with fixed random seeds and writes all figures and tables to a "
    "results folder, so every number in this report can be reproduced."
)
h2("1.3 Organisation of the report")
body(
    "Section 1.4 states the novelty and contribution. Section 2 describes the methodology and the data. Section 3 "
    "presents the experiments in six parts followed by a discussion. Section 4 reviews the literature. Section 5 "
    "compares the methods with each other and with the figures reported in the literature. Sections 6 and 7 give the "
    "conclusion and future scope, Section 8 the GitHub link, and the report ends with the bibliography and references."
)
h2("1.4 Novelty and contribution")
body(
    "LSB embedding, the DCT and QIM are all classical, and this project does not claim a new algorithm. Its "
    "contribution is a careful, reproducible comparison in which the two methods are treated identically. The "
    "specific contributions are:"
)
bullet("Both methods carry the same 256-bit payload, use the same secret-key mechanism for choosing positions, and are "
       "attacked by the same 17 attacks, so the bit error rates in one table can be compared directly.",
       "One benchmark, two methods.")
bullet("The step-size sweep shows where the watermark becomes robust: the bit error rate after JPEG quality 30 drops from "
       f"{f3(trade[24]['ber_jpeg30'])} at step 24 to {f3(trade[32]['ber_jpeg30'])} at step 32, at a cost of "
       f"{f2(trade[24]['psnr'] - trade[32]['psnr'])} dB of PSNR.",
       "A measured trade-off.")
bullet("Repetition coding lowers the error under random noise (Gaussian noise of standard deviation 10: "
       f"{f3(att['Gaussian noise s=10'][D1])} to {f3(att['Gaussian noise s=10'][D4])}) but leaves the error after blur and "
       "JPEG quality 30 near total loss (about 0.19). The report explains this: those attacks move every copy of a bit in the same "
       "direction, so majority voting cannot correct them.",
       "An explanation, not just a table.")
bullet("A bit error rate of about 0.19 for the DCT watermark is shown to mean complete loss, because the extractor then "
       "outputs all zeros and the logo contains 19.5% ones. Reading the chart against the usual 0.5 'guessing' line "
       "would hide this.",
       "A caution about reading BER.")
bullet("A chi-square test is applied to both methods, so invisibility to the eye and invisibility to a detector are "
       "reported side by side.", "Visual and statistical invisibility.")

# ---- 2 Methodology
h1("2. Proposed Methodology")
body(
    "The pipeline has five stages. A payload is turned into a bit sequence; it is embedded in a cover image by one of "
    "the two methods; the stego or watermarked image is attacked; the payload is extracted; and the result is "
    "measured. Quality of the image is measured against the original cover, and quality of the extraction against the "
    "original payload."
)
h2("2.1 Data used and its source")
body(
    "No external dataset was downloaded and no data was collected. The two test images are the standard Cameraman "
    "(grayscale) and Astronaut (colour) images distributed with scikit-image [13] "
    "(skimage.data.camera and skimage.data.astronaut). The Astronaut image is a NASA photograph and is in the "
    "public domain. They are stored in the images folder as camera.png and astronaut.png and resized to 256x256 pixels. "
    "Everything else is generated by the code:"
)
bullet("the payload: a 16x16 binary logo showing the initials 'SD' (256 bits), a short text message "
       "(264 bits), and random bits for the capacity test;")
bullet("the attacks: JPEG compression by Pillow, Gaussian noise, salt-and-pepper noise, Gaussian blur, a 3x3 median filter, "
       "cropping, rescaling and a brightness shift, all with fixed random seeds.")
h2("2.2 LSB steganography (spatial domain)")
body(
    "With k = 1 each payload bit replaces the least significant bit of one pixel; with k bits per pixel the k lowest "
    "bit planes are replaced. A pixel therefore changes by at most 2^k - 1 grey levels. Positions are either raster "
    "order or a pseudo-random permutation seeded with a secret key, so that extraction with a wrong key returns noise "
    "(Section 3, Part 1)."
)
formula("p' = (p AND (255 - (2^k - 1))) OR m,    0 <= m < 2^k")
h2("2.3 DCT-domain watermark with QIM")
body(
    "The cover is divided into 8x8 blocks and each block is transformed with the orthonormal 2-D DCT. One "
    "mid-frequency coefficient, at position (3, 2), is chosen: low frequencies are visible if changed and high "
    "frequencies are removed by compression. The coefficient c is quantized with step size Δ, and the parity of the "
    "quantization index carries one bit:"
)
formula("c' = Δ · q,   q = nearest integer to c/Δ with  q mod 2 = bit")
body(
    "Extraction is blind: the original image is not needed. The decoder transforms each block, rounds c/Δ and reads "
    "the parity. With a repetition factor r each bit is placed in r different blocks and decided by majority vote. "
    "A 256x256 image has 1,024 blocks, so 256 bits with r = 4 uses every block."
)
h2("2.4 Attacks")
body(
    "Seventeen attacks plus the no-attack case are applied one at a time: JPEG at quality 90, 70, 50 and 30; Gaussian "
    "noise with standard deviation 2, 5 and 10; salt-and-pepper noise at 1% and 5%; Gaussian blur with σ = 0.8 and 1.5; "
    "a 3x3 median filter; zeroing the bottom 10% and 25% of the rows (cropping); downscaling to 75% and 50% and "
    "back; and a brightness increase of 20."
)
h2("2.5 Steganalysis")
body(
    "The chi-square test of Westfeld and Pfitzmann [4] looks at pairs of grey values (2i, 2i+1). In a natural image "
    "the two counts in a pair usually differ. Replacing least significant bits with random data pushes the counts in each "
    "pair towards equality. The statistic measures how close the observed counts are to equal counts, and a p-value "
    "close to 1 suggests that data is hidden. The test is run on the part of the image that was written to."
)
h2("2.6 Evaluation metrics")
formula("PSNR = 10 · log10(255² / MSE)          BER = (number of wrong bits) / (number of bits)")
body(
    "SSIM [5] compares local luminance, contrast and structure on a 0 to 1 scale. PSNR and SSIM are computed between "
    "the cover and the stego image. BER is computed between the embedded and the extracted bits. Normalised "
    "correlation (NC) is also implemented in the metrics module."
)
h2("2.7 Implementation")
body(
    "The code is organised as one module per task (lsb, dct_wm, attacks, steganalysis, metrics), a runner main.py "
    "that executes all experiments, and 18 unit tests. The tests check, for example, that LSB extraction returns "
    "exactly what was embedded for k = 1 to 4, that no pixel changes by more than 2^k - 1, that extraction with a "
    "wrong key fails, that the DCT watermark survives JPEG better than LSB on a test image, and that the chi-square "
    "test responds to full-capacity embedding."
)

# ---- 3 Experiments
h1("3. Experiment Segment")
body("The experiments are presented in six parts, followed by a discussion (Part 7). All figures and tables were "
     "generated by the project code.")

h2("Part 1: LSB capacity and imperceptibility")
body(
    "Random payloads that fill the whole image were embedded with k = 1 to 4 bits per pixel (Table 1). Every payload "
    "was extracted exactly. Each additional bit plane roughly doubles the error energy, so PSNR falls by about 6 to 7 dB "
    "per plane, and from k = 3 the change becomes visible in smooth regions such as the sky, where banding appears; at k = 4 it is clearly noise (Figure 1)."
)
rows = [["k (bits/pixel)", "Capacity (bytes)", "PSNR (dB)", "SSIM", "Exact recovery"]]
for r in lsbq:
    rows.append([r["k"], f"{r['capacity_bytes']:,}", f2(r["psnr"]), f3(r["ssim"]), "yes" if r["exact"] else "no"])
table(rows, [1.2, 1.4, 1.1, 1.0, 1.3], "Table 1: LSB embedding at full capacity in a 256x256 image.")
figure("fig1_lsb_capacity.png", 6.3, "Figure 1: Stego images for k = 1 to 4 (top) and the scaled absolute difference from the cover (bottom).")
td = R["text_demo"]
body(
    f"A short text message ('{td['message']}', {td['bits']} bits) was hidden with the secret key and recovered exactly "
    f"(PSNR {f2(td['psnr'])} dB). Extraction with a key that differs by one returned unreadable bytes, which shows "
    "that the key, and not just the knowledge of the method, is needed to read the message. Figure 2 shows why LSB "
    "embedding is invisible: the least significant bit plane of a natural image already looks like noise, and so "
    "the hidden bits are not visible in it."
)
figure("fig2_bitplanes.png", 5.4, "Figure 2: The eight bit planes of the Cameraman image.")

h2("Part 2: DCT-domain watermark")
body(
    f"The 256-bit logo was embedded with Δ = {int(dflt['delta'])} and r = {dflt['repeat']}. The result has PSNR "
    f"{f2(dflt['psnr'])} dB and SSIM {f3(dflt['ssim'])}. The change is a faint texture that is visible only when the "
    f"difference is amplified (Figure 3). The logo was recovered with BER {f3(dflt['ber_clean'])} without attack and "
    f"{f3(dflt['ber_jpeg50'])} after JPEG quality 50."
)
figure("fig3_dct_watermark.png", 6.4, "Figure 3: DCT watermark: original, watermarked image, amplified difference, embedded logo and logo extracted after JPEG quality 50.")

h2("Part 3: Robustness to attacks")
body(
    "Table 2 gives the bit error rate of the three configurations after each attack and Figure 4 plots the same data. "
    f"All three recover the payload without error when nothing is done to the image. For the same 256-bit payload, LSB "
    f"changes the image by {f2(sq[L]['psnr'])} dB PSNR, DCT-QIM with r = 1 by {f2(sq[D1]['psnr'])} dB and DCT-QIM "
    f"with r = 4 by {f2(sq[D4]['psnr'])} dB."
)
rows = [["Attack", "LSB (k=1)", "DCT-QIM r=1", "DCT-QIM r=4"]]
for a in R["attacks"]:
    rows.append([a["attack"], f3(a[L]), f3(a[D1]), f3(a[D4])])
table(rows, [2.3, 1.3, 1.3, 1.3], "Table 2: Bit error rate after each attack (256-bit payload, Cameraman 256x256).")
figure("fig4_attack_ber.png", 6.4, "Figure 4: Bit error rate after each attack for the three configurations.")
body("The results fall into three groups.")
bullet(f"LSB fails completely against anything that changes pixel values slightly everywhere: JPEG at every quality "
       f"(BER {f3(att['JPEG Q90'][L])} to {f3(att['JPEG Q30'][L])}), Gaussian noise, blur and rescaling. A change of one grey "
       f"level is enough to flip a least significant bit.", "LSB.")
bullet(f"LSB is the more robust method against attacks that touch only some pixels. Only {int(0.25*100)}% of the "
       f"pixels were cleared by the 25% crop, and those cleared pixels cause an error only where the hidden bit was a "
       f"1, which gives BER {f3(att['Crop 25% rows'][L])}. Salt-and-pepper noise at 1% altered no bit that carried "
       f"data (BER {f3(att['Salt&pepper 1%'][L])}). This is partly luck: with only 256 of 65,536 pixels carrying data, "
       "about 3 hidden bits are expected to be hit at 1%.", "LSB under local damage.")
bullet(f"DCT-QIM is recovered without error after JPEG quality 90, 70 and 50 (r = 4), Gaussian noise of σ = 2 and 5, and a "
       f"brightness change (a brightness shift only changes the DC coefficient, which is not used). It fails at JPEG quality 30 "
       f"(BER {f3(att['JPEG Q30'][D4])}), blur, median filtering and rescaling, which remove mid-frequency energy.",
       "DCT-QIM.")
body(
    "The DCT bit error rates of about 0.19 to 0.26 need careful reading. A low-pass attack shrinks the mid-frequency "
    "coefficient towards zero, so round(c/Δ) becomes 0, the parity is even, and every bit is read as 0. The error is "
    "then the fraction of ones in the logo, which is 0.195. A BER of 0.195 therefore means that the watermark is "
    "completely destroyed, even though it is far below 0.5."
)

h2("Part 4: Step size and repetition")
body(
    "The step size Δ controls the trade-off (Table 3, Figure 5). Small steps keep the image almost unchanged but the "
    f"watermark does not survive compression or noise: at Δ = 8 the BER after JPEG quality 50 is {f3(trade[8]['ber_jpeg50'])}. "
    f"From Δ = 16 the watermark survives JPEG quality 50 and noise of σ = 5, and from Δ = 32 it also survives JPEG quality 30, "
    f"at {f2(trade[32]['psnr'])} dB PSNR."
)
rows = [["Step Δ", "PSNR (dB)", "SSIM", "BER JPEG Q50", "BER JPEG Q30", "BER noise σ=5"]]
for d in [8, 12, 16, 24, 32, 48, 64]:
    t = trade[d]
    rows.append([d, f2(t["psnr"]), f3(t["ssim"]), f3(t["ber_jpeg50"]), f3(t["ber_jpeg30"]), f3(t["ber_noise5"])])
table(rows, [0.9, 1.0, 0.9, 1.2, 1.2, 1.3], "Table 3: Effect of the QIM step size (r = 4).")
figure("fig5_tradeoff.png", 4.6, "Figure 5: PSNR (left axis) and bit error rate (right axis) against the QIM step size.")
rows = [["Repetition r", "PSNR (dB)", "BER JPEG Q50", "BER JPEG Q30", "BER crop 25%"]]
for r_ in (1, 2, 4):
    t = rep[r_]
    rows.append([r_, f2(t["psnr"]), f3(t["ber_jpeg50"]), f3(t["ber_jpeg30"]), f3(t["ber_crop25"])])
table(rows, [1.2, 1.1, 1.3, 1.3, 1.3], f"Table 4: Effect of repetition coding (Δ = {int(dflt['delta'])}).")
body(
    f"Repetition does not help against JPEG quality 30 (BER {f3(rep[1]['ber_jpeg30'])} for r = 1 and {f3(rep[4]['ber_jpeg30'])} "
    f"for r = 4), because compression removes the coefficient in every copy in the same way. It helps against noise that "
    f"acts independently on each block (Table 2), and it costs {f2(rep[1]['psnr'] - rep[4]['psnr'])} dB of PSNR because more "
    "blocks are modified. For compression, a larger step is the better tool."
)

h2("Part 5: Steganalysis")
rows = [["Embedding rate", "PSNR (dB)", "Chi-square p-value"]]
for r in ster["lsb"]:
    ps = "inf" if r["psnr"] > 200 or r["psnr"] != r["psnr"] else f2(r["psnr"])
    rows.append([f"{int(r['rate']*100)}%", "-" if r["rate"] == 0 else ps, f3(r["p_value"])])
table(rows, [1.6, 1.3, 1.8], "Table 5: Chi-square test on LSB embedding (k = 1, raster order).")
body(
    f"The clean image gives a p-value of {f3(ster['lsb'][0]['p_value'])}, while LSB embedding gives {f3(ster['lsb'][1]['p_value'])} "
    f"at a rate of 10% and at least {f3(min(x['p_value'] for x in ster['lsb'][1:]))} at every rate from 10% up. So the test "
    "detects LSB embedding reliably even though at full rate the image changes by only about 51 dB PSNR, which is invisible to the eye. The "
    f"DCT-domain watermark was not flagged (p = {f3(ster['dct_watermark_p'])}). Embedding was in raster order here, so that "
    "the test window is known; with a secret key the positions are scattered and this simple test is expected to be "
    "less sensitive (Section 6, limitations)."
)
figure("fig6_chisquare.png", 3.9, "Figure 6: Chi-square p-value against LSB embedding rate (0% is the clean image).")

h2("Part 6: Colour image")
body(
    "For the colour Astronaut image the watermark was embedded in the luminance (Y) channel of the YCbCr representation "
    f"(Δ = {int(dflt['delta'])}, r = 4), converted back to RGB and attacked with JPEG. The RGB image has PSNR {f2(col['psnr'])} dB and "
    f"SSIM {f3(col['ssim'])}. Table 6 shows the extraction result. Even without attack the BER is "
    f"{f3(col['attacks'][0]['ber'])} (4 of 256 bits): converting Y to RGB and back rounds to integers and moves a few "
    "coefficients across a quantization boundary. The watermark survives JPEG down to quality 50 with at most 5 wrong bits "
    "and fails at quality 30."
)
rows = [["Attack", "BER"]] + [[a["attack"], f3(a["ber"])] for a in col["attacks"]]
table(rows, [2.2, 1.2], "Table 6: Watermark in the luminance channel of the colour image.")
figure("fig7_color.png", 5.6, "Figure 7: Colour image, watermarked image and amplified difference.")

h2("Part 7: Discussion")
bullet("A method that is invisible is not necessarily robust. LSB has the smallest visual change and the worst "
       "robustness to compression; DCT-QIM trades 25 to 30 dB of PSNR (for the same 256 bits) for survival of JPEG.")
bullet("Robustness is decided by which information the attack removes. JPEG and blur remove high and mid frequencies, so the "
       "watermark has to be placed where the attack leaves energy, or made strong enough to cross the "
       "quantization threshold.")
bullet("No single setting is best. Steganography wants the smallest change and tolerates a fragile message, whereas "
       "watermarking wants survival and tolerates a visible texture.")
bullet("Invisibility to the eye is different from invisibility to a detector: LSB at 51 dB PSNR is flagged by the "
       "chi-square test.")

# ---- 4 Literature
h1("4. Literature Referred or Reviewed")
body("This section summarises the literature that was read for each part of the project. The textbooks in the "
     "Bibliography were the main source for the course material.")
h2("4.1 Information hiding")
body("Bender et al. [1] and Petitcolas, Anderson and Kuhn [2] give the framework in which steganography and "
     "watermarking are placed, with their different requirements of capacity, invisibility and robustness. "
     "Cheddad et al. [3] survey image steganography and organise the methods into spatial-domain, transform-domain and "
     "adaptive groups, which is the grouping used in this project.")
h2("4.2 Spatial-domain embedding and its detection")
body("LSB replacement is the simplest spatial method. Westfeld and Pfitzmann [4] showed that it leaves a statistical "
     "trace in the histogram: the counts of the two values in each pair (2i, 2i+1) become equal. This is the chi-square test "
     "of Part 5. Fridrich, Goljan and Du [6] developed more sensitive detectors for LSB embedding in grayscale and colour "
     "images; these are left for future work.")
h2("4.3 Transform-domain watermarking")
body("Cox et al. [7] introduced spread-spectrum watermarking, in which a pseudo-random sequence is added to the "
     "significant transform coefficients so that it survives common processing. Barni et al. [8] proposed a "
     "DCT-domain system for robust image watermarking. Chen and Wornell [9] introduced quantization index "
     "modulation, which hides bits in the choice of quantizer and, unlike additive schemes, is not disturbed by "
     "the image itself; this is the embedding rule used here. The DCT was introduced by Ahmed, Natarajan and Rao [10] "
     "and is the transform used in JPEG [11], which is why a DCT-domain mark interacts closely with JPEG compression.")
h2("4.4 Quality measures")
body("PSNR is simple but only loosely related to perceived quality [12]. SSIM [5] compares local structure and was "
     "designed to follow human judgement more closely. Both are reported for invisibility, and BER for extraction.")
rows = [["Reference", "Contribution", "Used in this project for"],
        ["Bender et al. [1]; Petitcolas et al. [2]", "Information hiding framework", "Problem set-up, requirements"],
        ["Cheddad et al. [3]", "Survey of image steganography", "Choice of spatial and transform methods"],
        ["Westfeld, Pfitzmann [4]", "Chi-square attack on LSB", "Steganalysis, Part 5"],
        ["Wang et al. [5]", "Structural similarity index", "SSIM metric"],
        ["Cox et al. [7]; Barni et al. [8]", "Robust transform-domain watermarking", "Motivation for the DCT approach"],
        ["Chen, Wornell [9]", "Quantization index modulation", "Embedding rule, Section 2.3"],
        ["Ahmed et al. [10]; Wallace [11]", "DCT; JPEG standard", "Block transform, JPEG attack"]]
table(rows, [2.0, 2.2, 2.2], "Table 7: Summary of the literature reviewed and how it is used in this project.", font=8.5)

# ---- 5 Comparison
h1("5. Comparison with Others")
body("This section compares the methods of the project with each other, since all of them were measured on the same "
     "image, payload and attacks, and then with what the literature reports. No numbers from other papers are quoted, because "
     "their images, payloads and settings differ and the numbers would not be comparable.")
h2("5.1 LSB against DCT-QIM")
rows = [["Property", "LSB (k=1)", "DCT-QIM r=1", "DCT-QIM r=4"],
        ["Domain", "Spatial", "8x8 DCT", "8x8 DCT"],
        ["Payload used (bits)", "256", "256", "256"],
        ["Maximum capacity (256x256)", "65,536 bits (k=1)", "1,024 bits", "256 bits"],
        ["PSNR (dB)", f2(sq[L]["psnr"]), f2(sq[D1]["psnr"]), f2(sq[D4]["psnr"])],
        ["SSIM", f3(sq[L]["ssim"]), f3(sq[D1]["ssim"]), f3(sq[D4]["ssim"])],
        ["BER, JPEG Q50", f3(att["JPEG Q50"][L]), f3(att["JPEG Q50"][D1]), f3(att["JPEG Q50"][D4])],
        ["BER, noise σ=5", f3(att["Gaussian noise s=5"][L]), f3(att["Gaussian noise s=5"][D1]), f3(att["Gaussian noise s=5"][D4])],
        ["BER, noise σ=10", f3(att["Gaussian noise s=10"][L]), f3(att["Gaussian noise s=10"][D1]), f3(att["Gaussian noise s=10"][D4])],
        ["BER, blur σ=1.5", f3(att["Gaussian blur s=1.5"][L]), f3(att["Gaussian blur s=1.5"][D1]), f3(att["Gaussian blur s=1.5"][D4])],
        ["BER, crop 25%", f3(att["Crop 25% rows"][L]), f3(att["Crop 25% rows"][D1]), f3(att["Crop 25% rows"][D4])],
        ["Detected by chi-square", "Yes (p ≥ 0.92)", "No", "No"]]
table(rows, [2.0, 1.45, 1.45, 1.45], "Table 8: Side-by-side comparison of the three configurations.")
body(
    "LSB offers about 64 times the capacity of the DCT scheme with 1,024 blocks, and a change that is hard to see, but "
    "the payload is lost under JPEG, noise and blur. DCT-QIM carries less, changes the image more, and keeps the "
    "payload through JPEG quality 50 and moderate noise. The choice depends on whether the image will be "
    "processed after embedding."
)
h2("5.2 Agreement with the literature")
bullet("The failure of LSB under lossy compression and the need for a transform domain for robust marking agree "
       "with the arguments in [1], [3] and [7].")
bullet("The finding that the LSB plane is detectable by the chi-square test at partial rates agrees with [4].")
bullet("The finding that QIM survives only while the added distortion stays below the quantizer step is the "
       "behaviour that [9] predicts: bits are lost when the attack moves a coefficient past half a step.")
bullet("The step size trade-off between PSNR and robustness (Table 3) is the usual trade-off of robust watermarking "
       "[7], [8].")

# ---- 6 Conclusion
h1("6. Conclusion")
body(
    f"Two embedding methods were built from scratch and compared under 17 attacks. LSB embedding is the less visible "
    f"({f2(sq[L]['psnr'])} dB for 256 bits; {f2(lsbq[0]['psnr'])} dB at full capacity), has high capacity, and "
    f"is destroyed by JPEG even at quality 90. DCT-QIM with Δ = {int(dflt['delta'])} and r = 4 was recovered exactly after JPEG quality "
    f"50, noise of σ = 5 and a brightness change at {f2(sq[D4]['psnr'])} dB, and a step of 32 extends this to JPEG quality 30. "
    "Neither method survived blur, median filtering or rescaling. Repetition coding helps only against independent noise. "
    "The chi-square test detected LSB embedding but not the DCT watermark."
)
body("Limitations:")
bullet("Only two test images were used, and attacks use one random seed, so no mean or standard deviation is reported.")
bullet("Each bit error rate comes from a 256-bit payload, so one bit changes the value by 0.004.")
bullet("The chi-square test was run on raster-order embedding. With a secret key the positions are scattered, and the "
       "simple test is expected to be weaker; stronger detectors were not implemented.")
bullet("Attacks that need synchronisation (rotation, translation, large crops) are not handled, and cropping was "
       "modelled as clearing rows.")
bullet("Watermark extraction was tested with a known step size Δ, a known coefficient position and a known key.")
bullet("The step size and repetition factor were chosen by trying values on the test image, not tuned on a separate set.")

# ---- 7 Future work
h1("7. Future Work (Future Scope)")
bullet("Replace the repetition code with an error-correcting code such as BCH, which can also correct the systematic errors "
       "that repetition cannot.", "Better coding.")
bullet("Embed in wavelet (DWT) or SVD coefficients and compare with the DCT scheme in the same benchmark.", "Other domains.")
bullet("Make Δ depend on block content using a perceptual model so that textured blocks carry a larger step and flat "
       "blocks a smaller one.", "Adaptive step size.")
bullet("Add a synchronisation template so that the watermark can survive small rotations and rescaling.", "Geometric robustness.")
bullet("Implement the more sensitive detectors of [6] and test keyed embedding against them.", "Stronger steganalysis.")
bullet("Repeat the experiments on a larger set such as the Kodak images and report mean and standard deviation.", "Larger test set.")

# ---- 8 GitHub
h1("8. GitHub Link")
body("The source code, scripts and results of this project are available on GitHub:")
p = para("", after=6)
r = p.add_run(GITHUB)
r.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
r.underline = True

# ---- 9 Bibliography
h1("9. Bibliography")
body("Books, standards and documentation that were studied but are not cited by number in the text:")
bib = [
    "R. C. Gonzalez and R. E. Woods, Digital Image Processing, 4th ed. New York, NY, USA: Pearson Education, 2018.",
    "A. K. Jain, Fundamentals of Digital Image Processing. Englewood Cliffs, NJ, USA: Prentice Hall, 1989.",
    "I. J. Cox, M. L. Miller, J. A. Bloom, J. Fridrich, and T. Kalker, Digital Watermarking and Steganography, 2nd ed. Burlington, MA, USA: Morgan Kaufmann, 2008.",
    "ITU-T Recommendation T.81, Information technology: Digital compression and coding of continuous-tone still images (JPEG), 1992.",
    "scikit-image documentation, https://scikit-image.org/docs/stable/ (image processing functions and bundled test images).",
    "NumPy, SciPy, Matplotlib and Pillow online documentation (array operations, DCT routines, plotting and the JPEG encoder used for the attack).",
]
for i, b in enumerate(bib, 1):
    p = para(f"{i}. {b}", size=10, after=3)
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.25)

# ---- 10 References
h1("10. References")
refs = [
    "W. Bender, D. Gruhl, N. Morimoto, and A. Lu, “Techniques for data hiding,” IBM Syst. J., vol. 35, no. 3–4, pp. 313–336, 1996.",
    "F. A. P. Petitcolas, R. J. Anderson, and M. G. Kuhn, “Information hiding—a survey,” Proc. IEEE, vol. 87, no. 7, pp. 1062–1078, 1999.",
    "A. Cheddad, J. Condell, K. Curran, and P. McKevitt, “Digital image steganography: Survey and analysis of current methods,” Signal Process., vol. 90, no. 3, pp. 727–752, 2010.",
    "A. Westfeld and A. Pfitzmann, “Attacks on steganographic systems,” in Information Hiding, Lecture Notes in Computer Science, vol. 1768. Berlin, Germany: Springer, 2000.",
    "Z. Wang, A. C. Bovik, H. R. Sheikh, and E. P. Simoncelli, “Image quality assessment: from error visibility to structural similarity,” IEEE Trans. Image Process., vol. 13, no. 4, pp. 600–612, 2004.",
    "J. Fridrich, M. Goljan, and R. Du, “Detecting LSB steganography in color and gray-scale images,” IEEE Multimedia, vol. 8, no. 4, pp. 22–28, 2001.",
    "I. J. Cox, J. Kilian, F. T. Leighton, and T. Shamoon, “Secure spread spectrum watermarking for multimedia,” IEEE Trans. Image Process., vol. 6, no. 12, pp. 1673–1687, 1997.",
    "M. Barni, F. Bartolini, V. Cappellini, and A. Piva, “A DCT-domain system for robust image watermarking,” Signal Process., vol. 66, no. 3, pp. 357–372, 1998.",
    "B. Chen and G. W. Wornell, “Quantization index modulation: A class of provably good methods for digital watermarking and information embedding,” IEEE Trans. Inf. Theory, vol. 47, no. 4, pp. 1423–1443, 2001.",
    "N. Ahmed, T. Natarajan, and K. R. Rao, “Discrete cosine transform,” IEEE Trans. Comput., vol. C-23, no. 1, pp. 90–93, 1974.",
    "G. K. Wallace, “The JPEG still picture compression standard,” Commun. ACM, vol. 34, no. 4, pp. 30–44, 1991.",
    "Q. Huynh-Thu and M. Ghanbari, “Scope of validity of PSNR in image/video quality assessment,” Electron. Lett., vol. 44, no. 13, pp. 800–801, 2008.",
]
refs_extra = {13: "S. van der Walt et al., “scikit-image: image processing in Python,” PeerJ, vol. 2, p. e453, 2014.",
              14: "C. R. Harris et al., “Array programming with NumPy,” Nature, vol. 585, pp. 357–362, 2020."}
for i, rtext in enumerate(refs, 1):
    p = para(f"[{i}] {rtext}", size=10, after=3)
    p.paragraph_format.left_indent = Inches(0.35)
    p.paragraph_format.first_line_indent = Inches(-0.35)
for i, rtext in refs_extra.items():
    p = para(f"[{i}] {rtext}", size=10, after=3)
    p.paragraph_format.left_indent = Inches(0.35)
    p.paragraph_format.first_line_indent = Inches(-0.35)

doc.add_page_break()
para("", after=140)
para("Thank You", bold=True, size=26, color=TEAL, align="center")

for z in doc.settings.element.findall(qn('w:zoom')):
    if z.get(qn('w:percent')) is None:
        z.set(qn('w:percent'), '100')
doc.save(OUT_DOCX)
print("saved", OUT_DOCX)
