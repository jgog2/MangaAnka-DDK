# Publisher completion fixtures

Unmodified public MANGA Plus `title_detailV4` protobuf responses captured on
2026-10-08 at 01:04 UTC (2026-10-07 America/Chicago). Query parameters were
`title_id=<filename stem>&clang=eng` on
`https://jumpg-webapi.tokyo-cdn.com/api/title_detailV4`.

- 100026: The Promised Neverland; COMPLETED, only numbered chapters 1–4 exposed.
- 100014: Haikyu!!; COMPLETED, only numbered chapters 1–4 exposed.
- 100010: Dr. STONE; COMPLETED, only numbered chapters 1–4 exposed.
- 100003: Black Clover; COMPLETED, first four and explicitly labeled Final Page 392.

The files contain public title/chapter metadata, not reader pages, credentials,
session tokens, or catalog contents. Chapter availability is not final-chapter
authority. The tests do not use series names or IDs as runtime policy.

Original capture script, parsed observations, frontend protobuf definitions,
and SHA-256 manifest are under `build/batch004-autonomous-20261007/`.
