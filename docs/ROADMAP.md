<!--
 Licensed to the Apache Software Foundation (ASF) under one
 or more contributor license agreements.  See the NOTICE file
 distributed with this work for additional information
 regarding copyright ownership.  The ASF licenses this file
 to you under the Apache License, Version 2.0 (the
 "License"); you may not use this file except in compliance
 with the License.  You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing,
 software distributed under the License is distributed on an
 "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 KIND, either express or implied.  See the License for the
 specific language governing permissions and limitations
 under the License.
-->

# Work — Roadmap

**Status:** draft, September 2026
**Scope:** the product direction for this fork. Build and hardening conventions stay in `CLAUDE.md`
and `SECURITY.md`.

## 1. Identity

This repository is becoming **Work**: a private-by-default office suite for small organisations and
charities, built on the hardened Apache OpenOffice trunk in this fork.

| Upstream | Work |
| --- | --- |
| OpenOffice (suite) | **Work** |
| Writer | **Write** |
| Calc | **Accounts** |
| Impress | **Show** |
| Base | **Keep** |

The renames are product names. Module directories (`main/sw`, `main/sc`, `main/sd`, `main/dbaccess`)
keep their upstream names so patches remain portable and `git blame` stays useful. Branding lives in
`main/instsetoo_native`, `main/scp2`, `main/officecfg`, `main/default_images`, and the `.ulf`
string files; `docs/design/WORK-UI.md` covers the visual identity and maps it onto the tree.

### Principles

1. **Private by default.** Nothing leaves the machine unless the user explicitly sends it. That
   includes assistive features: language models run on device.
2. **Local-first, self-hostable.** Anything that needs a server must run on a NAS or a cheap VPS
   the organisation controls.
3. **Hardened.** The importer bounds work continues; every new parser (data connectors, PDF forms,
   sync protocol) gets the same treatment from day one.
4. **Small-org shaped.** A treasurer, a fundraiser, and a volunteer coordinator are the users, not
   an enterprise IT department. Templates carry real domain logic, not placeholder text.

## 2. Sequencing

The ideas are grouped by how much of the core they touch, because that decides cost and risk.
Extension-layer work ships in months; core work in the Accounts engine takes quarters; the
document-model rewrites (co-editing, Keep) take years and are last.

```
Phase 0  Verifiable build          full office build in CI, nightly installers
Phase 1  Extension layer           private assistant, checkers, connectors, template packs
Phase 2  Accounts engine           LAMBDA, audit tooling, Python formulas, live refresh
Phase 3  Documents and PDF         forms, signing, redaction; OOXML fidelity programme
Phase 4  Keep and co-editing       new data app; CRDT sync
```

OOXML round-trip fidelity is the single biggest adoption blocker and is also the longest item.
It is therefore run as a **continuous, measured programme** starting in Phase 0 (the harness) and
never "finishes"; see §4.

## 3. Phase 0 — Verifiable build

Every hardening commit in the log ends with "Not verified by a full office build" because no CI job
and no developer machine builds the office. Nothing below can be developed or shipped until that
changes. This phase is small and unblocks everything.

- **Full Linux build in CI.** Extend `.github/scripts/linux-*.sh` into a job that runs
  `build --all` from `main/instsetoo_native` with `--with-package-format=installed` and archives
  the result. Expect multi-hour runtimes; use ccache and the existing tarball cache.
- **Nightly installers** (`.deb`, `.rpm`, archive) published as workflow artifacts so features can
  be tried without a local build.
- **Smoke run.** Start the installed office headless, load and re-save one document per
  application, exit cleanly. This catches the crash class that the bounds work protects against.
- **Fidelity harness skeleton** (see §4) so measurement starts before any filter work.
- **Windows and macOS** builds follow, using `win10-msvc/README.md` as the starting point.

Exit criterion: a green nightly that produces an installable Work, and a `test/` BVT run against it.

## 4. OOXML fidelity programme (continuous)

Goal: `.docx`, `.xlsx`, `.pptx` open and re-save without visible or structural loss.

Where the code is: `main/oox` (shared OOXML core, Show and Accounts import), `main/writerfilter`
(Write import), `main/sw/source/filter/ww8` and `main/sc/source/filter/excel` (export and the legacy
binary formats), `main/sd/source/filter`.

- **Corpus.** A versioned set of real-world documents (charity accounts, grant reports, board
  packs, funder templates) plus synthetic documents that exercise one feature each.
- **Round-trip harness.** For each document: open, save as the same format, reopen, and compare
  (a) the XML parts structurally, (b) rendered pages as images, (c) the ODF model. Score per
  feature, publish a table per nightly. This is the metric the programme is judged on.
- **Triage by frequency.** Fix what the corpus shows breaks most, not what is easiest.
- **Known gaps to expect first:** tracked changes and comments in Write, conditional formatting and
  structured tables in Accounts, SmartArt and animation in Show, theme colours and fonts everywhere.

This is the one area where the starting point (AOO's filters, which stopped tracking upstream in
2011) is weakest. The harness makes progress visible; without it the work is unbounded.

## 5. Phase 1 — Extension layer

Trunk ships Python 3.11 and pyuno, and the Python editing and embedding feature is on trunk. These
items are Python extensions with UNO as the boundary. They can be built, tested, and shipped
independently of a core build once Phase 0 exists.

### 5.1 Private assistant

An on-device language model (llama.cpp or equivalent, bundled or user-supplied weights) exposed
as a sidebar in every application. First tasks:

- Summarise a document or selection.
- Draft from an outline, in the document's existing style.
- Explain a formula in plain language; suggest a fix for a broken one.
- Generate documentation for a spreadsheet: what each sheet and named range is for.

No network calls. Model choice, memory limits, and "off" are user settings. Beneficiary and
donor data never leaves the machine, which is the reason this exists.

### 5.2 Checkers

Run on demand and before "send" or "export":

- **PII detection.** Names against a contact source, national insurance and bank-account
  patterns, email addresses, postcodes, dates of birth. Warn before emailing or exporting a sheet.
- **Plain-language checker.** Reading age, sentence length, jargon list per organisation.
- **Accessibility checker.** Alt text, heading order, table headers, contrast, tagged PDF export.

### 5.3 Data connectors

Sources that **refresh** instead of being re-pasted each month: CSV and bank-export files (with
per-bank column maps), SQL via the existing `main/connectivity` drivers, REST endpoints with
authentication stored in the system keyring. Each connector is a parser and gets bounds
hardening and a gtest spec like the importers.

### 5.4 Domain template packs

Templates with logic, shipped as extensions and versioned separately from the suite:

- Invoicing and VAT, including Making Tax Digital submission.
- Gift Aid claim preparation and HMRC schedule export.
- Charity SORP accounts (receipts and payments, and accruals).
- Grant reporting and restricted-fund tracking.

Logic in Python where possible, Basic only where a template must also open elsewhere.

### 5.5 Mail merge and delivery

Write already merges to email through the Python mail-merge provider. Finish it: per-recipient
PDF attachments, a send log, a dry-run preview, and delivery through the user's own SMTP or a
local mail client.

### 5.6 Git-friendly documents

Flat ODF (`.fodt`, `.fods`, `.fodp`) is single-file XML and already diffs. Ship a `git` textconv
filter and a "save for version control" option that writes flat ODF with stable element ordering
and no volatile metadata (timestamps, edit duration, generator string).

## 6. Phase 2 — Accounts engine

Core C++ work in `main/sc`. Each item is a quarter-sized project.

- **LAMBDA-style user functions.** Named lambdas with LET, MAP, REDUCE, and friends in the
  interpreter under `main/sc/source/core/tool` (`interpr*.cxx`, `compiler.cxx`). Stored in ODF
  as named expressions so files stay valid elsewhere.
- **Audit tooling.**
  - Cell-level change history with author and time, built on the existing change tracking in
    `chgtrack.cxx`, surfaced as a per-cell timeline rather than a dialog.
  - Dependency tracing that stays on screen (the Detective, `main/sc/source/core/tool/detfunc.cxx`,
    made persistent and navigable).
  - Warnings: broken references, formulas inconsistent with their row or column, hard-coded
    numbers inside formulas, hidden rows or sheets feeding totals.
- **Python as a first-class formula language.** `=PY("...")` through the add-in interface first;
  then a persistent interpreter per document so cell functions do not pay a bridge crossing per
  call. JavaScript is a follow-on once the engine boundary exists.
- **Live refresh.** Connectors from §5.3 become refreshable ranges with a schedule and a "last
  refreshed" cell.

## 7. Phase 3 — Documents and PDF

- **PDF form filling** on top of the PDF import in `main/sdext/source/pdfimport`, with field
  round-trip rather than flattening.
- **E-signature.** Extend `main/xmlsecurity` from ODF and PDF signing to a guided sign-and-send
  flow: visible signature, certificate management, audit trail in the document.
- **Redaction.** Mark, then burn: text removed from the content stream and metadata, not drawn
  over. Must be verified by re-extracting the text.
- **OOXML fidelity** continues from §4 with corpus-driven targets per release.

## 8. Phase 4 — Keep and co-editing

Both require models the current cores do not have, so they come last and are designed as new
components rather than modifications.

- **Keep.** A local-first, form → table → report data application, Airtable-shaped. SQLite
  storage, forms generated from the schema, reports rendered through Write. Replaces the
  HSQLDB-embedded Base for new documents; the existing `main/dbaccess` and `main/reportdesign`
  stay for legacy files.
- **Real-time co-editing over CRDTs.** Offline-first, self-hosted on a NAS or VPS. Requires a
  change-log document model, so Keep is the first host (its model is new), Accounts second (cell
  grid maps well), Write last (rich text and layout are hardest). The sync server is a small,
  separately built daemon.

## 9. Open decisions and risks

- **Substrate.** This roadmap assumes staying on the AOO trunk fork. The OOXML gap is the
  cost of that choice. The fidelity harness (§4) is the early-warning signal: if after two release
  cycles the corpus score is not moving, revisit the base before Phase 3.
- **Licensing.** Apache 2.0 stays for the suite. Bundled model weights and template packs need
  their own licence review; category-B components remain opt-in.
- **Platform.** Linux first for CI and nightlies. Windows is where most charity desktops are;
  it must be green by the end of Phase 1.
- **Team size.** Phases are sized for a small team. Phase 4 is not achievable alone.
