#**************************************************************
#
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.
#
#**************************************************************



EXTERNAL_WARNINGS_NOT_ERRORS := TRUE

PRJ=.

PRJNAME=harfbuzz
TARGET=so_harfbuzz

# --- Settings -----------------------------------------------------

.INCLUDE :	settings.mk

.IF "$(SYSTEM_HARFBUZZ)" == "YES"

all:
        @echo "An already available installation of harfbuzz should exist on your system."
        @echo "Therefore the version provided here does not need to be built in addition."

.ELIF "$(ENABLE_HARFBUZZ)" != "TRUE"

all:
        @echo "Support for harfbuzz has been disabled.  Nothing to do."

.ELSE

# --- Files --------------------------------------------------------

TARFILE_NAME=harfbuzz-14.4.0
TARFILE_MD5=9bfe1a9767a6b3eb54a3c23f4cea129e

# Static lib with FreeType; no glib/cairo/icu/graphite2/tests/utils.
# Meson/ninja path is for Linux GCC/Clang (and compatible Unix toolchains).
CONFIGURE_ACTION=bash -c 'meson setup build --default-library=static -Dtests=disabled -Ddocs=disabled -Dutilities=disabled -Dfreetype=enabled -Dglib=disabled -Dcairo=disabled -Dicu=disabled -Dgraphite2=disabled -Dgobject=disabled'
CONFIGURE_FLAGS=

# Stage public headers (plus generated hb-features.h / hb-version.h) for deliver.
BUILD_ACTION=bash -c 'ninja -C build && mkdir -p stage/harfbuzz && cp -f src/hb.h src/hb-*.h build/src/hb-features.h build/src/hb-version.h stage/harfbuzz/'

OUT2LIB=build$/src$/libharfbuzz.a
OUTDIR2INC=stage$/harfbuzz

# --- Targets ------------------------------------------------------

.INCLUDE :	set_ext.mk
.INCLUDE :	target.mk
.INCLUDE :	tg_ext.mk

.ENDIF
