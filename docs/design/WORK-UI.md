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

# Work — UI specification

**Source:** the Claude Design project "Work suite UI mockups", file `Work Suite.dc.html`, on the
Organic design system. The mockup and its stylesheet are checked in verbatim under
`docs/design/mockup/` (open `work-suite.dc.html` in a browser to click through it). This document
translates that mockup into what the office suite has to do, and records where each part lands in
the tree and what has been done.

The product roadmap is `docs/ROADMAP.md`; this file covers only the look and the chrome.

## 1. Design tokens

All values come from `docs/design/mockup/_ds/organic-*/styles.css` (light) and the `.wk[data-theme="dark"]`
block at the top of the mockup (dark). Ramps are OKLCH-generated on a shared lightness scale; use a
ramp step rather than an ad-hoc mix wherever the suite has a single colour slot.

### Colour

| Role | Light | Dark | Used for |
| --- | --- | --- | --- |
| bg | `#f5ead8` | `#211e1a` | window ground, rail-active tile, primary button text |
| surface | `#ebddc5` | `#2c2822` | title bar, rail, tab strip, status bar, side panel, cards |
| text | `#201e1d` | `#f3e8d6` | UI text; muted variants are 55–78% mixes over bg |
| divider | 16% of text over bg | 18% of text over bg | every 1px rule and border |
| accent (terracotta) | `#c67139` | `#e2905a` | primary buttons, selection outline, active segment, Write tint |
| accent-2 (sage) | `#7a8a5e` | `#a4b57f` | Accounts tint, totals rows, "current" status, second voice |
| neutral-100 | `#f9f4ed` | `#2c2822` | document page, slide canvas, template thumbnails |
| neutral-200 | `#eee7db` | `#37322a` | area around the page and slide |
| neutral-300 | `#dcd3c4` | `#463f34` | grid lines, boundaries, zoom track, Keep tint |
| neutral-600 | `#82796a` | `#b3a894` | secondary labels, column/row headers, kickers |
| neutral-900 | `#2e2b25` | `#f6ecdb` | document text |
| accent-100 / 200 / 300 | `#fff2eb` / `#ffe1d0` / `#ffc6a5` | `#3a291f` / `#4b3324` / `#6a452c` | Revenue row tint, active ribbon tab, Show tint, chart bars |
| accent-700 / 800 | `#8c491a` / `#643312` | `#f4c19a` / `#f4c19a` | accent-coloured text (links, negatives, active rail label) |
| accent-2-100 / 200 / 300 | `#f0fae1` / `#e1eecc` / `#ccdbb2` | `#2b3125` / `#39422c` / `#4b5739` | Net row tint, active sheet tab, avatar |

Contrast rule from the design system: accent on bg is tuned to 3:1, enough for chrome and large
text, not for body copy. Accent-coloured body text uses accent-700 on the light ground.

### Per-application identity

Each app has a tint (fill) and an ink (text on that fill), used on the Start tiles, the empty-state
mark, recents dots and the document-tab strip.

| App | Upstream | Tint | Ink | Icon (Lucide, stroke 2.75) |
| --- | --- | --- | --- | --- |
| Write | Writer | accent-200 | accent-800 | three lines + pen |
| Accounts | Calc | accent-2-200 | accent-2-800 | rounded grid |
| Show | Impress | accent-300 | accent-900 | monitor on stand |
| Keep | Base | neutral-300 | neutral-900 | database cylinder |
| Start | Start Center | bg | accent-700 | four tiles |

Draw and Math keep their upstream names and are reached from the "+" tab and the Start chips, not
the rail.

### Type

| Slot | Face | Notes |
| --- | --- | --- |
| Display | Caprasimo 400 | app names, document titles, dialog titles, primary button labels, the W mark |
| UI | Figtree 400/600/700 | everything else; 600 for labels and tabs, 700 for cell/row headers |
| Document body (mockup) | Figtree 13.5 / 1.75 | the letter template's Body style |
| Kickers | Figtree 9.5–11, uppercase, tracking .11–.16em | section labels in panels and sidebars |
| Numbers | tabular figures | spreadsheet cells and Keep balances |

Both faces are SIL Open Font License. They are not bundled yet (see §5).

### Shape and spacing

- Radii: 8 / 16 / 28 px. Pills (999px) for every button, chip, tab and input. Window frame 28px.
- Spacing scale ×1.10: 4.4 / 8.8 / 13.2 / 17.6 / 26.4 / 35.2 px.
- Shadows: `0 1px 2px`, `0 3px 10px`, `0 12px 32px` of ink at 14/16/22%. The page and the slide sit
  on the medium shadow; dialogs on the large one.
- Dividers are 1px of the divider colour. No hairline-only geometry, no sharp corners.

## 2. Window anatomy

Fixed parts, top to bottom and left to right, at the mockup's 1340×862:

1. **Title bar** (46px, surface). Traffic lights in accent-500 / accent-2-400 / neutral-400; centred
   window title "*Document* — *App*" or "Work — Start"; right side "Saved 2 min ago" and a
   sage avatar disc with initials in Caprasimo.
2. **App rail** (78px, surface, right divider). A 34px accent disc with a white Caprasimo "W", then
   five 58px tiles: Start, Write, Accounts, Show, Keep. Each tile is an icon over a 10px 600-weight
   label; the active tile is filled with bg and its label is accent-700. "Save as" sits at the bottom.
3. **Document tabs** (surface, bottom divider). Open documents as 14px-top-rounded tabs; the active
   tab is bg with a divider border and no bottom edge; "+" after them; the app tagline
   ("Write · documents", "Accounts · books and numbers", "Show · slides", "Keep · records") at the
   right. Hidden on Start.
4. **Command area**: one of two chrome models, chosen in the mockup strip and meant to be a user
   setting.
   - **Ribbon.** A row of pill tabs Home / Insert / Layout / Review / View (active = accent-200 fill,
     accent-800 text), then groups separated by dividers, each a row of pill buttons over a
     uppercase kicker. Groups per app are listed in §3.
   - **Minimal + panel.** One 11px-padded row: the document title in Caprasimo 16, a short quick bar
     of ghost pills, then "⌘K Commands" and a solid accent primary action (Share draft / Chart
     range / Present / New record). A 262px context panel appears on the right (see 5).
5. **Context panel** (262px, surface, left divider; minimal chrome only). Caprasimo title and sub
   line, four labelled pill fields with a chevron, a chip group, and a footer note. Contents per app
   are in §3.
6. **Status bar** (32px, surface, top divider). Three or four short facts on the left, the chrome
   model or version on the right, then "100%" and a 64px zoom track with an accent thumb.
7. **Dialogs** overlay the whole window with a 42% ink scrim; 520px card in bg with 28px radius,
   Caprasimo 22 title, muted sub line, uppercase-labelled pill inputs, a row of choice tags, then
   Cancel (secondary) and a solid accent confirm.

## 3. Screens

### Start

Replaces the Start Center. Left column: an organisation kicker ("Bramble Bakehouse · 4 seats"), a
Caprasimo 40 greeting ("Good morning, Rosa"), one sentence of what needs doing, a 4-up grid of app
tiles (44px tinted icon disc, Caprasimo 20 name, one-line blurb), then "Pick up where you left off"
as a row list (app-tinted dot, name, app, when). Right column (296px, surface): "Needs you" cards
(title + meta), "Start something" outline chips (Customer letter, Quote, Cash flow, Payroll, Deck,
Stock table), and a footer "Work keeps files on your own disk. Where things are saved →".

Status bar: organisation, "9 files on this machine", "Backup ran 06:00", "Work 1.0".

### Empty state (any app)

Centred: 60px app-tinted disc with the icon, Caprasimo 30 title, one-line blurb, then a row of
186px template cards (a bg swatch with four rounded skeleton lines, the first tinted; name and meta
below), and a secondary "Open the one I was writing instead".

| App | Title | Templates |
| --- | --- | --- |
| Write | A blank page, or a start | Blank; Customer letter; Quote; Terms sheet |
| Accounts | A new book | Blank book; Cash flow; Payroll; Invoice tracker |
| Show | A new deck | Blank deck; Wholesale review; Supplier pitch; Team update |
| Keep | A new store | Blank store; Customers & orders; Stock; Suppliers |

### Write

Left: 212px Navigator with an outline (indent 12px per level, current heading in accent-100 /
accent-800) and page thumbnails (active page has a 2px accent border). Centre: neutral-200 field,
660px page in neutral-100 on the medium shadow with 52/62px margins; letterhead row, Caprasimo 31
title, muted sub line, 13.5/1.75 body, a pull quote with a 3px accent-300 left rule.

Ribbon: Text (B I U) · Paragraph (Flush left, List, Spacing) · Insert (Table, Image, Comment) ·
Styles (Body, Heading, Pull quote). Quick bar: B, I, Styles, Comment. Panel: "Paragraph" with
Style / Face / Line height / Space after, "Recent styles" chips. Status: Page 1 of 2 · 412 words ·
English (UK) · Draft.

### Accounts

Formula row: cell reference in a 700-weight pill, "ƒx", the formula in monospace. Grid: 38px row
header column and A–G column headers in surface with 10.5px 700 neutral-600 text; the selected
column header is accent-200. Cells 12.5px, tabular numbers, right-aligned; first column and header
row 600. Negative numbers in accent-700. Row tints: Revenue row accent-100, Net row accent-2-100.
Selected cell has a 2px accent outline inset. Sheet tabs at the bottom as pills (active =
accent-2-200 / accent-2-800), "+", and a solid accent "Chart this range" on the right.

Ribbon: Number (£ % 0.00) · Formula (Σ Sum, Average, Lookup) · Insert (Chart, Rows, Pivot) · Review
(Freeze, Trace). Panel: "Cell format" with Number / Alignment / Fill / Border and "Named ranges"
chips (Revenue, Costs, Net); foot "Named ranges can be used in Show and in Keep reports."

"Chart this range" dialog: Range, Title; choices Columns / Line / Stacked / Send to Show; confirm
"Insert chart".

### Show

Left: 176px slide sorter with 80px cards (Caprasimo 9.5 title, two skeleton lines, number top
right; active = 2px accent border). Centre: neutral-200 field with a 16:9 slide (max 760px,
neutral-100, 10px radius, medium shadow); uppercase accent-700 kicker, Caprasimo 34 title, bullets
with 7px accent dots, and a bar chart whose last bar is accent and the rest accent-300.

Ribbon: Slide (New, Layout, Duplicate) · Insert (Image, Chart, Shape) · Transition (Fade, None) ·
Present (From start, Notes). Panel: "Slide layout" with Layout / Palette / Title face / Transition
and "Data source" chips (Accounts · Cash flow, Live link).

### Keep

Left: 206px sidebar with "Tables" (Customers, Orders, Suppliers, Products with counts; active =
accent-100 / accent-800) and "Saved queries" as dashed-outline rows. Header: Caprasimo 17 table
name, a neutral count tag, and a Grid / Form segmented pill. Grid view: the design system's
`.table` with uppercase 10.5px headers and status tags (Current = sage, Overdue = accent, Watch =
outline). Form view: uppercase-labelled pill inputs, "Save record" (primary) and "New order for
this customer" (secondary), and a "Linked orders" column of small cards.

Ribbon: Record (New, Duplicate, Delete) · Table (Fields, Relations, Index) · Query (Filter, Sort,
Report). Panel: "Field properties" with Type / Choices / Required / Default, "Used in" chips.

### Save a copy (any app)

Name, Where; choices Work format / Open format / PDF / Send to accountant; confirm "Save".

## 4. Implementation map

What the codebase can take today, and where. Verification status is honest: this tree has no full
office build (see `docs/ROADMAP.md` Phase 0), so runtime checks are still open.

### Done in this pass (data and string files, XML validated with xmllint)

| Design element | Change | File |
| --- | --- | --- |
| App names in title bars, tabs, menus | Writer → Write, Calc → Accounts, Impress → Show, Base → Keep (and "Keep: …" sub-views), en-US | `main/officecfg/registry/data/org/openoffice/Setup.xcu` |
| Light palette for the document area | Default colour scheme filled: page neutral-100, app background neutral-200, boundaries and grids neutral-300, document text neutral-900, links accent-700/800, spell underline accent, sage note background | `main/officecfg/registry/data/org/openoffice/Office/UI.xcu` |
| Dark palette | Second scheme "Work Dark" with the mockup's dark tokens, selectable under Options › Appearance | same file |
| UI face | Figtree first in the `en` UI sans list; falls through to the old list when the font is absent | `main/officecfg/registry/data/org/openoffice/VCL.xcu` |
| Launcher names and descriptions (Linux) | Name and Comment lines | `main/sysui/desktop/menus/{writer,calc,impress,base}.desktop` |
| Installer module names and Start-menu tooltips | en-US strings | `main/scp2/source/{writer,calc,impress,base}/module_*.ulf`, `folderitem_*.ulf` |
| Splash progress bar | terracotta bar on neutral-300 frame | `main/instsetoo_native/util/openoffice.lst` |

### Next, in order

1. **Product name.** `PRODUCTNAME`, `FULLPRODUCTNAME`, `SERVICETAG_*`, `AOODOWNLOADNAMEPREFIX`,
   download names and `STARTCENTER_*_URL` in `main/instsetoo_native/util/openoffice.lst`. Changing
   `PRODUCTNAME` also renames the install directory, the user profile directory, registry keys and
   the branded colour-scheme node, and `test/README.md` hard-codes `openoffice4`. Do it as one
   commit with the installer and the test docs, after Phase 0 can install the result.
2. **Fonts.** Add Figtree and Caprasimo to `main/more_fonts` (OFL, licence text into
   `LICENSE_aggregated`), then add Caprasimo to the document heading defaults in `VCL.xcu` and set
   the Write templates' Body style to Figtree 13.5 / 1.75.
3. **Icons.** A "work" icon theme under `main/default_images` built from Lucide at stroke 2.75,
   starting with the five rail icons, the app icons in `main/sysui/desktop/icons`, and the splash and
   about images in `main/default_images/introabout` (551×366 and 400×100).
4. **Start screen.** `main/framework/source/services/backingwindow.cxx` draws the current Start
   Center from `backing.png` and hard-coded text colours (lines 351–413, 659–669). Rework it to the
   §3 layout: greeting, tiles, recents, "Needs you". Strings live in
   `main/framework/source/services/fwk_services.src` (`STR_BACKING_*`).
5. **Window chrome.** The app rail, document tabs and status bar are new VCL work in
   `main/framework` (layout manager) and `main/vcl`. Ribbon and Minimal + panel are two
   configurations of the same toolbar/sidebar data in `main/officecfg/registry/data/org/openoffice/Office/UI/*.xcu`;
   the panel maps onto the sidebar framework in `main/sfx2/source/sidebar`.
6. **Controls.** Pill buttons, 16–28px radii and the accent focus ring are `StyleSettings` and
   native-widget drawing in `main/vcl/source/window` and the per-platform `salnativewidgets`.
7. **Dialogs.** "Save a copy" and "Chart this range" are new dialogs in `main/sfx2` and `main/sc`
   respectively; the choice-tag row is a new control.

## 5. Open items

- Font bundling and the OFL licence review (item 2).
- The Start screen's greeting and "Needs you" list need a user name and a task source; the task
  source is the Accounts audit tooling in the roadmap (Phase 2).
- "Send to accountant" and "Send to Show" imply the mail-merge and cross-app link features in
  the roadmap; the dialogs can ship with those choices disabled.
- Dark mode is a colour scheme only. Chrome surfaces (rail, tabs, status bar) follow the system
  theme until item 5 lands.
