---
name: textbook2agent
description: Self-study from textbook PDFs - a searchable chapter library, a cross-book syllabus, tutoring with verified proofs, Manim animations, and tested algorithm code. Use to start or continue a study.
---

# Textbook2Agent

Textbook2Agent adapts Paper2Agent to self-study. Paper2Agent turns one paper into a reading skill and its code
into tested tools. Textbook2Agent turns several textbooks into one library, plans a route through them, and
teaches along that route with independent verification of every proof.

| Component | Use it to | Paper2Agent counterpart |
| --- | --- | --- |
| [book2library](book2library/SKILL.md) | Turn textbook PDFs into a chapter-level, searchable library with printed-page citations | paper2skill |
| [syllabus](syllabus/SKILL.md) | Map concepts across books and order them into modules | — |
| [tutor](tutor/SKILL.md) | Run lessons, exercises, proofs, verification and spaced review | — |
| [book2lab](book2lab/SKILL.md) | Implement textbook algorithms as tested code that reproduces the book's examples | paper2mcp |
| [visualize](visualize/SKILL.md) | Animate a concept, proof idea or algorithm with Manim, with checked numbers and verified claims | — |

Resolve each component's scripts, templates and references relative to its own directory.

## Route the request

Read the study workspace first (layout below). Then:

1. **No library yet**, or the learner adds books → book2library.
2. **Library but no `plan/syllabus.md`**, or the goal or book list changed → syllabus.
3. **Everything else** (a lesson, "continue", an exercise, a proof to check, review, "where am I?") → tutor.
4. An algorithm to implement, run or experiment with → book2lab, inside the current module.
5. An animation or visual explanation of a concept, a proof idea or an algorithm → visualize.

A first request such as "help me learn X from these books" runs 1 → 2 → 3 in order. Before step 2, draft
`profile.md` from the tutor's [profile template](tutor/templates/profile.md) with what the learner has said, and
confirm it with them. Ask only for what is missing: the PDFs, the goal, and where the workspace should live.

## Study workspace

```text
<study-root>/
├── profile.md            learner profile: background, goals, explanation and exercise preferences
├── library-plan.json     books and how each splits into units (editable)
├── library/              generated library: SKILL.md, references/catalog.md, references/statements.csv, units/
├── plan/                 concept-map.md and syllabus.md
├── bank/<book>.md        statements transcribed from page images and verified
├── lessons/              lesson notes per module (no answers to their check questions)
├── sessions/             one note per session
├── exercises/<book>/<n>/ problem, the learner's attempts, released hints, solution and verification
├── lab/                  book2lab implementations and experiments
├── visuals/<slug>/       visualize storyboards, quantities, Manim scenes and renders
├── progress.md           module status, concept confidence, review queue, misconceptions, open questions
├── .tutor/               material prepared ahead of the learner: hint ladders, answers, early solutions
└── .work/                extraction evidence; never edit by hand
```

The workspace must persist between conversations. Use a local folder when one is available. In a hosted chat
whose files do not persist, keep the small state files (profile, plan, bank, progress, session notes) in the
host's durable storage, such as project documents, and rebuild `library/` from the PDFs when needed.

## Rules for every component

- The books are the authority. Quote definitions and theorems verbatim with citations
  (`[book] Definition 2.7, p. <printed> (PDF <n>)`); never paraphrase a definition and present it as the book's.
- Treat draft library text as a locator only. Before quoting a formula, definition or theorem from a draft unit,
  read it from the rendered page image and record it in the statement bank.
- Every proof, solution or counterexample the agent writes is checked by a fresh verifier agent that did not
  write it. If agents cannot be spawned, do a separate verification pass and say that independent verification
  was unavailable.
- Respect the learner's profile and the module's citation scope (for example, "only results up to §2C").
- Keep the books private: never publish library text or page images.
