# Fixture provenance

Every file under `fixtures/` is listed here. A fixture without an entry must not be merged.

## Rule

**Only public or synthetic data may ever be added to this repository.** That means:

- no real customer, user or employee data, and no personal information of any kind;
- no internal business data, logs, tickets, metrics or exports, even if anonymised;
- no hostnames, IP addresses, account names or other infrastructure identifiers;
- public datasets only under a license that permits redistribution, with the source,
  version and license recorded below.

Synthetic text should be written fresh for the fixture, not adapted from real records.
The secret wall (`make scan`) catches some mistakes; it cannot catch all of them, so
this rule is enforced in review as well.

## Files

### `fixtures/support_intents.jsonl`

| Field | Value |
|---|---|
| Rows | 40 (10 each: `account`, `billing`, `bug`, `feedback`) |
| Format | JSONL, one `{"text": str, "label": str}` object per line |
| Author | Andrew Pyle, written by hand for this template (2026-10-01), with AI assistance |
| Origin | Synthetic. Not derived from, sampled from, or paraphrased from any real support messages |
| Personal data | None. No names, emails, account numbers, or identifiable details |
| Business data | None. Refers to a generic, unnamed software product |
| License | Apache-2.0, same as the repository |
| Known bias | Single author, short and clean English; no typos, slang, or multi-intent messages |
