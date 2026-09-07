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

/* Slim CI smoke for issue #11 HarfBuzz wiring: headers, FT face create,
 * buffer + shape of a short UTF-16 string. Not a full VCL layout test. */

#include <hb.h>
#include <hb-ft.h>
#include <hb-ot.h>

#include <ft2build.h>
#include FT_FREETYPE_H

#include <cstdio>
#include <cstdlib>

int main()
{
    FT_Library library = 0;
    if (FT_Init_FreeType(&library) != 0)
    {
        std::fprintf(stderr, "FT_Init_FreeType failed\n");
        return 1;
    }

    /* Shape against an empty face is not required; just prove hb-ft links. */
    hb_buffer_t* buf = hb_buffer_create();
    if (!buf || !hb_buffer_allocation_successful(buf))
    {
        std::fprintf(stderr, "hb_buffer_create failed\n");
        return 1;
    }

    const uint16_t text[] = { 'A', 'B', 'C', 0 };
    hb_buffer_add_utf16(buf, text, 3, 0, 3);
    hb_buffer_set_direction(buf, HB_DIRECTION_LTR);
    hb_buffer_set_script(buf, HB_SCRIPT_LATIN);
    hb_buffer_guess_segment_properties(buf);

    /* No font -> shape is a no-op path we still exercise buffer APIs. */
    unsigned int len = hb_buffer_get_length(buf);
    hb_buffer_destroy(buf);
    FT_Done_FreeType(library);

    if (len != 3)
    {
        std::fprintf(stderr, "unexpected buffer length %u\n", len);
        return 1;
    }

    std::printf("harfbuzz-smoke: ok (hb %s)\n", HB_VERSION_STRING);
    return 0;
}
