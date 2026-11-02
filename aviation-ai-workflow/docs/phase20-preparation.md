# Phase 20 preparation | synthetic intake and source-linked reports

Built against feature/aerocie-015-internal-demo-brief at
955bf3f3815e48ef7886113c4aa56935c73e4367. This preparation is an offline CLI,
not a customer portal, production intake service, or approved client deliverable.

## Contract

sample-data/phase20/intake.json documents the exact allowed intake fields.
The case and subject use demo: identifiers, the organization starts with
Synthetic, and synthetic must be the JSON boolean true. Unknown fields are
rejected. Do not enter actual customer data: these checks cannot detect private
data disguised as a synthetic label or embedded in free text.

The subject must match the checksum-validated AeroCIE-013 packet. The optional
AeroCIE-014 journal is read through the existing read-only audit-chain validator.
The output contains intake provenance, packet provenance, publication links,
review states, and limitations. No new regulatory findings are inferred.
Source URLs are format-checked only. The bundled publication, date and fingerprint
are explicitly fictional placeholders; the placeholder link is suppressed in
generated HTML and is not a real evidence citation.

All external release remains unauthorized, and applicability and compliance remain
NOT_DETERMINED. Private journal names, notes and citations are omitted.
Reports require a new output directory and refuse to overwrite an existing one.
An interrupted write may leave a partial directory; rerun with a fresh path.

## PowerShell validation

The GitHub draft branch includes the runner. Run from aviation-ai-workflow using
your existing Python environment:

~~~powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate-phase20.ps1 -Python "C:\FULL\PATH\TO\.venv\Scripts\python.exe" -OpenDemo
~~~

Only run the script from a trusted checkout. The subprocess execution policy is
not a permanent system setting. The runner needs dependencies from requirements.txt.
It copies source and synthetic samples to a new Documents folder, tests there,
and generates both sample HTML reports. It does not write into your existing
research databases or review journal. Browser opening is not a rendering audit.

To use an existing synthetic packet (not real customer material), first make
appropriate backups of any live research databases:

~~~powershell
python -m src.aerocie.customer_report --intake INTAKE.json --packet PACKET.json --journal JOURNAL.sqlite3 --out-dir NEW_REPORT_FOLDER
~~~

## Remaining work

- Visual rendering inspection at desktop, mobile/narrow viewport and printing.
- Source/link authority and amendment history review for real research evidence.
- Approval of intake fields, privacy handling and customer workflow before any
  production intake UI or real customer information.
- Security and professional/regulatory QA before external release.
- Keep the Phase 18 journal research-only and the seven remaining checks pending.

## Review status

Draft PR stacked on AeroCIE-015. Do not merge or deploy without separate approval.
