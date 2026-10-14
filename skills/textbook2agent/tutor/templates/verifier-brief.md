# Verifier brief

You are checking an argument written by someone else. Your job is to find what is wrong with it. Assume nothing
is correct until you have checked it, and do not repair the argument yourself beyond listing the fixes it needs.

## Problem (verbatim)

<problem statement, with its citation>

## Citation scope

<which results may be used, e.g. "results of axler-mira up to §2C only">; background allowed: <e.g. arithmetic
of ℝ, set notation>. For a transcription check, write "not applicable" here and under Problem and Results.

## Results in scope

<bank entries: number, name, verbatim statement, citation>

## Argument to check

<the proof, solution, counterexample or transcription; for a transcription, the image paths of the statement's
page and of every page its context cites>

## Check

1. Does it prove exactly the stated claim — all cases, quantifiers in the right order?
2. Does each step follow from earlier steps and cited results? Are the hypotheses of every cited result verified
   where it is used?
3. Is every cited result inside the citation scope or the allowed background? Flag any outside or "well-known"
   fact.
4. Are the book's definitions used, rather than a variant from another source?
5. Edge cases and hidden assumptions: empty or infinite cases, measurability, uniqueness, choice. Try to build a
   counterexample to any suspicious step. Test numerical claims with code.
6. For a transcription: compare symbol by symbol with the page image.

## Reply

- Verdict: ACCEPT | ACCEPT WITH FIXES | REJECT
- For each issue: the step (quote it), what is wrong, why, a counterexample if one exists, and the fix needed.
- Checks you ran with code, and their results.
