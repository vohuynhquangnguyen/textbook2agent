# Exercises and proofs

## Find the exercise

Look it up with `rg -i ',exercise,<number>,' library/references/statements.csv` and check the `section` column.
Bare exercise numbers under a heading such as "Exercises 2A" are stored with that prefix (`2A.4`).
Many books print exercises as bare numbers under an "Exercises" heading, and draft extraction can lose some of
them (often inside formula images): if there is no row, render the chapter's Exercises pages or `locate` a
distinctive phrase, and read the number from the image. The same number may also be a section, Definition or
Example — confirm it is the exercise.

## Set up the exercise

Create `exercises/<book>/<number>/` (for example `exercises/axler-mira/2A.3/`) with:

| File | Content |
| --- | --- |
| `problem.md` | The statement transcribed verbatim from the page image, its citation, the citation scope and the allowed background |
| `attempt.md` | The learner's work, verbatim (one file per attempt if there are several) |
| `hints.md` | Only the hints already released to the learner, in order, with dates |
| `solution.md` | The verified solution or corrected proof, once the learner may see it |
| `verification.md` | Verifier verdicts, one per round |

Keep anything prepared ahead of the learner — the full hint ladder, a solution written before the attempt — in
`.tutor/exercises/<book>/<number>/`, and move each piece into the exercise folder only when it is released.
Before an attempt, never open a `solutions` unit or an answer key, and never show a full solution — unless the
learner asks for it.

## Choose the mode

The profile sets the default; the learner can switch at any time.

- **coach**: hint ladder → learner's attempt → review → verified solution.
- **review**: the learner's attempt → review → corrected proof, verified.
- **solve**: a full verified solution straight away.

## Hint ladder (coach)

Release one level at a time and invite an attempt after each. Record which levels were used.

1. **Orientation.** Restate the goal precisely. Unfold every defined term in the statement into what must
   actually be shown, with the quantifiers explicit. Name the bank entries in scope that look relevant.
2. **Strategy.** The technique (direct proof, contradiction, contrapositive, induction, an ε-argument, a
   construction, a counting argument) and why it fits. Point to an analogous example or result in the readings.
3. **Key step.** The crucial construction, lemma or inequality, still leaving the argument to the learner.

An animation made with [visualize](../../visualize/SKILL.md) can serve as a hint: give each beat a hint level and
release only the section videos up to the level reached.

Add a small numerical illustration to a hint when it makes the idea concrete — test the claim on a specific set,
sequence, function or matrix — and check its numbers with code. The illustration must not give the proof away.
A hint is a claim too: if a hint asserts a lemma or an inequality, it is verified with the solution.

## Review the learner's attempt

1. **Assess it as written first.** Give the overall verdict, what is correct, and every gap or error at its exact
   location (quote the line): why it fails, and a counterexample when one exists.
2. **Then the corrected proof.** Keep the learner's outline, notation and order; change only what is wrong or
   missing, and mark each change. If the outline cannot work, explain why and make the smallest change of
   strategy that does.
3. Verify the corrected proof before calling it correct.

## Write a solution

- **Verbose format** (when the profile asks): open with *Results used* — every definition and result the proof
  relies on, with book, number, printed page and its statement from the bank, all inside the citation scope;
  then the allowed background facts used, listed once and labelled "background". Then the proof, each step
  justified by an item on those lists or by an earlier step.
- **Standard format**: the proof with inline citations.
- Use the book's own definitions and techniques; a definitional variant from another book counts as outside
  material.
- Make quantifiers and edge cases explicit: empty sets, infinite values, measure-zero sets, small n,
  non-unique choices, and any use of the axiom of choice.
- For computational parts, compute with code, show the numbers, and check them by an independent route. Keep
  these checks in your working notes, not in the text sent to the verifier.
- Write in the profile's output format (for example Markdown with LaTeX, or LaTeX in the learner's template,
  compiled to PDF when a TeX engine is available).

Every solution and corrected proof goes through [verification](verification.md) before the learner sees it as
correct. Afterwards, update the exercise row and any misconception in `progress.md`.
