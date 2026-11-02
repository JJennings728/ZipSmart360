# Microsoft Power BI schema validation fixtures

Unmodified Microsoft JSON schemas are bundled so report validation remains offline and repeatable. `manifest.json` records each upstream URL and downloaded file's SHA-256. `scripts/validate_powerbi.py` rejects missing references or changed checksums. PBIR files retain their official Microsoft `$schema` URIs; the validator resolves those URIs to this local bundle.

Sources: [microsoft/json-schemas](https://github.com/microsoft/json-schemas) and the [Power BI report theme schema 2.152](https://github.com/microsoft/powerbi-desktop-samples/tree/main/Report%20Theme%20JSON%20Schema). Respective MIT licenses are retained alongside the fixtures. To update a schema, review the authoritative upstream change, include its full referenced graph, update the checksum manifest, and rerun all validation. Never relax validation or replace a checksum to conceal a corrupt download.

These schemas validate serialized definitions; they do not execute DAX, parse TMDL in the Desktop engine or prove report rendering. Native visual format properties are extensible and still need Windows inspection.
