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

#include <rtl/ustrbuf.hxx>
#include <rtl/ustring.hxx>

// Spec of Base CSV number copy in issue #11 / CVE-2025-64406 leftover.
// Keep in sync with lcl_NormalizeCsvNumber in
//   main/connectivity/source/drivers/flat/ETable.cxx

namespace {

::rtl::OUString normalizeCsvNumber(
        const ::rtl::OUString& rStr,
        sal_Unicode cDecimalDelimiter,
        sal_Unicode cThousandDelimiter,
        bool bInteger )
{
    if ( bInteger )
    {
        if ( !cThousandDelimiter )
            return rStr;
        ::rtl::OUStringBuffer aBuf( rStr.getLength() );
        for ( sal_Int32 j = 0; j < rStr.getLength(); ++j )
        {
            const sal_Unicode cChar = rStr[j];
            if ( cChar != cThousandDelimiter )
                aBuf.append( cChar );
        }
        return aBuf.makeStringAndClear();
    }

    ::rtl::OUStringBuffer aBuf( rStr.getLength() );
    for ( sal_Int32 j = 0; j < rStr.getLength(); ++j )
    {
        const sal_Unicode cChar = rStr[j];
        if ( cDecimalDelimiter && cChar == cDecimalDelimiter )
            aBuf.append( sal_Unicode( '.' ) );
        else if ( cChar == '.' )
            continue;
        else if ( cThousandDelimiter && cChar == cThousandDelimiter )
            ;
        else
            aBuf.append( cChar );
    }
    return aBuf.makeStringAndClear();
}

}

TEST(CsvNumber, SixteenBitAllocLengthWraps)
{
    // String::AllocBuffer takes xub_StrLen (16-bit). A 32-bit cell of
    // 65536 characters truncated the allocation to 0 while the copy loop
    // still wrote the full length.
    EXPECT_EQ( 0u, static_cast<unsigned short>( 65535u + 1u ) );
    EXPECT_EQ( 1u, static_cast<unsigned short>( 65536u + 1u ) );
}

TEST(CsvNumber, DecimalAndThousandSeparators)
{
    const sal_Unicode cDec = ',';
    const sal_Unicode cThou = '.';
    EXPECT_EQ(
        ::rtl::OUString( RTL_CONSTASCII_USTRINGPARAM( "1234.56" ) ),
        normalizeCsvNumber(
            ::rtl::OUString( RTL_CONSTASCII_USTRINGPARAM( "1.234,56" ) ),
            cDec, cThou, false ) );
    EXPECT_EQ(
        ::rtl::OUString( RTL_CONSTASCII_USTRINGPARAM( "1234" ) ),
        normalizeCsvNumber(
            ::rtl::OUString( RTL_CONSTASCII_USTRINGPARAM( "1.234" ) ),
            cDec, cThou, true ) );
}

TEST(CsvNumber, LongCellKeepsFullLength)
{
    // 70000 digits would wrap a 16-bit AllocBuffer (70000 & 0xFFFF == 4464).
    const sal_Int32 nLen = 70000;
    ::rtl::OUStringBuffer aIn( nLen );
    for ( sal_Int32 i = 0; i < nLen; ++i )
        aIn.append( sal_Unicode( '1' ) );
    const ::rtl::OUString aOut = normalizeCsvNumber(
            aIn.makeStringAndClear(), ',', '.', false );
    EXPECT_EQ( nLen, aOut.getLength() );
    EXPECT_EQ( sal_Unicode( '1' ), aOut[0] );
    EXPECT_EQ( sal_Unicode( '1' ), aOut[nLen - 1] );
}
