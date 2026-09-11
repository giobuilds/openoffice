#!/bin/bash
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

# Run the fidelity harness locally against a private corpus, using the
# installed office that CI built (the work-linux-x86_64-installed
# artifact), so documents never have to be committed.
#
#   test/fidelity/run-local.sh [corpus_dir] [out_dir]
#
# Defaults: corpus test_files/ (git-ignored), output .fidelity-local/.
# Needs: gh (logged in), zstd, and a python3.X matching the artifact's
# pyuno (the script tells you which). Set RUN_ID to pick a specific
# linux-full-build run; otherwise the newest successful one is used.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CORPUS="${1:-${ROOT}/test_files}"
OUT="${2:-${ROOT}/.fidelity-local}"
CACHE="${ROOT}/.local-office"

test -d "${CORPUS}" || { echo "no corpus directory: ${CORPUS}" >&2; exit 2; }

run_id="${RUN_ID:-$(gh run list --workflow linux-full-build --limit 20 --json databaseId,conclusion \
    -q '[.[] | select(.conclusion=="success")][0].databaseId')}"
test -n "${run_id}" || { echo "no successful linux-full-build run found" >&2; exit 2; }

office="$(ls -d "${CACHE}"/*/openoffice*/ 2>/dev/null | sed -n '1p' || true)"
if test -z "${office}" -o "$(cat "${CACHE}/run_id" 2>/dev/null)" != "${run_id}"; then
    echo "===== downloading installed office from run ${run_id} ====="
    rm -rf "${CACHE}"
    mkdir -p "${CACHE}/dl" "${CACHE}/${run_id}"
    gh run download "${run_id}" -n work-linux-x86_64-installed -D "${CACHE}/dl"
    tar -C "${CACHE}/${run_id}" -I zstd -xf "${CACHE}/dl"/work-linux-x86_64.tar.zst
    rm -rf "${CACHE}/dl"
    echo "${run_id}" > "${CACHE}/run_id"
    office="$(ls -d "${CACHE}"/*/openoffice*/ | sed -n '1p')"
fi
office="${office%/}"
echo "office: ${office}"

pyunoso="$(find "${office}" -name 'pyuno.so' | sed -n '1p')"
unopy="$(find "${office}" -name uno.py | sed -n '1p')"
pyunolib="$(find "${office}" -name 'libpyuno.so' | sed -n '1p')"
test -n "${pyunoso}" -a -n "${unopy}" || { echo "pyuno.so / uno.py not found in ${office}" >&2; exit 2; }

# pyuno.so is linked against one specific libpython; use that interpreter.
pyver="$( (ldd "${pyunoso}" 2>/dev/null; strings "${pyunoso}" 2>/dev/null) | grep -oE 'libpython3\.[0-9]+' | sort -u | sed 's/libpython//' | sed -n '1p')"
py="$(command -v "python${pyver:-3}" || true)"
if test -z "${py}"; then
    echo "pyuno.so needs python${pyver}, which is not installed here." >&2
    echo "Fedora: sudo dnf install python${pyver}   Debian/Ubuntu: sudo apt install python${pyver}" >&2
    exit 3
fi
echo "python: ${py} (pyuno built for ${pyver:-?})"

export PYTHONPATH="$(dirname "${unopy}"):$(dirname "${pyunoso}"):${office}/program${PYTHONPATH:+:${PYTHONPATH}}"
export URE_BOOTSTRAP="vnd.sun.star.pathname:${office}/program/fundamentalrc"
export LD_LIBRARY_PATH="$(dirname "${pyunoso}"):$(dirname "${pyunolib:-${office}/program/x}"):${office}/program${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
export HOME="${OUT}/home"
mkdir -p "${HOME}" "${OUT}/out"

"${py}" -c 'import uno; print("pyuno import ok")'
"${py}" "${ROOT}/test/fidelity/run.py" "${office}" "${CORPUS}" "${OUT}/out"
echo "report: ${OUT}/out/report.md"
