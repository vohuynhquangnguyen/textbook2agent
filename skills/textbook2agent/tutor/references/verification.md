# Independent verification

No proof, solution, counterexample or statement transcription written by the agent reaches the learner as
correct until an agent that did not write it has tried to break it.

## Brief the verifier

Spawn a **fresh** agent for each verification and give it [the verifier brief](../templates/verifier-brief.md)
filled in with:

- the problem statement, verbatim, its citation scope and the allowed background;
- the bank entries in scope;
- the argument to check.

For a transcription, give it the transcription and the rendered images of the statement's page and of every page
its context cites, and mark the problem, scope and results sections "not applicable".

Do not give it the author's reasoning, drafts, hints, check marks, or any claim that the argument is correct. The
verifier must differ from every agent that wrote or repaired the argument. When the host has no agent tool but
has a command-line agent, start a fresh non-interactive session in a new, empty folder that holds only the brief
and its page images; that counts as a fresh agent.

## What the verifier checks

1. **The claim.** The argument proves exactly the stated result: every case, the right order of quantifiers.
2. **Each step.** Follows from earlier steps and cited results; every hypothesis of a cited result is verified
   where the result is used.
3. **Citation scope.** Every cited result is in scope or in the allowed background. No outside theorem slips
   in, including "well-known" facts.
4. **Definitions.** The book's definitions are used, not a variant from another book.
5. **Edge cases and hidden assumptions.** Empty or infinite cases, measurability, uniqueness, choice. It tries to
   build a counterexample to any suspicious step, and tests numerical claims with code (random instances of an
   inequality, a claimed limit, a computed value).
6. **Transcriptions.** Symbol by symbol against the page image, including subscripts, quantifiers and
   conditions.

Verdict: **ACCEPT**, **ACCEPT WITH FIXES** (each fix listed), or **REJECT** (the first failing step, why, and a
counterexample when one exists). Record every verdict: in the exercise's `verification.md`, in the bank entry's
*Checked* line for a transcription, or in the session note for claims made in a lesson.

## Repair loop

ACCEPT ends the loop. ACCEPT WITH FIXES ends it once every listed fix is applied, provided each fix only adds a
citation, a label or a routine step and introduces no new claim; record "fixes applied". Otherwise the author
repairs and a fresh verifier re-checks the changed steps and everything depending on them. After three rounds
without passing, present the best version to the learner and state the unresolved issue plainly.

## Hard problems

When the profile asks for it, or after a REJECT, run two independent solver agents with different strategies.
Verify both. Present the verified one — or both, when they teach different techniques.

## Without agent spawning

Finish the argument, then do a separate pass that re-reads only the brief's inputs and checks the list above.
Tell the learner that independent verification was unavailable.
