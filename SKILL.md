---
name: claim-gate
description: Check a CSV of claims about real companies or people before it is sent or published. Every row needs a source URL, an exact quote and a recent check date; optionally confirm each quote live on the page. Use after any step that writes facts into a list (lead research, sales lists, marketing copy, LLM output).
---

# claim-gate

## When to use
- A list of claims is about to reach a prospect, a client or the public.
- An LLM or agent produced facts about companies and you need proof, not plausibility.

## Steps
1. Make sure the CSV has the columns `claim,evidence_url,evidence_quote,checked_at` (or pass `--config` with your
   own names, in that role order).
2. Run `claim-gate check <file.csv> --live`. Exit code 0 means pass; 1 means at least one row failed (the reasons
   are printed per row); 2 means bad input.
3. Fix or drop every failing row. Never invent a quote or a URL to make a row pass.
4. Before sending, run `claim-gate verify <file.csv>`. It refuses a file changed since the check.

## Rules
- A pass covers only the exact file it checked (sha256).
- Offline mode checks shape and freshness only; use `--live` when the quote must be confirmed on the page.
