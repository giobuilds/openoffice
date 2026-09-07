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

# Slim Linux CI (issue #11): configure with system HarfBuzz, compile a
# smoke that exercises the HbLayoutEngine translation unit flags, and
# optionally build the bundled harfbuzz module. Not a full office build.

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
pkg-config --modversion harfbuzz
pkg-config --modversion freetype2
ccache -s || true

autoconf

./configure \
    --without-java \
    --without-junit \
    --disable-odk \
    --disable-epm \
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
    --with-system-boost \
    --with-system-python \
    --with-system-expat \
    --with-system-zlib \
    --with-system-openssl \
    --with-system-curl \
    --with-system-jpeg \
    --with-system-libxml \
    --with-system-libxslt \
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

echo "ENABLE_HARFBUZZ=${ENABLE_HARFBUZZ:-}"
echo "SYSTEM_HARFBUZZ=${SYSTEM_HARFBUZZ:-}"
echo "HARFBUZZ_CFLAGS=${HARFBUZZ_CFLAGS:-}"
echo "HARFBUZZ_LIBS=${HARFBUZZ_LIBS:-}"

test "${ENABLE_HARFBUZZ}" = "TRUE"
test "${SYSTEM_HARFBUZZ}" = "YES"

# Compile smoke: HarfBuzz + FreeType + the same includes the layout engine needs.
SMOKE="${ROOT}/.github/scripts/harfbuzz-smoke.cxx"
"${CXX}" -std=c++11 -c -o /tmp/harfbuzz-smoke.o \
    ${HARFBUZZ_CFLAGS} $(pkg-config --cflags freetype2) \
    -DENABLE_HARFBUZZ \
    "${SMOKE}"
"${CXX}" -o /tmp/harfbuzz-smoke /tmp/harfbuzz-smoke.o \
    ${HARFBUZZ_LIBS} $(pkg-config --libs freetype2)
/tmp/harfbuzz-smoke

# Also build the bundled module (meson) to prove the internal path.
# Reconfigure is heavy; invoke meson directly on the tarball like the module.
HB_TAR="${ROOT}/ext_sources/9bfe1a9767a6b3eb54a3c23f4cea129e-harfbuzz-14.4.0.tar.xz"
test -f "${HB_TAR}"
HB_BUILD="${ROOT}/.hb-ci-build"
rm -rf "${HB_BUILD}"
mkdir -p "${HB_BUILD}"
tar -xJf "${HB_TAR}" -C "${HB_BUILD}"
(
  cd "${HB_BUILD}/harfbuzz-14.4.0"
  meson setup build --default-library=static \
    -Dtests=disabled -Ddocs=disabled -Dutilities=disabled \
    -Dfreetype=enabled -Dglib=disabled -Dcairo=disabled \
    -Dicu=disabled -Dgraphite2=disabled -Dgobject=disabled
  ninja -C build
  test -f build/src/libharfbuzz.a
  ls -l build/src/libharfbuzz.a
)

ccache -s || true
echo "linux-harfbuzz: ok"
