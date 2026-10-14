---
name: syllabus
description: Build a cross-book concept map and an ordered study plan (modules with readings, citation scope, exercises and checkpoints) from a textbook library and the learner's goal.
---

# Syllabus

Turn the library into a route. The concept map records where each concept lives in each book and how the books
differ. The syllabus orders concepts into modules a learner can finish one at a time.

## Inputs

- The library (`library/references/catalog.md` and `statements.csv`). Build it first with book2library.
- The learner's goal in their words: what they want to be able to do, and why. Ask if it is missing.
- Constraints: time budget or target dates, a course that follows one book's order, citation-scope rules,
  and anything to skip. Record them in `profile.md`.
- Starting point: what the learner already knows. When unsure, run a short diagnostic (below).

## 1. Inventory each book

For each book, list its concepts from the catalog's section titles and the `statements.csv` rows: each
Definition and named Theorem becomes a concept candidate, with its book, number and printed page. Also take terms
the readings define without a number (italic or margin keywords on the page images), and check the catalog's gap
list for statements the index missed; recover them with `locate`. Use one agent per book in parallel when
available; each returns its inventory as a table.

## 2. Align concepts across books

Merge the inventories into `plan/concept-map.md` using [the template](templates/concept-map.md). For every concept
record, per book: where it is defined, the notation, and the approach. Then add prerequisite edges.

Look hard for **definitional variants**: the same word defined differently (Riemann integral via Darboux sums
versus tagged partitions; "measurable" for sets versus functions; σ-algebra versus algebra), or the same object
built in a different order (outer measure first, or measure first). Read both definitions from the page images
before declaring two concepts the same. Record each variant and how to translate between the books — this is
where self-study across books goes wrong.

A fresh verifier agent then spot-checks the alignment: every "same concept" claim in the map's first modules,
and every recorded variant, against the cited pages.

With a single book, skip the alignment and its verifier. Record instead where the book departs from common usage
the learner will meet elsewhere (labelled "outside the readings"), and write "Parallel reading: none".

## 3. Choose a spine and order the modules

1. Pick one **spine book** whose order and notation the modules follow (the course book, or the clearest
   match to the goal). Other books become parallel readings: an alternative proof, more examples, a gentler
   or more general treatment.
2. Group concepts into modules of roughly one or two study sessions each. Order them so every prerequisite comes
   first (a topological order of the concept map); where the spine's order differs, follow the spine and note
   the forward references.
3. For each module, write the fields in [the syllabus template](templates/syllabus.md): goal, prerequisites,
   primary and parallel readings with printed pages and unit ids, key statements, **citation scope** with the
   background it allows, exercises (core and stretch, by book, section and number), optional lab work, and a
   checkpoint that defines mastery.
4. Check every reading reference against the catalog and every exercise number against the book.

## 4. Calibrate the start

If the learner's background is uncertain, give a short diagnostic: 6–10 questions on the first modules'
prerequisites, mixing definitions, a computation and a proof idea. Mark modules the learner already masters as
`review only`, and add a brief refresher module for any weak prerequisite.

## 5. Agree the plan

Show the learner the module list (titles, readings, checkpoints, dates) and adjust it with them. Then create
`progress.md` from the tutor's [progress template](../tutor/templates/progress.md) with every module
`not started`, and hand over to the tutor.

Revise the syllabus when books are added, the goal changes, or progress shows a module was too large. Keep
module ids stable; do not renumber completed modules.
