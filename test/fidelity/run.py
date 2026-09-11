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

"""OOXML import-fidelity harness (roadmap section 4), skeleton.

For every .docx / .xlsx / .pptx in a corpus directory:

1. Read ground truth straight from the OOXML package with zipfile and
   ElementTree: paragraph, table, image and footnote counts and the text
   for Word; sheet, cell and formula counts and the strings for Excel;
   slide and shape counts and the text for PowerPoint.
2. Load the document in the office over a UNO pipe and read the same
   facts from the document model.
3. Export to PDF and record the page count and extracted text when
   poppler-utils are installed.
4. Store as ODF, reload, and check the model facts survive (ODF
   round-trip stability).

Each feature scores 0..1; a document's score is the mean of its
features; the run's score is the mean over documents. The harness only
fails on its own errors (no office, no corpus); low fidelity is
reported, never fatal. The office has no OOXML *export* filters, so a
save-as-OOXML round trip cannot be measured until an exporter exists.

Usage: python run.py <office_dir> <corpus_dir> <out_dir>
Run with PYTHONPATH/URE_BOOTSTRAP/LD_LIBRARY_PATH set so `import uno`
works (see .github/scripts/linux-full-build.sh, office_pyenv).
"""

import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
import xml.etree.ElementTree as ET

try:  # pyuno is only needed to drive the office; ground truth works without it
    import uno
    from com.sun.star.beans import PropertyValue
    from com.sun.star.connection import NoConnectException
except ImportError:  # pragma: no cover
    uno = PropertyValue = NoConnectException = None

CONNECT_TIMEOUT_S = 240
TERMINATE_TIMEOUT_S = 60

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}

KINDS = {
    ".docx": ("writer", "writer8", "writer_pdf_Export", ".odt"),
    ".xlsx": ("calc", "calc8", "calc_pdf_Export", ".ods"),
    ".pptx": ("impress", "impress8", "impress_pdf_Export", ".odp"),
}

# com.sun.star.sheet.CellFlags
CF_VALUE, CF_DATETIME, CF_STRING, CF_FORMULA = 1, 2, 4, 16


# ----------------------------------------------------------------------
# helpers

def props(**kwargs):
    out = []
    for name, value in kwargs.items():
        p = PropertyValue()
        p.Name = name
        p.Value = value
        out.append(p)
    return tuple(out)


def file_url(path):
    return uno.systemPathToFileUrl(os.path.abspath(path))


def norm_text(s):
    return re.sub(r"\s+", " ", s or "").strip()


def text_similarity(a, b):
    a, b = norm_text(a), norm_text(b)
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def bag_similarity(a, b):
    """Order-free text comparison for spreadsheets: cell strings have no
    reading order, and the package and the model enumerate cells differently."""
    la = sorted(norm_text(x) for x in (a or "").split("\n") if norm_text(x))
    lb = sorted(norm_text(x) for x in (b or "").split("\n") if norm_text(x))
    if not la and not lb:
        return 1.0
    return difflib.SequenceMatcher(None, la, lb, autojunk=False).ratio()


def count_score(expected, got):
    if expected is None or got is None:
        return None
    if expected == got:
        return 1.0
    return max(0.0, 1.0 - abs(expected - got) / float(max(expected, 1)))


def have(tool):
    return shutil.which(tool) is not None


# ----------------------------------------------------------------------
# ground truth from the OOXML package

def _xml(z, name):
    try:
        return ET.fromstring(z.read(name))
    except KeyError:
        return None


def _paras_text(root):
    return "\n".join("".join(t.text or "" for t in p.iter("{%s}t" % NS["w"]))
                     for p in root.iter("{%s}p" % NS["w"]))


def truth_docx(z):
    doc = _xml(z, "word/document.xml")
    body = doc.find("w:body", NS)
    paras = [c for c in body if c.tag == "{%s}p" % NS["w"]]
    tables = [c for c in body if c.tag == "{%s}tbl" % NS["w"]]
    # All paragraphs in document order, table cells included: that is what
    # the loaded document's getText().getString() returns.
    text = _paras_text(body)
    images = [n for n in z.namelist() if n.startswith("word/media/")]
    footnotes = 0
    chrome = []
    for name in sorted(z.namelist()):
        base = name.rsplit("/", 1)[-1]
        if name.startswith("word/") and re.match(r"(header|footer)\d*\.xml$", base):
            chrome.append(_paras_text(_xml(z, name)))
    fn = _xml(z, "word/footnotes.xml")
    if fn is not None:
        real = [f for f in fn.findall("w:footnote", NS)
                if f.get("{%s}type" % NS["w"]) not in ("separator", "continuationSeparator")]
        footnotes = len(real)
        chrome += [_paras_text(f) for f in real]
    return {"paragraphs": len(paras), "tables": len(tables), "images": len(images),
            "footnotes": footnotes, "text": text,
            # headers, footers and footnote bodies: rendered into the PDF,
            # not part of the body text; used only for the PDF comparison
            "chrome_text": "\n".join(c for c in chrome if c)}


def truth_xlsx(z):
    sheets = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    shared = []
    ss = _xml(z, "xl/sharedStrings.xml")
    if ss is not None:
        for si in ss.findall("s:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["s"])))
    cells = formulas = 0
    strings = []
    for name in sheets:
        sh = _xml(z, name)
        for c in sh.iter("{%s}c" % NS["s"]):
            v = c.find("s:v", NS)
            f = c.find("s:f", NS)
            is_ = c.find("s:is", NS)
            if v is None and f is None and is_ is None:
                continue
            cells += 1
            if f is not None:
                formulas += 1
            if c.get("t") == "s" and v is not None:
                try:
                    strings.append(shared[int(v.text)])
                except (ValueError, IndexError):
                    pass
            elif is_ is not None:
                strings.append("".join(t.text or "" for t in is_.iter("{%s}t" % NS["s"])))
    return {"sheets": len(sheets), "cells": cells, "formulas": formulas,
            "text": "\n".join(strings)}


def truth_pptx(z):
    slides = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                    key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)))
    shapes = 0
    texts = []
    for name in slides:
        sl = _xml(z, name)
        shapes += sum(1 for _ in sl.iter("{%s}sp" % NS["p"]))
        for para in sl.iter("{%s}p" % NS["a"]):
            texts.append("".join(t.text or "" for t in para.iter("{%s}t" % NS["a"])))
    return {"slides": len(slides), "shapes": shapes, "text": "\n".join(texts)}


def ground_truth(path, kind):
    with zipfile.ZipFile(path) as z:
        return {"writer": truth_docx, "calc": truth_xlsx, "impress": truth_pptx}[kind](z)


# ----------------------------------------------------------------------
# facts from the loaded document model

def facts_writer(doc):
    paragraphs = 0
    enum = doc.getText().createEnumeration()
    while enum.hasMoreElements():
        el = enum.nextElement()
        if el.supportsService("com.sun.star.text.Paragraph"):
            paragraphs += 1
    return {"paragraphs": paragraphs,
            "tables": doc.getTextTables().getCount(),
            "images": doc.getGraphicObjects().getCount(),
            "footnotes": doc.getFootnotes().getCount(),
            "text": doc.getText().getString()}


def _count_cells(ranges):
    n = 0
    e = ranges.getCells().createEnumeration()
    while e.hasMoreElements():
        e.nextElement()
        n += 1
    return n


def facts_calc(doc):
    sheets = doc.getSheets()
    cells = formulas = 0
    strings = []
    for i in range(sheets.getCount()):
        sheet = sheets.getByIndex(i)
        cells += _count_cells(sheet.queryContentCells(CF_VALUE | CF_DATETIME | CF_STRING | CF_FORMULA))
        formulas += _count_cells(sheet.queryContentCells(CF_FORMULA))
        e = sheet.queryContentCells(CF_STRING).getCells().createEnumeration()
        while e.hasMoreElements():
            strings.append(e.nextElement().getString())
    return {"sheets": sheets.getCount(), "cells": cells, "formulas": formulas,
            "text": "\n".join(strings)}


def facts_impress(doc):
    pages = doc.getDrawPages()
    shapes = 0
    texts = []
    for i in range(pages.getCount()):
        page = pages.getByIndex(i)
        shapes += page.getCount()
        for j in range(page.getCount()):
            shape = page.getByIndex(j)
            try:
                s = shape.getString()
            except Exception:
                s = ""
            if s:
                texts.append(s)
    return {"slides": pages.getCount(), "shapes": shapes, "text": "\n".join(texts)}


FACTS = {"writer": facts_writer, "calc": facts_calc, "impress": facts_impress}


# ----------------------------------------------------------------------
# office control

def start_office(office_dir, pipe_name):
    soffice = os.path.join(office_dir, "program", "soffice")
    cmd = [soffice, "-headless", "-invisible", "-nologo", "-norestore", "-nofirststartwizard",
           "-accept=pipe,name=%s;urp;StarOffice.ComponentContext" % pipe_name]
    print("start:", " ".join(cmd), flush=True)
    return subprocess.Popen(cmd)


def connect(pipe_name, proc):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    url = "uno:pipe,name=%s;urp;StarOffice.ComponentContext" % pipe_name
    deadline = time.time() + CONNECT_TIMEOUT_S
    while True:
        if proc.poll() is not None:
            raise RuntimeError("soffice exited early with code %s" % proc.returncode)
        try:
            return resolver.resolve(url)
        except NoConnectException:
            if time.time() > deadline:
                raise RuntimeError("could not connect to soffice within %ss" % CONNECT_TIMEOUT_S)
            time.sleep(1)


def load(desktop, path, **extra):
    return desktop.loadComponentFromURL(file_url(path), "_blank", 0, props(Hidden=True, **extra))


# ----------------------------------------------------------------------
# PDF facts

def pdf_facts(pdf):
    out = {}
    if have("pdfinfo"):
        r = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True)
        m = re.search(r"^Pages:\s+(\d+)", r.stdout, re.M)
        if m:
            out["pages"] = int(m.group(1))
    if have("pdftotext"):
        r = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True)
        out["text"] = r.stdout
    return out


# ----------------------------------------------------------------------
# one document

def run_document(desktop, path, out_dir, corpus_dir=None):
    # report name relative to the corpus so subdirectories stay visible
    name = os.path.relpath(path, corpus_dir) if corpus_dir else os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    kind, odf_filter, pdf_filter, odf_ext = KINDS[ext]
    rec = {"file": name, "kind": kind, "features": {}, "notes": []}
    t0 = time.time()

    truth = ground_truth(path, kind)
    chrome_text = truth.pop("chrome_text", "")
    rec["truth"] = {k: v for k, v in truth.items() if k != "text"}

    doc = None
    try:
        doc = load(desktop, path)
    except Exception as e:  # loadComponentFromURL raises on hard failures
        rec["notes"].append("load raised %s" % type(e).__name__)
    if doc is None:
        rec["features"]["load"] = 0.0
        rec["score"] = 0.0
        rec["seconds"] = round(time.time() - t0, 1)
        return rec
    rec["features"]["load"] = 1.0

    try:
        got = FACTS[kind](doc)
        rec["model"] = {k: v for k, v in got.items() if k != "text"}
        similarity = bag_similarity if kind == "calc" else text_similarity
        for key, expected in truth.items():
            if key == "text":
                rec["features"]["text"] = round(similarity(expected, got.get("text", "")), 3)
            else:
                rec["features"][key] = round(count_score(expected, got.get(key)), 3)

        # PDF export
        os.makedirs(os.path.dirname(os.path.join(out_dir, name)) or out_dir, exist_ok=True)
        pdf = os.path.join(out_dir, name + ".pdf")
        doc.storeToURL(file_url(pdf), props(FilterName=pdf_filter, Overwrite=True))
        pf = pdf_facts(pdf)
        rec["pdf"] = {"bytes": os.path.getsize(pdf), "pages": pf.get("pages")}
        if "text" in pf and truth.get("text"):
            expected_pdf = truth["text"] + ("\n" + chrome_text if chrome_text else "")
            if kind == "calc":
                # the PDF also prints every number; check that the strings appear
                pdf_norm = norm_text(pf["text"])
                strings = [norm_text(x) for x in truth["text"].split("\n") if norm_text(x)]
                found = sum(1 for x in strings if x in pdf_norm)
                rec["features"]["pdf_text"] = round(found / len(strings), 3) if strings else 1.0
            else:
                rec["features"]["pdf_text"] = round(text_similarity(expected_pdf, pf["text"]), 3)

        # ODF round trip: store, close, reload, compare model facts
        odf = os.path.join(out_dir, name + odf_ext)
        doc.storeToURL(file_url(odf), props(FilterName=odf_filter, Overwrite=True))
        doc.close(True)
        doc = None
        doc2 = load(desktop, odf)
        got2 = FACTS[kind](doc2)
        doc2.close(True)
        stable = [1.0 if got[k] == got2.get(k) else 0.0 for k in got if k != "text"]
        stable.append(similarity(got["text"], got2.get("text", "")))
        rec["features"]["odf_roundtrip"] = round(sum(stable) / len(stable), 3)
    except Exception as e:
        rec["notes"].append("%s: %s" % (type(e).__name__, str(e)[:200]))
    finally:
        if doc is not None:
            try:
                doc.close(True)
            except Exception:
                pass

    scores = [v for v in rec["features"].values() if v is not None]
    rec["score"] = round(sum(scores) / len(scores), 3) if scores else 0.0
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


# ----------------------------------------------------------------------
# report

COLUMNS = ["load", "text", "pdf_text", "paragraphs", "tables", "images", "footnotes",
           "sheets", "cells", "formulas", "slides", "shapes", "odf_roundtrip"]


def write_report(out_dir, run):
    with open(os.path.join(out_dir, "report.json"), "w") as f:
        json.dump(run, f, indent=2, sort_keys=True)
    lines = ["# OOXML import fidelity", "",
             "Run: %s, %d documents, score **%.3f**" % (run["date"], len(run["documents"]), run["score"]), "",
             "| file | kind | score | " + " | ".join(COLUMNS) + " | pdf pages | s |",
             "|" + "---|" * (len(COLUMNS) + 5)]
    for d in run["documents"]:
        cells = []
        for c in COLUMNS:
            v = d["features"].get(c)
            cells.append("" if v is None else ("%.2f" % v))
        pages = (d.get("pdf") or {}).get("pages")
        lines.append("| %s | %s | %.2f | %s | %s | %s |" % (
            d["file"], d["kind"], d["score"], " | ".join(cells),
            "" if pages is None else pages, d.get("seconds", "")))
    notes = [(d["file"], n) for d in run["documents"] for n in d["notes"]]
    if notes:
        lines += ["", "Notes:", ""] + ["- %s: %s" % n for n in notes]
    md = "\n".join(lines) + "\n"
    with open(os.path.join(out_dir, "report.md"), "w") as f:
        f.write(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(md)
    print(md, flush=True)


def main(argv):
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    office_dir, corpus_dir, out_dir = argv[1:]
    if uno is None:
        print("pyuno is not importable; set PYTHONPATH/URE_BOOTSTRAP to the office", file=sys.stderr)
        return 2
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(os.path.join(root, f)
                   for root, _dirs, names in os.walk(corpus_dir)
                   for f in names if os.path.splitext(f)[1].lower() in KINDS)
    if not files:
        print("no .docx/.xlsx/.pptx in %s" % corpus_dir, file=sys.stderr)
        return 2

    pipe_name = "work-fidelity-%d" % os.getpid()
    proc = start_office(office_dir, pipe_name)
    rc = 1
    docs = []
    try:
        ctx = connect(pipe_name, proc)
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        for path in files:
            print("--", os.path.basename(path), flush=True)
            docs.append(run_document(desktop, path, out_dir, corpus_dir))
        try:
            desktop.terminate()
        except Exception:
            pass
        rc = 0
    finally:
        deadline = time.time() + TERMINATE_TIMEOUT_S
        while proc.poll() is None and time.time() < deadline:
            time.sleep(1)
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    run = {"date": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
           "office": office_dir, "documents": docs,
           "score": round(sum(d["score"] for d in docs) / len(docs), 3) if docs else 0.0}
    write_report(out_dir, run)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
