---
name: book2lab
description: Implement textbook algorithms as code tested against the book's printed examples, then run experiments that check the theory (convergence, error bounds, sensitivity).
---

# Book2Lab

Paper2MCP binds every tool to existing repository code and checks it against reference runs. Book2Lab binds every
implementation to an algorithm printed in a textbook and checks it against the numbers the book prints. The aim
is to see the theory work: convergence rates, error bounds, stability and sensitivity.

## Layout

```text
lab/
├── pyproject.toml                     one uv project for all lab code
└── <book>/<algorithm>/                e.g. lab/burden-faires/alg-2-3-newton/
    ├── BINDING.md                     book, number, pages, the verbatim pseudocode, and every deviation
    ├── algorithm.py                   the faithful implementation
    ├── test_algorithm.py              acceptance tests from the book's printed examples, plus edge cases
    └── experiments/<slug>/            script, fixed seeds, results, figures, README with conclusions
```

## Steps

1. **Select.** Take the algorithms the current module needs: pseudocode boxes, iterative methods, stated
   procedures. Transcribe the pseudocode verbatim into the statement bank (the tutor's protocol) and copy it into
   `BINDING.md` with its citation.
2. **Find reference numbers.** Look for worked examples and tables that print iterates, residuals or final
   values. They become the acceptance tests. When the book prints none, derive reference values by an
   independent route (a closed form, or a trusted library such as NumPy or SciPy) and say so in `BINDING.md`.
   Never invent values and attribute them to the book.
3. **Implement faithfully.** Follow the pseudocode's steps, stopping rule and outputs; use the book's notation
   where it reads well; expose the parameters the book exposes. Put improvements (pivoting, a better stopping
   test) in separately named variants and list them as deviations. Follow the profile's coding standards.
4. **Test.** Reproduce each printed example: exact equality for integers and identifiers; for floating point, a
   tolerance justified by the digits the book prints (half a unit in the last printed place). Add the breakdown
   cases the book mentions and any invariant the theory guarantees.
5. **Verify independently.** A fresh agent, distinct from the implementer, compares the code with the
   pseudocode line by line, runs the tests, and tries inputs that should trigger the documented failure modes.
   Fix and re-verify until it accepts.
6. **Experiment.** Connect the code to the module's theorems. State the question and the theorem it tests (cite
   the bank), fix seeds, record a results table or figure, and compare with the prediction: measured versus
   theoretical convergence order, tightness of an error bound, sensitivity to perturbed or noisy inputs (for
   instance, noise models from the learner's own field). Write the conclusion in the experiment's
   README, including where the theory and the measurements disagree.
7. **Record.** Summarise in the session note and count lab results as evidence in `progress.md`.

## Running

Use the lab's uv project (`uv add numpy`, `uv run pytest lab/<book>/<algorithm>`). Keep generated data and
figures inside the experiment folder; never write into `library/` or `.work/`.
