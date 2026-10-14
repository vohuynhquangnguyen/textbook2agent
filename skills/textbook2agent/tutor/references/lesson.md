# Lessons

A lesson makes one module's concepts understandable from the ground up and usable in exercises.

## Prepare before teaching

- Read the module entry in the syllabus and its prerequisites' confidence in `progress.md`.
- Read the primary reading in full (reviewed unit text, or page images for a draft unit). Skim the parallel
  readings for what they add: a different definition, another proof, more examples.
- Bank every statement you will quote. Check `plan/concept-map.md` for definitional variants and
  `progress.md` for misconceptions touching this module.

## Teach in this order

Teach in chunks and pause for the learner's answers, unless the profile asks for complete notes in one go.

1. **Orientation.** Where the module fits the goal; each prerequisite in one line. If a prerequisite has
   confidence 0–1, do a short refresher first.
2. **Motivation.** The question the concept answers, with a concrete case where the naive idea fails.
3. **Definition.** Quote it verbatim from the bank with its citation. Then unpack it clause by clause: what each
   quantifier and condition does, an example and a non-example for each condition, and what goes wrong when a
   condition is dropped.
4. **Worked numerical example.** Textbook style: state the data, show every intermediate step with numbers,
   and end with a check. Use the profile's application domain when it fits naturally (for example defect counts
   and process variation in manufacturing, returns and risk in finance, dosages in pharmacology); use plain
   numbers otherwise. Never bend the mathematics to fit the story. Compute nontrivial numbers with code.
5. **Results.** Quote each statement from the bank. Give the proof idea in two or three sentences, then the
   proof at the depth the profile asks for, marking where each hypothesis is used.
6. **Across the books.** How the parallel reading treats the same idea: a different definition (from the concept
   map's variants), another proof technique, more or less generality. Translate the notation. With a single
   book, compare instead with the notation the learner will meet in their target sources.
7. **Check understanding.** Three to five questions of rising difficulty: recall, compute, explain why, find the
   flaw in a short argument. The learner answers before seeing any answer; then give feedback. Keep the answers
   in `.tutor/`, not in the lesson file.
8. **Assign.** The module's core exercises, each with what it practises.

Write the lesson to `lessons/<module>.md` when the profile asks for notes, or when the lesson spans sessions.

## Keep it accurate

- Every proof, proof idea, counterexample or non-example you write rather than quote is verified before you teach
  it. Batch a lesson's claims into one verification before the lesson starts. Where the book's own argument has
  a gap, say so and give the repaired, verified argument.
- Never present an outside result as the book's. Label outside material "outside the readings".
- When a draft unit's text and the page image disagree, the image wins; note the extraction error.
- If the learner's question goes beyond the module, answer briefly and record it under open questions, or point
  to the module that covers it.
