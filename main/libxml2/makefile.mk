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



PRJ=.

PRJNAME=libxml2
TARGET=so_libxml2

# --- Settings -----------------------------------------------------

.INCLUDE :	settings.mk

.IF "$(SYSTEM_LIBXML)" == "YES"
all:
	@echo "An already available installation of libxml should exist on your system."
	@echo "Therefore the version provided here does not need to be built in addition."
.ENDIF

# --- Files --------------------------------------------------------

LIBXML2VERSION=2.15.3

TARFILE_NAME=$(PRJNAME)-$(LIBXML2VERSION)
TARFILE_MD5=b7b0123654f86ebf630a5cbedaafdece

# xml2-config.in: rewrite prefix/cflags/libs for the solver tree.
# The three 2.9.10 git-hash backports (0e1a49c, 50f06b3, 7ffcd44) are upstream.
PATCH_FILES=libxml2-configure.patch

# libxml2-global-symbols: #i112480#: Solaris ld won't export non-listed symbols
#            libxml2-global-symbols.patch

# This is only for UNX environment now

.IF "$(OS)"=="WNT"
.IF "$(COM)"=="GCC"
xml2_CC=$(CC) -mthreads
.IF "$(MINGW_SHARED_GCCLIB)"=="YES"
xml2_CC+=-shared-libgcc
.ENDIF
xml2_LIBS=-lws2_32
.IF "$(MINGW_SHARED_GXXLIB)"=="YES"
xml2_LIBS+=$(MINGW_SHARED_LIBSTDCPP)
.ENDIF
CONFIGURE_DIR=
CONFIGURE_ACTION=.$/configure
CONFIGURE_FLAGS=--without-python --without-iconv --enable-static=no --without-debug --build=i586-pc-mingw32 --host=i586-pc-mingw32 lt_cv_cc_dll_switch="-shared" CC="$(xml2_CC)" LDFLAGS="-no-undefined -Wl,--enable-runtime-pseudo-reloc-v2 -L$(ILIB:s/;/ -L/)" LIBS="$(xml2_LIBS)" OBJDUMP=objdump
BUILD_ACTION=$(GNUMAKE)
BUILD_DIR=$(CONFIGURE_DIR)
.ELSE
# 2.15 removed win32/configure.js. MSVC uses CMake (NMake). Needs CMake 3.18+.
CONFIGURE_DIR=
CONFIGURE_ACTION=cmake
CONFIGURE_FLAGS=-G "NMake Makefiles" -DLIBXML2_WITH_PYTHON=OFF -DLIBXML2_WITH_ICONV=OFF -DLIBXML2_WITH_SAX1=ON -DLIBXML2_WITH_TESTS=OFF -DLIBXML2_WITH_ZLIB=OFF -DLIBXML2_WITH_PROGRAMS=ON
.IF "$(debug)"!=""
CONFIGURE_FLAGS+=-DCMAKE_BUILD_TYPE=Debug
.ELSE
CONFIGURE_FLAGS+=-DCMAKE_BUILD_TYPE=Release
.ENDIF
BUILD_ACTION=nmake
BUILD_DIR=$(CONFIGURE_DIR)
.ENDIF
.ELSE
.IF "$(SYSBASE)"!=""
xml2_CFLAGS+=-I$(SYSBASE)$/usr$/include
.IF "$(COMNAME)"=="sunpro5"
xml2_CFLAGS+=$(ARCH_FLAGS) $(C_RESTRICTIONFLAGS)
.ENDIF			# "$(COMNAME)"=="sunpro5"
xml2_LDFLAGS+=-L$(SYSBASE)$/usr$/lib
.ENDIF			# "$(SYSBASE)"!=""

# --without-iconv: no OpenOffice code calls iconv. The Windows build has
# passed iconv=no all along. Dropping it keeps UTF-8/UTF-16/ASCII/Latin-1
# and turns on libxml2's built-in ISO-8859-x tables; only encodings like
# Shift_JIS, Big5 and KOI8-R go. --enable-ipv6 and --without-lzma are gone
# in 2.15 (HTTP/LZMA modules were removed).
CONFIGURE_DIR=
.IF "$(OS)"=="OS2"
CONFIGURE_ACTION=sh .$/configure
CONFIGURE_FLAGS=--without-python --without-zlib --without-iconv --enable-static=yes --with-sax1=yes ADDCFLAGS="$(xml2_CFLAGS)" CFLAGS="$(EXTRA_CFLAGS)" LDFLAGS="$(xml2_LDFLAGS) $(EXTRA_LINKFLAGS)"
.ELIF "$(OS)"=="MACOSX"
# Community builds bundle a static libxml2 rather than a dylib -- see
# main/xmlsecurity/util/makefile.mk and main/forms/util/makefile.mk for
# the consumer side of this.
CONFIGURE_ACTION=.$/configure
CONFIGURE_FLAGS=--without-python --without-zlib --without-iconv --enable-static=yes --enable-shared=no --with-sax1=yes ADDCFLAGS="$(xml2_CFLAGS) $(EXTRA_CFLAGS)" LDFLAGS="$(xml2_LDFLAGS) $(EXTRA_LINKFLAGS)"
.ELSE
CONFIGURE_ACTION=.$/configure
CONFIGURE_FLAGS=--without-python --without-zlib --without-iconv --enable-static=no --with-sax1=yes ADDCFLAGS="$(xml2_CFLAGS) $(EXTRA_CFLAGS)" LDFLAGS="$(xml2_LDFLAGS) $(EXTRA_LINKFLAGS)"
.ENDIF
BUILD_ACTION=$(GNUMAKE)
BUILD_FLAGS+= -j$(EXTMAXPROCESS)
BUILD_DIR=$(CONFIGURE_DIR)
.ENDIF


OUTDIR2INC=include$/libxml

.IF "$(OS)"=="MACOSX"
EXTRPATH=URELIB
OUT2LIB+=.libs$/libxml2.a
OUT2BIN+=.libs$/xmllint
OUT2BIN+=xml2-config
.ELIF "$(OS)"=="WNT"
.IF "$(COM)"=="GCC"
OUT2LIB+=.libs$/libxml2*.a
OUT2BIN+=.libs$/libxml2*.dll
OUT2BIN+=.libs$/xmllint.exe
OUT2BIN+=xml2-config
.ELSE
OUT2LIB+=libxml2*.lib
OUT2BIN+=libxml2*.dll
OUT2BIN+=xmllint.exe
OUT2BIN+=xml2-config
.ENDIF
.ELSE
OUT2LIB+=.libs$/libxml2.so*
OUT2BIN+=.libs$/xmllint
OUT2BIN+=xml2-config
.ENDIF

# --- Targets ------------------------------------------------------

.INCLUDE : set_ext.mk
.INCLUDE : target.mk
.INCLUDE : tg_ext.mk
