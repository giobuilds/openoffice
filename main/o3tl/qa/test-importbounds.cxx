/**************************************************************
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 *************************************************************/



#include "preextstl.h"
#include "gtest/gtest.h"
#include "postextstl.h"

#include <cstring>
#include <map>

// Spec of importer bounds. Keep in sync with:
//   main/sw/source/filter/ww8/ww8scan.cxx      (WW8 FKP)
//   main/filter/source/graphicfilter/icgm/class7.cxx
//   main/filter/source/graphicfilter/icgm/class4.cxx    (CGM polygon counts)
//   main/filter/source/graphicfilter/icgm/outact.cxx    (CGM figure scratch)
//   main/filter/source/graphicfilter/icgm/bitmap.cxx    (CGM cell-array size)
//   main/filter/source/graphicfilter/itiff/itiff.cxx
//   main/filter/source/graphicfilter/iras/iras.cxx     (RAS dimensions)
//   main/filter/source/graphicfilter/ipbm/ipbm.cxx      (PBM dimensions)
//   main/svtools/source/filter/ixbm/xbmread.cxx        (XBM dimensions)
//   main/svtools/source/filter/ixpm/xpmread.cxx        (XPM dimensions)
//   main/filter/source/graphicfilter/ieps/ieps.cxx     (EPS preview/bbox)
//   main/svtools/source/filter/igif/gifread.cxx        (GIF dimensions)
//   main/filter/source/graphicfilter/ipict/ipict.cxx   (PICT dimensions)
//   main/filter/source/graphicfilter/ipcx/ipcx.cxx     (PCX dimensions)
//   main/filter/source/graphicfilter/itga/itga.cxx     (TGA dimensions)
//   main/sw/source/filter/ww8/ww8par2.cxx              (WW8 SPRM length)
//   main/sw/source/filter/ww8/ww8scan.hxx              (WW8 SPRM walk)
//   main/filter/source/graphicfilter/idxf/dxf2mtf.cxx  (DXF POLYLINE)
//   main/sc/source/core/tool/compiler.cxx              (formula FunctionStack)
//   main/sc/source/core/tool/chgtrack.cxx              (tracked-changes ids)

namespace {

bool ww8FkpBxOffsetOk(unsigned nIMax, unsigned nIdx, unsigned nItemSize)
{
    if (nItemSize == 0)
        return false;
    unsigned nOff = (nIMax + 1u) * 4u + nIdx * nItemSize;
    return nOff < 511u;
}

unsigned ww8FkpClipLen(unsigned nOffset, unsigned nLen)
{
    if (nOffset >= 512u)
        return 0;
    unsigned nAvail = 512u - nOffset;
    return nLen < nAvail ? nLen : nAvail;
}

// Remaining bytes of the CGM element; 0 means missing NUL (hard fail).
unsigned cgmBoundedCStrLen(const char* p, unsigned nRemain)
{
    if (!p || nRemain == 0)
        return 0;
    for (unsigned i = 0; i < nRemain; ++i)
    {
        if (p[i] == 0)
            return i + 1;
    }
    return 0;
}

enum { TIFF_MAX_PIXELS = 64u * 1024u * 1024u };

bool tiffDimensionsOk(unsigned long nWidth, unsigned long nHeight)
{
    if (nWidth == 0 || nHeight == 0)
        return false;
    const unsigned long nMaxDim = 0x7FFFFFFFul / 32u;
    if (nWidth > nMaxDim || nHeight > nMaxDim)
        return false;
    if (nHeight > static_cast<unsigned long>(TIFF_MAX_PIXELS) / nWidth)
        return false;
    return true;
}

bool tiffRowSize(unsigned long nWidth, unsigned long nSamples,
    unsigned long nPlanes, unsigned long nBits, unsigned long* pBytes)
{
    if (!pBytes || nPlanes == 0 || nBits == 0 || nBits > 32)
        return false;
    unsigned long long nRow = static_cast<unsigned long long>(nWidth)
        * nSamples / nPlanes * nBits;
    nRow = (nRow + 7) >> 3;
    if (nRow == 0 || nRow > 0x7FFFFFFFull / 4)
        return false;
    *pBytes = static_cast<unsigned long>(nRow);
    return true;
}

}

TEST(ImportBounds, Ww8FkpRejectsCrunThatDoesNotFitPage)
{
    // CHP BX is 1 byte. crun=127 => FC array is 512 bytes, BX starts at 512.
    EXPECT_FALSE(ww8FkpBxOffsetOk(127, 0, 1));
    EXPECT_FALSE(ww8FkpBxOffsetOk(255, 0, 1));

    // crun=101 is the classic Word CHP max: (101+1)*4 + 101*1 = 509 < 511.
    EXPECT_TRUE(ww8FkpBxOffsetOk(101, 0, 1));
    EXPECT_TRUE(ww8FkpBxOffsetOk(101, 100, 1));

    // PAP BX is 13 bytes; fewer runs fit. nIdx=0 of crun=40 still
    // starts at (40+1)*4 = 164. Overflow is at the last run:
    // (40+1)*4 + 39*13 = 671 >= 511.
    EXPECT_TRUE(ww8FkpBxOffsetOk(20, 0, 13));
    EXPECT_TRUE(ww8FkpBxOffsetOk(20, 19, 13));
    EXPECT_TRUE(ww8FkpBxOffsetOk(40, 0, 13));
    EXPECT_FALSE(ww8FkpBxOffsetOk(40, 39, 13));
}

TEST(ImportBounds, Ww8FkpClipsOffsetAndLengthToPage)
{
    EXPECT_EQ(0u, ww8FkpClipLen(512, 10));
    EXPECT_EQ(0u, ww8FkpClipLen(600, 1));
    EXPECT_EQ(1u, ww8FkpClipLen(511, 20));
    EXPECT_EQ(4u, ww8FkpClipLen(508, 4));
    EXPECT_EQ(2u, ww8FkpClipLen(510, 8));
}

TEST(ImportBounds, CgmStringRequiresNulWithinRemainingElement)
{
    const char aOk[] = "hello";
    EXPECT_EQ(6u, cgmBoundedCStrLen(aOk, sizeof aOk));

    char aNoNul[8];
    std::memset(aNoNul, 'A', sizeof aNoNul);
    EXPECT_EQ(0u, cgmBoundedCStrLen(aNoNul, sizeof aNoNul));

    char aEarly[8];
    std::memset(aEarly, 'B', sizeof aEarly);
    aEarly[2] = 0;
    EXPECT_EQ(3u, cgmBoundedCStrLen(aEarly, sizeof aEarly));

    EXPECT_EQ(0u, cgmBoundedCStrLen(aOk, 0));
}

TEST(ImportBounds, TiffDimensionsUseCheckedMultiplyAndCap)
{
    EXPECT_FALSE(tiffDimensionsOk(0, 10));
    EXPECT_FALSE(tiffDimensionsOk(10, 0));
    EXPECT_TRUE(tiffDimensionsOk(100, 100));
    EXPECT_TRUE(tiffDimensionsOk(8192, 8192));
    // 65536^2 exceeds both the 64M pixel cap and INT32/32.
    EXPECT_FALSE(tiffDimensionsOk(65536, 65536));
    EXPECT_FALSE(tiffDimensionsOk(0xFFFFFFFFul, 0xFFFFFFFFul));
    EXPECT_FALSE(tiffDimensionsOk(1, 0xFFFFFFFFul));
}

// RAS and PBM use the same Size()/64M cap as TIFF.

TEST(ImportBounds, RasPbmDimensionsMatchTiffCap)
{
    EXPECT_TRUE(tiffDimensionsOk(640, 480));
    EXPECT_FALSE(tiffDimensionsOk(0, 480));
    EXPECT_FALSE(tiffDimensionsOk(65536, 65536));
}

namespace {

bool pbmAsciiMultiplyOk32(unsigned nCur, unsigned nDigit, unsigned* pNew)
{
    unsigned nNew = nCur * 10 + nDigit;
    if (nCur != 0 && nNew / 10 != nCur)
        return false;
    *pNew = nNew;
    return true;
}

}

TEST(ImportBounds, PbmAsciiWidthRejectsUnsignedWrap)
{
    unsigned nNew = 0;
    EXPECT_TRUE(pbmAsciiMultiplyOk32(0, 6, &nNew));
    EXPECT_EQ(6u, nNew);
    EXPECT_TRUE(pbmAsciiMultiplyOk32(12, 3, &nNew));
    EXPECT_EQ(123u, nNew);

    // 0xFFFFFFFF * 10 wraps a 32-bit unsigned width accumulator.
    EXPECT_FALSE(pbmAsciiMultiplyOk32(0xFFFFFFFFu, 0, &nNew));
}

TEST(ImportBounds, TiffRowSizeRejectsOverflowAndZeroPlanes)
{
    unsigned long nBytes = 0;
    EXPECT_TRUE(tiffRowSize(8, 1, 1, 1, &nBytes));
    EXPECT_EQ(1UL, nBytes);

    EXPECT_TRUE(tiffRowSize(30, 1, 1, 1, &nBytes));
    EXPECT_EQ(4UL, nBytes); // 30 bits -> 4 bytes

    EXPECT_FALSE(tiffRowSize(100, 1, 0, 8, &nBytes));
    EXPECT_FALSE(tiffRowSize(0xFFFFFFFFul, 4, 1, 32, &nBytes));
}

// Spec of DXF POLYLINE VERTEX count vs tools::Polygon (CVE-2026-6039 class).
// Keep in sync with DrawPolyLineEntity in
//   main/filter/source/graphicfilter/idxf/dxf2mtf.cxx

namespace {

bool dxfPolylineFitsPolygon(unsigned nVertices)
{
    return nVertices >= 2 && nVertices <= 0xFFFFu;
}

unsigned dxfPolylineCountWrapsTo(unsigned nVertices)
{
    return static_cast<unsigned short>(nVertices);
}

}

TEST(ImportBounds, DxfPolylineRejectsCountThatDoesNotFitPolygon)
{
    EXPECT_FALSE(dxfPolylineFitsPolygon(0));
    EXPECT_FALSE(dxfPolylineFitsPolygon(1));
    EXPECT_TRUE(dxfPolylineFitsPolygon(2));
    EXPECT_TRUE(dxfPolylineFitsPolygon(0xFFFF));
    EXPECT_FALSE(dxfPolylineFitsPolygon(0x10000));
    EXPECT_FALSE(dxfPolylineFitsPolygon(0x10001));

    // 16-bit wrap of the old nPolySize++ counter: 65536 -> 0, 65538 -> 2.
    EXPECT_EQ(0u, dxfPolylineCountWrapsTo(0x10000));
    EXPECT_EQ(2u, dxfPolylineCountWrapsTo(0x10002));
}

// Spec of CGM polyline/polygon/polybezier vs tools::Polygon (CVE-2026-6039
// class). Polygon Set fills a 0x4000-point scratch buffer.
// Keep in sync with main/filter/source/graphicfilter/icgm/class4.cxx
// Figure polylines fill a 0x2000-point scratch buffer in
//   main/filter/source/graphicfilter/icgm/outact.cxx

namespace {

bool cgmPointsFitPolygon(unsigned nPoints)
{
    return nPoints <= 0xFFFFu;
}

bool cgmPolygonSetFitsScratch(unsigned nPoints)
{
    return nPoints < 0x4000u;
}

unsigned cgmPointCount(unsigned nElementSize, unsigned nPointSize)
{
    if (nPointSize == 0)
        return 0xFFFFFFFFu;
    return nElementSize / nPointSize;
}

}

TEST(ImportBounds, CgmPolygonRejectsCountThatDoesNotFitPolygon)
{
    EXPECT_TRUE(cgmPointsFitPolygon(0));
    EXPECT_TRUE(cgmPointsFitPolygon(2));
    EXPECT_TRUE(cgmPointsFitPolygon(0xFFFF));
    EXPECT_FALSE(cgmPointsFitPolygon(0x10000));

    EXPECT_TRUE(cgmPolygonSetFitsScratch(0));
    EXPECT_TRUE(cgmPolygonSetFitsScratch(0x3FFF));
    EXPECT_FALSE(cgmPolygonSetFitsScratch(0x4000));

    // Zero VDC precision: point size 0. Do not divide.
    EXPECT_EQ(0xFFFFFFFFu, cgmPointCount(100, 0));
    EXPECT_EQ(25u, cgmPointCount(100, 4));
}

namespace {

enum { CGM_FIGURE_MAX = 0x2000 };

bool cgmFigureFitsScratch(unsigned nIndex, unsigned nPoints)
{
    if (nPoints > CGM_FIGURE_MAX)
        return false;
    return nIndex + nPoints <= CGM_FIGURE_MAX;
}

}

TEST(ImportBounds, CgmFigureRejectsPolylineThatDoesNotFitScratch)
{
    EXPECT_TRUE(cgmFigureFitsScratch(0, 2));
    EXPECT_TRUE(cgmFigureFitsScratch(0, 0x2000));
    EXPECT_FALSE(cgmFigureFitsScratch(0, 0x2001));
    EXPECT_TRUE(cgmFigureFitsScratch(0x1FFF, 1));
    EXPECT_FALSE(cgmFigureFitsScratch(0x1FFF, 2));
    EXPECT_FALSE(cgmFigureFitsScratch(0x1000, 0x1001));
}

namespace {

// Old CGM cell-array check was (nX || nY) == 0, which is true only if both
// are zero. A zero-width, huge-height cell array slipped through.
bool cgmBitmapOldZeroCheck(unsigned nX, unsigned nY)
{
    return (nX || nY) == 0;
}

bool cgmBitmapDimsOk(unsigned nX, unsigned nY)
{
    if (nX == 0 || nY == 0)
        return false;
    return tiffDimensionsOk(nX, nY);
}

}

TEST(ImportBounds, CgmBitmapRejectsZeroOrHugeDimensions)
{
    EXPECT_TRUE(cgmBitmapOldZeroCheck(0, 0));
    EXPECT_FALSE(cgmBitmapOldZeroCheck(0, 1000000));
    EXPECT_FALSE(cgmBitmapDimsOk(0, 1000000));
    EXPECT_FALSE(cgmBitmapDimsOk(1000000, 0));
    EXPECT_TRUE(cgmBitmapDimsOk(320, 200));
    EXPECT_FALSE(cgmBitmapDimsOk(65536, 65536));
}

TEST(ImportBounds, XbmXpmDimensionsMatchTiffCap)
{
    EXPECT_TRUE(tiffDimensionsOk(16, 16));
    EXPECT_TRUE(tiffDimensionsOk(1024, 768));
    EXPECT_FALSE(tiffDimensionsOk(65536, 65536));
}

namespace {

bool xpmWidthTimesCppOk(unsigned nWidth, unsigned nCpp, unsigned nBuf)
{
    if (nCpp == 0)
        return false;
    if (nWidth > 0xFFFFFFFFu / nCpp)
        return false;
    return nWidth * nCpp < nBuf;
}

}

TEST(ImportBounds, XpmWidthTimesCppRejectsWrap)
{
    EXPECT_TRUE(xpmWidthTimesCppOk(8, 1, 0x8000));
    EXPECT_FALSE(xpmWidthTimesCppOk(0x8000, 1, 0x8000));
    EXPECT_FALSE(xpmWidthTimesCppOk(0xFFFFFFFFu, 4, 0x8000));
    EXPECT_FALSE(xpmWidthTimesCppOk(100, 0, 0x8000));
}

namespace {

bool epsDimsOk(long nWidth, long nHeight)
{
    if (nWidth <= 0 || nHeight <= 0)
        return false;
    return tiffDimensionsOk(static_cast<unsigned long>(nWidth),
        static_cast<unsigned long>(nHeight));
}

bool epsGetNumberDigitOk(long nCur, unsigned nDigit, long nMax)
{
    return nCur <= (nMax - static_cast<long>(nDigit)) / 10;
}

}

TEST(ImportBounds, EpsPreviewRejectsNonPositiveOrHugeDims)
{
    EXPECT_FALSE(epsDimsOk(0, 100));
    EXPECT_FALSE(epsDimsOk(-1, 100));
    EXPECT_FALSE(epsDimsOk(100, -8));
    EXPECT_TRUE(epsDimsOk(100, 100));
    EXPECT_FALSE(epsDimsOk(65536, 65536));

    EXPECT_TRUE(epsGetNumberDigitOk(12, 3, 0x7FFFFFFF));
    EXPECT_FALSE(epsGetNumberDigitOk(0x7FFFFFFF, 0, 0x7FFFFFFF));
}

TEST(ImportBounds, Gif16BitSidesStillExceedPixelCap)
{
    // GIF width/height are u16, so 65535 is a legal header value.
    EXPECT_TRUE(tiffDimensionsOk(65535, 1));
    EXPECT_TRUE(tiffDimensionsOk(8192, 8192));
    EXPECT_FALSE(tiffDimensionsOk(65535, 65535));
}

TEST(ImportBounds, PictPcxTga16BitSidesStillExceedPixelCap)
{
    EXPECT_TRUE(tiffDimensionsOk(640, 480));
    EXPECT_FALSE(tiffDimensionsOk(0, 480));
    EXPECT_FALSE(tiffDimensionsOk(65535, 65535));
    // PCX nMax-nMin+1 can be 65536.
    EXPECT_FALSE(tiffDimensionsOk(65536, 65536));
}

namespace {

bool ww8SprmLenOk(int nLen)
{
    return nLen > 0;
}

unsigned ww8SprmAllocWrapsTo(int nLen)
{
    return static_cast<unsigned>(nLen);
}

}

TEST(ImportBounds, Ww8SprmRejectsNonPositiveLength)
{
    EXPECT_FALSE(ww8SprmLenOk(0));
    EXPECT_FALSE(ww8SprmLenOk(-1));
    EXPECT_TRUE(ww8SprmLenOk(1));
    EXPECT_TRUE(ww8SprmLenOk(32767));

    // short -1 as size_t on a 32-bit size is 0xFFFFFFFF.
    EXPECT_EQ(static_cast<unsigned>(-1), ww8SprmAllocWrapsTo(-1));
}

namespace {

bool ww8SprmFitsRemain(unsigned nSprm, unsigned nRemain)
{
    return nSprm != 0 && nSprm <= nRemain;
}

}

TEST(ImportBounds, Ww8SprmWalkStopsOnZeroOrOversize)
{
    EXPECT_TRUE(ww8SprmFitsRemain(1, 10));
    EXPECT_TRUE(ww8SprmFitsRemain(10, 10));
    EXPECT_FALSE(ww8SprmFitsRemain(0, 10));
    EXPECT_FALSE(ww8SprmFitsRemain(11, 10));
}

// Spec of ScCompiler::CompileString FunctionStack (CVE-2026-8357).
// Keep in sync with main/sc/source/core/tool/compiler.cxx

namespace {

unsigned formulaFunctionStackSlots(unsigned nFormulaLen, unsigned nAlloc)
{
    if (nFormulaLen >= nAlloc)
        return nFormulaLen + 1;
    return nAlloc;
}

}

TEST(ImportBounds, FormulaFunctionStackHasRoomForAllOpens)
{
    const unsigned nAlloc = 512;
    // Sentinel at [0], then one slot per open token. L opens need L+1.
    EXPECT_EQ(512u, formulaFunctionStackSlots(511, nAlloc));
    EXPECT_EQ(513u, formulaFunctionStackSlots(512, nAlloc));
    EXPECT_EQ(514u, formulaFunctionStackSlots(513, nAlloc));
    EXPECT_GE(formulaFunctionStackSlots(512, nAlloc), 512u + 1u);
}

// Spec of ScChangeTrack::AppendLoaded (CVE-2026-8358).
// Keep in sync with:
//   main/sc/source/core/tool/chgtrack.cxx
//   main/sc/source/filter/xml/XMLChangeTrackingImportHelper.cxx
// tools::Table::Insert returns false when the action number is already in
// the table. AppendLoaded must honor that so SetContentDependencies never
// static_casts a smaller ScChangeActionIns via GetAction.

namespace {

enum { CAT_INSERT = 1, CAT_CONTENT = 2 };

bool changeTrackAppendLoaded(std::map<unsigned, int>& rTable,
    unsigned nAction, int eType)
{
    if (rTable.find(nAction) != rTable.end())
        return false;
    rTable[nAction] = eType;
    return true;
}

}

TEST(ImportBounds, ChangeTrackRejectsDuplicateActionNumber)
{
    std::map<unsigned, int> aTable;
    EXPECT_TRUE(changeTrackAppendLoaded(aTable, 1, CAT_INSERT));
    EXPECT_FALSE(changeTrackAppendLoaded(aTable, 1, CAT_CONTENT));
    EXPECT_EQ(1u, static_cast<unsigned>(aTable.size()));
    EXPECT_EQ(CAT_INSERT, aTable[1]);

    EXPECT_TRUE(changeTrackAppendLoaded(aTable, 2, CAT_CONTENT));
    EXPECT_EQ(2u, static_cast<unsigned>(aTable.size()));
    EXPECT_EQ(CAT_CONTENT, aTable[2]);
}
