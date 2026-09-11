# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Generate small, deterministic synthetic OOXML documents for the corpus.

The office cannot write OOXML, so the exercise-one-feature-each files
the roadmap asks for are written here by hand as minimal packages:

  synthetic-text.docx    three paragraphs (bold/italic runs), a 2x2 table, a footnote
  synthetic-book.xlsx    two sheets, shared strings, numbers, SUM formulas
  synthetic-deck.pptx    two slides with a title and bullet text each

Usage: python make_synthetic.py <corpus_dir>
Regenerate and commit the outputs when this script changes; the zip
entries carry a fixed timestamp so the files are reproducible.
"""

import os
import sys
import zipfile

FIXED = (2026, 1, 1, 0, 0, 0)
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
ODOC = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def write(path, parts):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts:
            info = zipfile.ZipInfo(name, FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)


def content_types(overrides):
    items = ['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
             '<Default Extension="xml" ContentType="application/xml"/>']
    items += ['<Override PartName="%s" ContentType="%s"/>' % o for o in overrides]
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="%s">%s</Types>' % (CT, "".join(items))


def rels(entries):
    items = ['<Relationship Id="%s" Type="%s" Target="%s"/>' % e for e in entries]
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="%s">%s</Relationships>' % (REL, "".join(items))


# ---------------------------------------------------------------- docx

def docx(path):
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    def p(*runs):
        return "<w:p>%s</w:p>" % "".join(runs)
    def r(text, bold=False, italic=False):
        pr = "".join(x for x, on in (("<w:b/>", bold), ("<w:i/>", italic)) if on)
        return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % ("<w:rPr>%s</w:rPr>" % pr if pr else "", text)
    def cell(text):
        return "<w:tc><w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>%s</w:tc>" % p(r(text))
    body = "".join([
        p(r("Work synthetic text document")),
        p(r("A paragraph with "), r("bold", bold=True), r(" and "), r("italic", italic=True), r(" runs.")),
        p(r("A footnote follows this sentence."),
          '<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteReference w:id="1"/></w:r>'),
        "<w:tbl><w:tblPr><w:tblW w:w=\"4800\" w:type=\"dxa\"/></w:tblPr><w:tblGrid><w:gridCol w:w=\"2400\"/><w:gridCol w:w=\"2400\"/></w:tblGrid>"
        "<w:tr>%s%s</w:tr><w:tr>%s%s</w:tr></w:tbl>" % (cell("Item"), cell("Jan"), cell("Wholesale"), cell("18400")),
        p(r("Closing paragraph after the table.")),
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>',
    ])
    document = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="%s"><w:body>%s</w:body></w:document>' % (W, body)
    footnotes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes xmlns:w="%s">'
                 '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
                 '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
                 '<w:footnote w:id="1"><w:p><w:r><w:footnoteRef/></w:r><w:r><w:t xml:space="preserve"> This is the footnote text.</w:t></w:r></w:p></w:footnote>'
                 '</w:footnotes>') % W
    write(path, [
        ("[Content_Types].xml", content_types([
            ("/word/document.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"),
            ("/word/footnotes.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml")])),
        ("_rels/.rels", rels([("rId1", ODOC + "/officeDocument", "word/document.xml")])),
        ("word/document.xml", document),
        ("word/_rels/document.xml.rels", rels([("rId1", ODOC + "/footnotes", "footnotes.xml")])),
        ("word/footnotes.xml", footnotes),
    ])


# ---------------------------------------------------------------- xlsx

def xlsx(path):
    S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    R = ODOC
    shared = ["Item", "Jan", "Feb", "Wholesale", "Market stall", "Total", "Second sheet note"]
    def s(ref, i):
        return '<c r="%s" t="s"><v>%d</v></c>' % (ref, i)
    def n(ref, v):
        return '<c r="%s"><v>%s</v></c>' % (ref, v)
    def f(ref, formula, v):
        return '<c r="%s"><f>%s</f><v>%s</v></c>' % (ref, formula, v)
    sheet1 = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="%s" xmlns:r="%s"><sheetData>'
              '<row r="1">%s%s%s</row><row r="2">%s%s%s</row><row r="3">%s%s%s</row><row r="4">%s%s%s</row>'
              '</sheetData></worksheet>') % (S, R,
              s("A1", 0), s("B1", 1), s("C1", 2),
              s("A2", 3), n("B2", 18400), n("C2", 19250),
              s("A3", 4), n("B3", 6120), n("C3", 5880),
              s("A4", 5), f("B4", "SUM(B2:B3)", 24520), f("C4", "SUM(C2:C3)", 25130))
    sheet2 = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="%s" xmlns:r="%s"><sheetData>'
              '<row r="1">%s</row></sheetData></worksheet>') % (S, R, s("A1", 6))
    sst = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><sst xmlns="%s" count="%d" uniqueCount="%d">%s</sst>'
           % (S, len(shared), len(shared), "".join("<si><t>%s</t></si>" % x for x in shared)))
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="%s" xmlns:r="%s"><sheets>'
                '<sheet name="Cash flow" sheetId="1" r:id="rId1"/><sheet name="Notes" sheetId="2" r:id="rId2"/></sheets></workbook>') % (S, R)
    write(path, [
        ("[Content_Types].xml", content_types([
            ("/xl/workbook.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"),
            ("/xl/worksheets/sheet1.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"),
            ("/xl/worksheets/sheet2.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"),
            ("/xl/sharedStrings.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml")])),
        ("_rels/.rels", rels([("rId1", ODOC + "/officeDocument", "xl/workbook.xml")])),
        ("xl/workbook.xml", workbook),
        ("xl/_rels/workbook.xml.rels", rels([
            ("rId1", ODOC + "/worksheet", "worksheets/sheet1.xml"),
            ("rId2", ODOC + "/worksheet", "worksheets/sheet2.xml"),
            ("rId3", ODOC + "/sharedStrings", "sharedStrings.xml")])),
        ("xl/worksheets/sheet1.xml", sheet1),
        ("xl/worksheets/sheet2.xml", sheet2),
        ("xl/sharedStrings.xml", sst),
    ])


# ---------------------------------------------------------------- pptx

def pptx(path):
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    P = "http://schemas.openxmlformats.org/presentationml/2006/main"
    R = ODOC
    XMLNS = 'xmlns:a="%s" xmlns:r="%s" xmlns:p="%s"' % (A, R, P)
    head = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    grp = ('<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
           '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>')
    def sp(sid, name, x, y, cx, cy, paras, size):
        body = "".join('<a:p><a:r><a:rPr lang="en-US" sz="%d"/><a:t>%s</a:t></a:r></a:p>' % (size, t) for t in paras)
        return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
                '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
                '<p:txBody><a:bodyPr/><a:lstStyle/>%s</p:txBody></p:sp>') % (sid, name, x, y, cx, cy, body)
    def slide(title, bullets):
        return (head + '<p:sld %s><p:cSld><p:spTree>%s%s%s</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
                % (XMLNS, grp,
                   sp(2, "Title", 457200, 274638, 8229600, 1143000, [title], 4000),
                   sp(3, "Body", 457200, 1600200, 8229600, 4525963, bullets, 2400)))
    slides = [slide("Work synthetic deck", ["First point", "Second point", "Third point"]),
              slide("Second slide", ["Only one point here"])]
    clrmap = ('<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
              'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>')
    master = (head + '<p:sldMaster %s><p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg>'
              '<p:spTree>%s</p:spTree></p:cSld>%s<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>'
              % (XMLNS, grp, clrmap))
    layout = (head + '<p:sldLayout %s type="blank"><p:cSld name="Blank"><p:spTree>%s</p:spTree></p:cSld>'
              '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>' % (XMLNS, grp))
    def scheme(name, val):
        return '<a:%s><a:srgbClr val="%s"/></a:%s>' % (name, val, name)
    colors = "".join(scheme(n, v) for n, v in [("dk1", "000000"), ("lt1", "FFFFFF"), ("dk2", "1F497D"), ("lt2", "EEECE1"),
                                                ("accent1", "C67139"), ("accent2", "7A8A5E"), ("accent3", "9BBB59"),
                                                ("accent4", "8064A2"), ("accent5", "4BACC6"), ("accent6", "F79646"),
                                                ("hlink", "0000FF"), ("folHlink", "800080")])
    fill = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    ln = '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    eff = '<a:effectStyle><a:effectLst/></a:effectStyle>'
    theme = (head + '<a:theme xmlns:a="%s" name="Work"><a:themeElements><a:clrScheme name="Work">%s</a:clrScheme>'
             '<a:fontScheme name="Work"><a:majorFont><a:latin typeface="Liberation Sans"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
             '<a:minorFont><a:latin typeface="Liberation Sans"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
             '<a:fmtScheme name="Work"><a:fillStyleLst>%s%s%s</a:fillStyleLst><a:lnStyleLst>%s%s%s</a:lnStyleLst>'
             '<a:effectStyleLst>%s%s%s</a:effectStyleLst><a:bgFillStyleLst>%s%s%s</a:bgFillStyleLst></a:fmtScheme>'
             '</a:themeElements></a:theme>') % (A, colors, fill, fill, fill, ln, ln, ln, eff, eff, eff, fill, fill, fill)
    presentation = (head + '<p:presentation %s><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
                    '<p:sldIdLst><p:sldId id="256" r:id="rId2"/><p:sldId id="257" r:id="rId3"/></p:sldIdLst>'
                    '<p:sldSz cx="9144000" cy="6858000" type="screen4x3"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>' % XMLNS)
    T = "application/vnd.openxmlformats-officedocument."
    write(path, [
        ("[Content_Types].xml", content_types([
            ("/ppt/presentation.xml", T + "presentationml.presentation.main+xml"),
            ("/ppt/slideMasters/slideMaster1.xml", T + "presentationml.slideMaster+xml"),
            ("/ppt/slideLayouts/slideLayout1.xml", T + "presentationml.slideLayout+xml"),
            ("/ppt/slides/slide1.xml", T + "presentationml.slide+xml"),
            ("/ppt/slides/slide2.xml", T + "presentationml.slide+xml"),
            ("/ppt/theme/theme1.xml", T + "theme+xml")])),
        ("_rels/.rels", rels([("rId1", ODOC + "/officeDocument", "ppt/presentation.xml")])),
        ("ppt/presentation.xml", presentation),
        ("ppt/_rels/presentation.xml.rels", rels([
            ("rId1", ODOC + "/slideMaster", "slideMasters/slideMaster1.xml"),
            ("rId2", ODOC + "/slide", "slides/slide1.xml"),
            ("rId3", ODOC + "/slide", "slides/slide2.xml"),
            ("rId4", ODOC + "/theme", "theme/theme1.xml")])),
        ("ppt/slideMasters/slideMaster1.xml", master),
        ("ppt/slideMasters/_rels/slideMaster1.xml.rels", rels([
            ("rId1", ODOC + "/slideLayout", "../slideLayouts/slideLayout1.xml"),
            ("rId2", ODOC + "/theme", "../theme/theme1.xml")])),
        ("ppt/slideLayouts/slideLayout1.xml", layout),
        ("ppt/slideLayouts/_rels/slideLayout1.xml.rels", rels([("rId1", ODOC + "/slideMaster", "../slideMasters/slideMaster1.xml")])),
        ("ppt/slides/slide1.xml", slides[0]),
        ("ppt/slides/_rels/slide1.xml.rels", rels([("rId1", ODOC + "/slideLayout", "../slideLayouts/slideLayout1.xml")])),
        ("ppt/slides/slide2.xml", slides[1]),
        ("ppt/slides/_rels/slide2.xml.rels", rels([("rId1", ODOC + "/slideLayout", "../slideLayouts/slideLayout1.xml")])),
        ("ppt/theme/theme1.xml", theme),
    ])


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    out = argv[1]
    os.makedirs(out, exist_ok=True)
    docx(os.path.join(out, "synthetic-text.docx"))
    xlsx(os.path.join(out, "synthetic-book.xlsx"))
    pptx(os.path.join(out, "synthetic-deck.pptx"))
    print("wrote synthetic-text.docx, synthetic-book.xlsx, synthetic-deck.pptx to", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
