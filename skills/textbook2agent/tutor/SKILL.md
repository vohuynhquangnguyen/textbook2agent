---
name: tutor
description: Run self-study sessions over a textbook library - lessons from foundations, staged hints, review of the learner's proofs, independently verified solutions, and spaced review.
---

# Tutor

Teach the current syllabus module from the learner's books, check every agent-written argument independently,
and keep the learner's state so the next session continues where this one stopped.

## Start every session

1. Read `profile.md`, `progress.md` and the current module in `plan/syllabus.md`.
   If `profile.md` is missing, draft it from [the template](templates/profile.md) using what is already known
   about the learner (their stated preferences, earlier conversations), show it, and confirm it in one message.
2. **Due reviews first.** For each concept in `progress.md` whose next review date has arrived, ask one or two
   retrieval questions without notes (state a definition, apply a result, spot the flaw in a short argument).
   Grade them, then update confidence and next review dates. Keep this to a few minutes.
3. Do what the learner asked. "Continue" means the next step of the current module: lesson, then core
   exercises, then the checkpoint.

| Activity | Instructions |
| --- | --- |
| Lesson on a concept or section | [lesson.md](references/lesson.md) |
| Exercise, proof, or the learner's attempt to review | [exercises.md](references/exercises.md) |
| Checking any proof, solution, counterexample or transcription | [verification.md](references/verification.md) |
| Algorithm implementation or experiment | [book2lab](../book2lab/SKILL.md) |

## Quote the books through the statement bank

Every definition, theorem or formula presented as the book's goes through `bank/<book>.md`:

1. Look for the statement in the bank. If it is there and verified, quote it.
2. Otherwise find it with `library/references/statements.csv` or the catalog; when the index has no row, use
   `locate` and the catalog's gap list. Read it from the unit text when the unit is **reviewed**; when it is
   **draft**, render the page and read the image.
3. Transcribe it verbatim in LaTeX with its number, name, section, printed and PDF pages. Include the context it
   depends on: notation fixed earlier in the section, standing assumptions ("throughout this chapter …"), with
   the pages where that context is stated. Add it with [the bank template](templates/bank-entry.md), marked
   `verifier: pending`.
4. Have the transcription checked by a verifier against the page images — the statement's page and every page
   its context cites. Batch the transcriptions a piece of work needs into one check, and finish it **before**
   the statement is presented as the book's text or cited in a proof sent for verification. Record the verdict
   in the entry's *Checked* line.

Outside facts are allowed in explanations only when labelled "outside the readings". In exercises, use only
results inside the module's citation scope plus the background it explicitly allows (for example the arithmetic
of ℝ or set notation), labelled as background.

## End every session

1. Write `sessions/<date>-<module>.md` from [the session template](templates/session.md).
2. Update `progress.md` ([template](templates/progress.md)): module status, concept confidence with its
   evidence, exercise rows, new misconceptions, open questions, and next review dates.
3. Tell the learner, briefly: what was covered, what is due next time, and the next step.

## Hold to the profile

The profile sets the explanation style, the default exercise mode, proof format, output format, application
domain for examples, and verification depth. The learner's current request overrides it. When the learner
states a lasting preference, offer to add it to `profile.md`.
