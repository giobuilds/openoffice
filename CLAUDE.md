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

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A **hardening fork of Apache OpenOffice trunk** (the future 4.5.x line), not an official ASF release.
Default branch is `trunk`. Nearly all fork-specific work is importer/parser bounds hardening
tracked in GitHub issue #1 (punch list) and issue #11; branch names follow `issue-<n>-<topic>` and
land via PR merges. See `SECURITY.md` for the reporting policy and `AOO-trunk.md` for a trunk vs
AOO42X divergence analysis (trunk is Python 3.11 + native Win64 UNO bridge; AOO42X is Python 2.7).

The fork is being rebranded as **Work** (Write, Accounts, Show, Keep); product direction and phase
sequencing are in `docs/ROADMAP.md`; the visual identity and its implementation map are in
`docs/design/WORK-UI.md`, with the design mockup checked in verbatim under `docs/design/mockup/`.
Module directories keep their upstream names.

Almost all code lives under `main/` (~200 modules). Other top-level dirs:

- `ext_libraries/` – gtest, hunspell, coinmp built as extra "modules" (`build_dir ../ext_libraries/gtest`).
- `ext_sources/` – downloaded third-party tarballs, named `<md5>-<name>`; `bootstrap` fetches
  whatever is listed in `main/external_deps.lst` that is missing. CI caches this dir keyed on that file.
- `test/` – standalone Java/JUnit BVT/FVT/API suites run against an *installed* office (needs Ant + JDK 8).
  See `test/README.md`; needs a full build, so it is rarely usable here.
- `win10-msvc/` – notes on building trunk with modern MSVC.

## Build system

Two generations coexist and `build.pl` drives both:

- **dmake** modules: `prj/build.lst` (dependency graph, one line per directory), `prj/d.lst`
  (deliver rules), and `makefile.mk` per directory. Output goes to `main/<INPATH>/` (Linux x86-64:
  `unxlngx6.pro`) and `deliver.pl` copies it into `main/solver/`.
- **gbuild** modules (107 of them, e.g. `sw`, `vcl`, `o3tl`): `Module_<mod>.mk`, `Library_*.mk`,
  `GoogleTest_*.mk`, `JunitTest_*.mk`, plus a stub `Makefile` that pulls in `$(SOLARENV)/gbuild`.
  These still carry a one-line `prj/build.lst` so `build.pl` can order them. Default goal is
  `allandcheck` (compile + run GoogleTests); other goals: `all`, `check`, `subsequentcheck`, `clean`.
  Output: `OUTDIR=$SOLARVERSION/$INPATH`, `WORKDIR=$OUTDIR/workdir`.

Module ordering and dependencies come only from `prj/build.lst`. Starting `build.pl` inside a
subdirectory does not pull module-level prerequisites, so build `soltools` (makedepend) and friends
first (see the CI scripts).

### Configure and bootstrap (from `main/`)

```sh
cd main
autoconf
./configure <switches>        # see .github/scripts/linux-sal-gtest.sh for the known-good Linux set
./bootstrap                   # builds dmake, fetches ext_sources
. ./source_soenv.sh           # or: source *.Set.sh  (sets SOLARENV, INPATH, aliases build/deliver)
```

The sourced env file uses shell aliases and unset variables. In scripts use `set +u`,
`shopt -s expand_aliases`, and call `perl "$SOLARENV/bin/build.pl"` / `deliver.pl` directly.

The CI configure line disables Java, ODK, GTK, CUPS, NSS, category-B, fonts, etc. and uses system
boost/python/libxml/libxslt/expat/zlib/openssl/curl/jpeg/libpng plus `--enable-unit-tests` and
`--with-dmake-url=https://github.com/jimjag/dmake/archive/v4.13.1/dmake-4.13.1.tar.gz`. HarfBuzz
CI adds `--enable-harfbuzz --with-system-harfbuzz` (the bundled build needs meson/ninja and is only
attempted with `--enable-harfbuzz` and no `--with-system-harfbuzz`).

### Building modules

```sh
# in a module dir after sourcing the env
build                          # this module only (alias for build.pl)
build -P$(nproc)               # parallel
build --all                    # everything up to and including this module (full office from instsetoo_native)
build --from sfx2              # sfx2 and everything depending on it, up to here
deliver                        # dmake modules: copy outputs into main/solver
```

A full office build takes hours and needs the full dependency set; nothing in this tree is
prebuilt (no `main/solver`, no `*.Set.sh` present). Prefer the slim per-module path used by CI.

### Tests

- **GoogleTest (C++)** – gbuild modules with `GoogleTest_*.mk` run tests as part of the default
  goal. Build+run for one module: `cd main/o3tl && build`. The binary lands at
  `$WORKDIR/LinkTarget/GoogleTest/<name>` (e.g. `o3tl_test`); run it directly with
  `--gtest_filter=Suite.Case` for a single test. `sal` uses dmake `APP1TEST` gtests under `sal/qa`.
- **JUnit (Java)** – `JunitTest_*.mk` per module; need `--with-java`, not run in CI.
- **CI** (`.github/workflows/linux-*.yml` → `.github/scripts/linux-*.sh`) are slim checks, not a
  full build: `linux-sal-gtest` (soltools, xml2cmp, stlport, gtest, sal, o3tl, salhelper),
  `linux-icu`, `linux-libxml2`, `linux-xmlsec`, `linux-harfbuzz`, `pre-commit`. Run a script
  locally with `bash .github/scripts/linux-sal-gtest.sh` to reproduce CI exactly.

### Lint

```sh
make check          # installs + runs pre-commit on all files (gitleaks, codespell, markdownlint, whitespace/EOL fixers)
pre-commit run --files <paths>
make createwordlist # regenerate .github/linters/codespell.txt
```

The `insert-license` hook prepends the Apache license comment block to every `.md` file, and the
EOL/whitespace hooks touch most source extensions, so run pre-commit before committing to avoid
churn. `markdownlint` disables MD013 (line length), MD025, MD033, MD040.

## Hardening conventions (the fork's main work)

Look at recent `git log` for the pattern; commits are small and one importer at a time:

- **Bound before allocate.** Cap sizes read from the file against the remaining stream length
  (`remain`), a 64M ceiling (64M pixels for images, 64M bytes for blobs), and container limits
  (`Polygon` point counts must fit 16-bit; `SAL_MAX_INT32 / 32` per side). On failure set the
  reader's status false and return, rather than clamping silently.
- **Spec-mirror gtests.** Every bound is paired with a case in `main/o3tl/qa/test-importbounds.cxx`,
  which re-implements the predicate (e.g. `tiffDimensionsOk`) and lists the source file it mirrors
  in its header comment. Add the file to that list when hardening a new importer and keep the
  predicate in sync with the real code. This runs in the `linux-sal-gtest` CI job.
- **Commit message** states the format field widths, why the existing check was insufficient,
  and whether it was verified by a full office build (usually "Not verified by a full office build.").
- Code style follows the surrounding file: tabs, `sal_Bool`/`sal_True`, `sal_uLong`, space-padded
  parentheses `if ( x )`. Do not reformat existing lines.

## Key layout pointers

- `main/solenv/` – build system: `bin/build.pl`, `bin/deliver.pl`, `gbuild/` (platform files in
  `gbuild/platform/linux.mk` etc.), `inc/` dmake includes.
- `main/configure.ac`, `main/set_soenv.in` – configure and environment generation.
- `main/sal`, `main/o3tl`, `main/salhelper` – lowest layer (System Abstraction Layer), no UNO deps.
- `main/cppu`, `main/cppuhelper`, `main/bridges`, `main/udkapi`, `main/offapi` – UNO runtime and IDL API.
- `main/tools`, `main/vcl`, `main/svtools`, `main/svx`, `main/sfx2`, `main/framework` – GUI/app framework stack.
- `main/sw` (Writer), `main/sc` (Calc), `main/sd` (Impress/Draw), `main/starmath`, `main/chart2`.
- Import filters hardened so far: `main/filter/source/graphicfilter/*`, `main/filter/source/msfilter/*`,
  `main/svtools/source/filter/*`, `main/sw/source/filter/ww8/*`, `main/sc/source/filter/*`,
  `main/editeng/source/rtf/*`, `main/svtools/source/svrtf/*`.
- `main/instsetoo_native` – packaging; `build --all` here produces installers.
