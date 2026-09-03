<!--
 Licensed to the Apache Software Foundation (ASF) under one
 or more contributor license agreements.  See the NOTICE file
 distributed with this work for additional information
 regarding copyright ownership.  The ASF licenses this file
 to you under the Apache License, Version 2.0 (the
 "License"); you may not use this file except in compliance
 with the License.  You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing,
 software distributed under the License is distributed on an
 "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 KIND, either express or implied.  See the License for the
 specific language governing permissions and limitations
 under the License.
-->

# Security Policy

This repository is a hardening fork of Apache OpenOffice. It is not an
official Apache Software Foundation release.

## Reporting a vulnerability

Report undisclosed vulnerabilities **privately**. Do not open a public GitHub
issue, and do not attach exploit proofs of concept against unfixed parser bugs.

### This fork

Use [GitHub private vulnerability reporting](https://github.com/giobuilds/openoffice/security/advisories/new)
on this repository. That is the channel this fork monitors.

Include:

- Affected version or commit (for example a `trunk` SHA)
- Impact (code execution, file disclosure, denial of service, and so on)
- How to reproduce, without a public exploit payload
- Whether the issue is already public

### Apache OpenOffice (upstream)

If the issue also affects Apache OpenOffice, report it to the project's
private security list: [security@openoffice.apache.org](mailto:security@openoffice.apache.org).

See the [Apache OpenOffice security page](https://openoffice.apache.org/security.html)
and the [ASF vulnerability handling process](https://www.apache.org/security/).

## In-tree hardening

Known hardening work on this fork is tracked in
[#1 (5.1 hardening punch list)](https://github.com/giobuilds/openoffice/issues/1).
File ordinary bugs and hardening patches as public issues only when they do
not disclose an unfixed vulnerability.

## Supported versions

This fork tracks `trunk`. There is no product release published from this
repository.
