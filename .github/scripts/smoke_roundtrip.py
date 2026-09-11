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

"""Headless round-trip smoke for an installed office (roadmap Phase 0).

The office has no -convert-to switch, so this starts soffice headless with
a UNO pipe, connects with pyuno, and for each input loads the document,
stores it in the native ODF format, and finally exports the fresh ODT to
PDF. Any exception or a missing output fails the run.

Usage: python smoke_roundtrip.py <office_dir> <in_dir> <out_dir>
Run it with <office_dir>/program/python (or with PYTHONPATH pointing at
<office_dir>/program and URE_BOOTSTRAP set) so that `import uno` works.
"""

import os
import subprocess
import sys
import time

import uno  # noqa: E402  (needs the office's python environment)
from com.sun.star.beans import PropertyValue  # noqa: E402
from com.sun.star.connection import NoConnectException  # noqa: E402

CONNECT_TIMEOUT_S = 240
TERMINATE_TIMEOUT_S = 60


def props(**kwargs):
    out = []
    for name, value in kwargs.items():
        p = PropertyValue()
        p.Name = name
        p.Value = value
        out.append(p)
    return tuple(out)


def file_url(path):
    return uno.systemPathToFileUrl(os.path.abspath(path))


def start_office(office_dir, pipe_name):
    soffice = os.path.join(office_dir, "program", "soffice")
    cmd = [
        soffice,
        "-headless",
        "-invisible",
        "-nologo",
        "-norestore",
        "-nofirststartwizard",
        "-accept=pipe,name=%s;urp;StarOffice.ComponentContext" % pipe_name,
    ]
    print("start:", " ".join(cmd), flush=True)
    return subprocess.Popen(cmd)


def connect(pipe_name, proc):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    url = "uno:pipe,name=%s;urp;StarOffice.ComponentContext" % pipe_name
    deadline = time.time() + CONNECT_TIMEOUT_S
    while True:
        if proc.poll() is not None:
            raise RuntimeError("soffice exited early with code %s" % proc.returncode)
        try:
            ctx = resolver.resolve(url)
            print("connected after wait", flush=True)
            return ctx
        except NoConnectException:
            if time.time() > deadline:
                raise RuntimeError("could not connect to soffice within %ss" % CONNECT_TIMEOUT_S)
            time.sleep(1)


def round_trip(desktop, src, dst, store_filter, **load_props):
    print("load  %s" % src, flush=True)
    load = props(Hidden=True, **load_props)
    doc = desktop.loadComponentFromURL(file_url(src), "_blank", 0, load)
    if doc is None:
        raise RuntimeError("loadComponentFromURL returned None for %s" % src)
    try:
        print("store %s (%s)" % (dst, store_filter), flush=True)
        doc.storeToURL(file_url(dst), props(FilterName=store_filter, Overwrite=True))
    finally:
        doc.close(True)
    size = os.path.getsize(dst) if os.path.exists(dst) else 0
    if size <= 0:
        raise RuntimeError("missing or empty output: %s" % dst)
    print("ok    %s (%d bytes)" % (dst, size), flush=True)


def main(argv):
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    office_dir, in_dir, out_dir = argv[1:]
    os.makedirs(out_dir, exist_ok=True)
    pipe_name = "work-smoke-%d" % os.getpid()

    proc = start_office(office_dir, pipe_name)
    rc = 1
    try:
        ctx = connect(pipe_name, proc)
        desktop = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)

        # Write: plain text in, ODT out.
        round_trip(desktop, os.path.join(in_dir, "write.txt"),
                   os.path.join(out_dir, "write.odt"), "writer8")
        # Accounts: CSV in with explicit import options (comma, quote,
        # UTF-8, from line 1), ODS out.
        round_trip(desktop, os.path.join(in_dir, "accounts.csv"),
                   os.path.join(out_dir, "accounts.ods"), "calc8",
                   FilterName="Text - txt - csv (StarCalc)",
                   FilterOptions="44,34,76,1,,0,false,true,false,false")
        # Show: a layout template opened as a new presentation, ODP out.
        round_trip(desktop, os.path.join(in_dir, "show.otp"),
                   os.path.join(out_dir, "show.odp"), "impress8",
                   AsTemplate=True)
        # Re-open what the office just wrote, and export it.
        round_trip(desktop, os.path.join(out_dir, "write.odt"),
                   os.path.join(out_dir, "write.pdf"), "writer_pdf_Export")

        print("terminate", flush=True)
        try:
            desktop.terminate()
        except Exception as e:  # DisposedException on a clean exit is fine
            print("terminate raised %s" % type(e).__name__, flush=True)
        rc = 0
    finally:
        deadline = time.time() + TERMINATE_TIMEOUT_S
        while proc.poll() is None and time.time() < deadline:
            time.sleep(1)
        if proc.poll() is None:
            print("soffice did not exit; killing", flush=True)
            proc.kill()
            proc.wait()
            rc = rc or 1
        print("soffice exit code %s" % proc.returncode, flush=True)
        if proc.returncode not in (0, None) and rc == 0:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
