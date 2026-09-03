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

# Slim Linux CI (issue #8): configure, bootstrap, compile sal, run
# gbuild GoogleTests for o3tl and salhelper. Not a full office build.

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
    --enable-unit-tests \
    --with-system-boost \
    --with-system-python \
    --with-dmake-url=https://github.com/jimjag/dmake/archive/v4.13.1/dmake-4.13.1.tar.gz

./bootstrap

# Env.Set.sh uses aliases and can reference unset vars. bootstrap is a
# child process, so this shell still needs the environment.
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
}

# sal/util is the library. Module deps pull xml2cmp, soltools, gtest, boost.
build_dir sal/util

# gbuild modules: default goal is allandcheck (compile + run GoogleTest).
build_dir o3tl
build_dir salhelper

# A few sal dmake gtests (APP1TEST=enabled) that do not need a running office.
build_dir sal/qa/rtl/digest
build_dir sal/qa/rtl/crc32
build_dir sal/qa/ByteSequence

ccache -s || true
echo "linux-sal-gtest: ok"
