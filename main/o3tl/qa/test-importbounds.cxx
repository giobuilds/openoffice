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

// Spec of the three importer bounds in issue #2. Keep in sync with:
//   main/sw/source/filter/ww8/ww8scan.cxx      (WW8 FKP)
//   main/filter/source/graphicfilter/icgm/class7.cxx
//   main/filter/source/graphicfilter/itiff/itiff.cxx

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

    // PAP BX is 13 bytes; fewer runs fit.
    EXPECT_TRUE(ww8FkpBxOffsetOk(20, 0, 13));
    EXPECT_FALSE(ww8FkpBxOffsetOk(40, 0, 13));
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
