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



#include <iostream>
#include <dbgoutsw.hxx>
#include "WW8Sttbf.hxx"
#include <cstdio>

namespace ww8
{
    WW8Struct::WW8Struct(SvStream& rSt, sal_uInt32 nPos, sal_uInt32 nSize)
    : mn_offset(0), mn_size(0)
    {
        // FIB lcb* values are signed and cast to sal_uInt32. A negative
        // length wraps to a huge alloc; also reject a blob past EOF.
        if (nSize == 0)
            return;

        rSt.Seek(nPos);
        const sal_uInt32 nTell = rSt.Tell();
        const sal_uInt32 nEnd = rSt.Seek(STREAM_SEEK_TO_END);
        rSt.Seek(nTell);
        if (nEnd < nTell || nSize > nEnd - nTell)
            return;

        mn_size = nSize;
        mp_data.reset(new sal_uInt8[nSize]);
        rSt.Read(mp_data.get(), nSize);
    }

    WW8Struct::WW8Struct(WW8Struct * pStruct, sal_uInt32 nPos, sal_uInt32 nSize)
    : mp_data(pStruct->mp_data), mn_offset(pStruct->mn_offset + nPos),
    mn_size(nSize)
    {
    }

    WW8Struct::~WW8Struct()
    {
    }

    sal_uInt8 WW8Struct::getU8(sal_uInt32 nOffset)
    {
        sal_uInt8 nResult = 0;

        if (nOffset < mn_size)
        {
            nResult = mp_data[mn_offset + nOffset];
        }

        return nResult;
    }

    ::rtl::OUString WW8Struct::getUString(sal_uInt32 nOffset,
                                          sal_uInt32 nCount)
    {
        ::rtl::OUString aResult;

        if (nCount > 0)
        {
            rtl_uString * pNew = 0;
            rtl_uString_newFromStr_WithLength
            (&pNew, reinterpret_cast<const sal_Unicode *>(&mp_data[mn_offset + nOffset]),
             nCount);

            aResult = rtl::OUString(pNew);
        }

#ifdef DEBUG
        char sBuffer[256];
        snprintf(sBuffer, sizeof(sBuffer), "offset=\"%" SAL_PRIuUINT32 "\" count=\"%" SAL_PRIuUINT32 "\"",
                 nOffset, nCount);
        ::std::clog << "<WW8Struct-getUString" << sBuffer << ">"
                    << dbg_out(aResult) << "</WW8Struct-getUString>"
                    << ::std::endl;
#endif

        return aResult;

    }

    ::rtl::OUString WW8Struct::getString(sal_uInt32 nOffset,
                                         sal_uInt32 nCount)
    {
        ::rtl::OUString aResult;

        if (nCount > 0)
        {
            ::rtl::OString aOStr(reinterpret_cast<const sal_Char *>(&mp_data[mn_offset + nOffset]),
                                 nCount);
            ::rtl::OUString aOUStr(rtl::OStringToOUString(aOStr, RTL_TEXTENCODING_ASCII_US));
            aResult = rtl::OUString(aOUStr);
        }

#ifdef DEBUG
        char sBuffer[256];
        snprintf(sBuffer, sizeof(sBuffer), "offset=\"%" SAL_PRIuUINT32 "\" count=\"%" SAL_PRIuUINT32 "\"",
                 nOffset, nCount);
        ::std::clog << "<WW8Struct-getString " << sBuffer << ">"
                    << dbg_out(aResult) << "</WW8Struct-getUString>"
                    << ::std::endl;
#endif

        return aResult;
    }
}
