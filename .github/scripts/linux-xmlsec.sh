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

# Slim Linux CI (issue #3 phase 2): compile bundled xmlsec 1.3.x against
# system NSS and system libxml2. Not a full office build.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/main"

NPROC="$(nproc)"
export MAXPROCESS="${MAXPROCESS:-$NPROC}"
export CCACHE_DIR="${CCACHE_DIR:-${HOME}/.ccache}"
export CCACHE_COMPRESS=1
export CCACHE_MAXSIZE="${CCACHE_MAXSIZE:-2G}"
if test -d /usr/lib/ccache; then
    export PATH="/usr/lib/ccache:${PATH}"
fi
export CC="${CC:-ccache gcc}"
export CXX="${CXX:-ccache g++}"
export verbose="${verbose:-TRUE}"

echo "nproc=${NPROC} CC=${CC} CXX=${CXX}"
ccache -s || true

autoconf

# xmlsec needs NSS. --disable-category-b forces enable_nss_module=no
# (configure.ac), so this job enables category B and uses distro NSS
# (>= 3.91, required by xmlsec 1.3.10+) plus distro libxml2.
./configure \
    --without-java \
    --without-junit \
    --disable-odk \
    --disable-epm \
    --disable-gtk \
    --disable-gconf \
    --disable-cups \
    --enable-category-b \
    --disable-ldap \
    --disable-online-update \
    --without-fonts \
    --enable-unit-tests \
    --with-system-boost \
    --with-system-python \
    --with-system-nss \
    --with-system-hunspell \
    --with-system-hyphen \
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

set +u
# shellcheck disable=SC1091
. ./source_soenv.sh
shopt -s expand_aliases

if test -z "${SOLARENV:-}"; then
    echo "SOLARENV is empty after sourcing the build environment" >&2
    exit 1
fi

build_dir() {
    local dir="$1"
    echo "===== build ${dir} ====="
    ( cd "$dir" && perl "${SOLARENV}/bin/build.pl" -P"${MAXPROCESS}" )
    if test -f "${dir}/prj/d.lst"; then
        echo "===== deliver ${dir} ====="
        ( cd "$dir" && perl "${SOLARENV}/bin/deliver.pl" )
    fi
}

build_dir soltools
build_dir stlport
build_dir libxmlsec

LIBDIR="${SOLARVERSION}/${INPATH}/lib${UPDMINOREXT:-}"
echo "===== verify ${LIBDIR} ====="
ls -l "${LIBDIR}"/libxmlsec1* || true
test -e "${LIBDIR}/libxmlsec1.a"
test -e "${LIBDIR}/libxmlsec1-nss.a"

ccache -s || true
echo "linux-xmlsec: ok"
