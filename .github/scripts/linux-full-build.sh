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

# Roadmap Phase 0: full Linux office build. Configure, bootstrap, build
# every module up to instsetoo_native with the "installed" package
# format, then start the result headless and round-trip one document
# per application. This is the job that makes the rest of the roadmap
# verifiable; the other linux-*.sh scripts are slim module checks.
#
# Usage: bash .github/scripts/linux-full-build.sh [build|smoke|all]
#   build  configure + bootstrap + build --all (default when omitted: all)
#   smoke  headless round-trip against an existing installed tree
#
# A JDK is a hard build dependency of this tree even with --without-java:
# gbuild defines SOLAR_JAVA unconditionally and jvmfwk/ridljar have no
# Java gate, so the first run failed on jni.h and Ant. Build with Java.
#
# Known narrowing, to be lifted in later phases: no category-B
# components, no GTK plugin, no bundled fonts, en-US only.

set -euo pipefail

STAGE="${1:-all}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/main"

NPROC="$(nproc)"
export MAXPROCESS="${MAXPROCESS:-$NPROC}"
export CCACHE_DIR="${CCACHE_DIR:-${HOME}/.ccache}"
export CCACHE_COMPRESS=1
export CCACHE_MAXSIZE="${CCACHE_MAXSIZE:-5G}"
if test -d /usr/lib/ccache; then
    export PATH="/usr/lib/ccache:${PATH}"
fi
export CC="${CC:-gcc}"
export CXX="${CXX:-g++}"
export verbose="${verbose:-TRUE}"

find_jdk() {
    # JDK 8 first: set_soenv.in and libs.mk look for libjawt and the JVM
    # under $JAVA_HOME/jre/lib/amd64, a layout JDK 9+ no longer has, so
    # the bean module fails to link against a newer JDK.
    local c
    for c in "${JDK_HOME:-}" "${JAVA_HOME_8_X64:-}" "${JAVA_HOME_11_X64:-}" "${JAVA_HOME_17_X64:-}" "${JAVA_HOME:-}"; do
        if test -n "${c}" -a -x "${c}/bin/javac"; then
            echo "${c}"
            return 0
        fi
    done
    echo "no JDK found (set JDK_HOME)" >&2
    return 1
}

configure_and_bootstrap() {
    local jdk ant
    jdk="$(find_jdk)"
    ant="${ANT_HOME:-/usr/share/ant}"
    echo "nproc=${NPROC} CC=${CC} CXX=${CXX} jdk=${jdk} ant=${ant}"
    "${jdk}/bin/javac" -version
    test -x "${ant}/bin/ant"
    ccache -s || true
    df -h . || true

    autoconf

    # Same system-library set as linux-sal-gtest.sh. EPM stays enabled:
    # instsetoo_native skips packaging entirely when EPM=NO, and configure
    # does not need an epm binary for the "installed" format.
    ./configure \
        --with-jdk-home="${jdk}" \
        --with-ant-home="${ant}" \
        --without-junit \
        --disable-odk \
        --disable-gtk \
        --disable-gconf \
        --disable-cups \
        --disable-nss-module \
        --disable-category-b \
        --disable-coinmp \
        --disable-ldap \
        --disable-online-update \
        --without-fonts \
        --enable-unit-tests \
        --enable-harfbuzz \
        --with-system-harfbuzz \
        --with-package-format=installed \
        --with-system-boost \
        --with-system-python \
        --with-system-libxml \
        --with-system-libxslt \
        --with-system-expat \
        --with-system-zlib \
        --with-system-openssl \
        --with-system-curl \
        --with-system-jpeg \
        --with-system-libpng \
        --with-dmake-url=https://github.com/jimjag/dmake/archive/v4.13.1/dmake-4.13.1.tar.gz

    ./bootstrap
}

source_env() {
    # Env.Set.sh uses aliases and can reference unset vars.
    set +u
    # shellcheck disable=SC1091
    . ./source_soenv.sh
    shopt -s expand_aliases
    if test -z "${SOLARENV:-}"; then
        echo "SOLARENV is empty after sourcing the build environment" >&2
        exit 1
    fi
}

build_all() {
    # Keep the full output in a file: the GitHub log endpoints truncate or
    # refuse multi-hour logs, so the workflow uploads this as an artifact
    # and prints a short failure summary from it.
    local log="${BUILD_LOG:-${ROOT}/build.log}"
    echo "===== build --all from instsetoo_native (log: ${log}) ====="
    set +e
    ( cd instsetoo_native && perl "${SOLARENV}/bin/build.pl" --all -P"${MAXPROCESS}" ) 2>&1 | tee "${log}"
    local rc=${PIPESTATUS[0]}
    set -e
    ccache -s || true
    df -h . || true
    if test "${rc}" -ne 0; then
        echo "===== build failed (rc=${rc}); summary ====="
        grep -n 'occurred while making\|resume the build' "${log}" | tail -n 20 || true
        grep -nE ': error:|: fatal error:|undefined reference|BUILD FAILED|dmake:  Error|make: \*\*\*|ICU Error|No such file' "${log}" \
            | grep -v 'zip warning' | tail -n 60 || true
        return "${rc}"
    fi
}

find_office() {
    local office
    office="$(ls -d "${ROOT}"/main/instsetoo_native/*/Apache_OpenOffice/installed/install/en-US/*/ 2>/dev/null | sed -n '1p' || true)"
    if test -z "${office}" -o ! -x "${office}program/soffice"; then
        echo "no installed office found under instsetoo_native/*/Apache_OpenOffice/installed" >&2
        ls -R "${ROOT}"/main/instsetoo_native/*/Apache_OpenOffice 2>/dev/null | head -n 40 >&2 || true
        exit 1
    fi
    echo "${office%/}"
}

smoke() {
    local office soffice work
    office="$(find_office)"
    soffice="${office}/program/soffice"
    echo "===== smoke: ${soffice} ====="
    ls -l "${soffice}" "${office}/program/bootstraprc" || true

    work="${ROOT}/.smoke"
    rm -rf "${work}"
    mkdir -p "${work}/in" "${work}/out"
    # Fresh profile: the office keeps it under $HOME.
    export HOME="${work}/home"
    mkdir -p "${HOME}"

    printf 'Work smoke document.\n\nOne paragraph is enough to prove Write loads and saves.\n' > "${work}/in/write.txt"
    printf 'Item,Jan,Feb\nWholesale,18400,19250\nMarket stall,6120,5880\n' > "${work}/in/accounts.csv"
    local otp
    # sed instead of head: under pipefail, head closing the pipe fails sort.
    otp="$(find "${ROOT}/main/extras/source/templates/layout" -name '*.otp' | sort | sed -n '1p')"
    test -n "${otp}"
    cp "${otp}" "${work}/in/show.otp"

    # The office has no -convert-to switch; drive it over a UNO pipe.
    # With --with-system-python there is no program/python wrapper, and
    # scp2 puts uno.py, pyuno.so and libpyuno.so into the URE directory
    # (gid_Dir_Common_Ure), not program/, so locate them instead of
    # assuming a layout. Mirrors what pyuno/zipcore/python.sh sets up.
    local py unopy pyunoso pyunolib
    if test -x "${office}/program/python"; then
        py="${office}/program/python"
    else
        unopy="$(find "${office}" -name uno.py | sed -n '1p')"
        pyunoso="$(find "${office}" -name 'pyuno.so' | sed -n '1p')"
        pyunolib="$(find "${office}" -name 'libpyuno.so' | sed -n '1p')"
        echo "uno.py=${unopy} pyuno.so=${pyunoso} libpyuno.so=${pyunolib}"
        test -n "${unopy}" -a -n "${pyunoso}"
        export PYTHONPATH="$(dirname "${unopy}"):$(dirname "${pyunoso}"):${office}/program${PYTHONPATH:+:${PYTHONPATH}}"
        export URE_BOOTSTRAP="vnd.sun.star.pathname:${office}/program/fundamentalrc"
        export LD_LIBRARY_PATH="$(dirname "${pyunoso}"):$(dirname "${pyunolib:-${office}/program/x}"):${office}/program${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
        py="python3"
    fi
    echo "python runner: ${py}"
    echo "PYTHONPATH=${PYTHONPATH:-} LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}"
    "${py}" -c 'import uno, sys; print("pyuno import ok, python", sys.version.split()[0])'
    timeout 1200 "${py}" "${ROOT}/.github/scripts/smoke_roundtrip.py" \
        "${office}" "${work}/in" "${work}/out"

    ls -l "${work}/out"
    for f in write.odt accounts.ods show.odp write.pdf; do
        test -s "${work}/out/${f}" || { echo "missing or empty: ${f}" >&2; exit 1; }
    done
    # ODF containers must be zip files with a mimetype entry.
    for f in write.odt accounts.ods show.odp; do
        unzip -p "${work}/out/${f}" mimetype | grep -q '^application/vnd.oasis.opendocument'
    done
    echo "linux-full-build smoke: ok"
}

case "${STAGE}" in
    build)
        configure_and_bootstrap
        source_env
        build_all
        ;;
    smoke)
        smoke
        ;;
    all)
        configure_and_bootstrap
        source_env
        build_all
        smoke
        ;;
    *)
        echo "unknown stage: ${STAGE}" >&2
        exit 2
        ;;
esac

echo "linux-full-build (${STAGE}): ok"
