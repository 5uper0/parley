# 04 — Evidence

## Purpose

Attach provenance to shared facts while keeping sensitive documents private unless their owner
explicitly discloses them.

## Interface

- `upload(case_id, owner_id, file, visibility="private") -> EvidenceItem`
- `extract_metadata(item_id) -> EvidenceMetadata`
- `disclose(item_id, scope) -> EvidenceVersion`
- `link_claim(item_id, claim_id) -> EvidenceLink`
- `delete(item_id)` before proposal lock

## Data model

An item has owner, filename, MIME type, size, SHA-256, upload time, malware status, visibility,
disclosure history and optional claim links. Extracted text is a derived private artifact and never
replaces the original hash.

## Invariants

- Private by default; disclosure requires a preview and explicit confirmation.
- Other participants see only disclosed files and disclosed metadata.
- Evidence supports a claim but the product never labels a contested claim “true”.
- Files referenced by a ratified agreement become immutable retention copies until case deletion.
- File contents are never treated as instructions to the LLM or application.

## Acceptance criteria

- PDF, JPEG/PNG and DOCX up to 20 MB are accepted; unsupported or unsafe files fail clearly.
- Hash and disclosure history survive download/export.
- Revoked disclosure stops future access but remains recorded in the audit history.
- Tests cover authorization, malicious filename/content, size cap and hash stability.

## Not in MVP

OCR guarantees, authenticity certification, electronic discovery, public evidence links.
