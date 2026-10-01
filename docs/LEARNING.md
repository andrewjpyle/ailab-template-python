# Learning notes

The concepts this template puts into practice, in the order you meet them in the code.

## Baselines

Before measuring a model, measure something dumb. The **majority-class baseline** always
predicts the most frequent label; on this balanced four-class set it scores 0.25 accuracy
and 0.10 macro-F1. The **keyword baseline** is cheap, explainable and fast. A new model
only earns its cost if it clearly beats both, on data neither was tuned on.

## Accuracy, precision, recall, F1

For one label, with TP/FP/FN counted against the gold labels:

- **precision** = TP / (TP + FP): of the times we said "billing", how often were we right?
- **recall** = TP / (TP + FN): of the real billing messages, how many did we find?
- **F1** = 2PR / (P + R): the harmonic mean, which is low if *either* is low.

**Accuracy** is the share of all predictions that are correct. It is fine when classes are
balanced and errors cost the same, and misleading otherwise: with 9 negatives and 1
positive, predicting "negative" always scores 0.90.

## Macro vs micro vs weighted averaging

- **Macro-F1**: mean of per-class F1, every class weighted equally. Exposes a neglected
  minority class.
- **Micro-F1**: pool TP/FP/FN across classes first. For single-label multi-class problems
  it equals accuracy.
- **Weighted-F1**: per-class F1 weighted by support. Closer to accuracy; hides rare-class
  failures.

## Edge cases are part of a metric's definition

- **0/0**: a label never predicted has undefined precision. This repo scores it 0.0
  (scikit-learn's `zero_division=0`), which is pessimistic and therefore safe for a gate.
- **Invented labels**: a predicted label absent from the gold set still gets a row, with
  precision 0, so a model that hallucinates labels is penalised.
- **Empty or mismatched inputs** raise instead of returning a number, since a silent 0 or
  1 here would corrupt the gate.

## The confusion matrix

Rows are gold labels, columns are predictions. Off-diagonal cells show *what* a class is
mistaken for. Here every error lands in the `feedback` column, which immediately points
at the fallback rule rather than at any one keyword list.

## Small samples and uncertainty

With n=40, one example is 2.5 points of accuracy. A 95% Wilson interval around 0.875 is
roughly 0.74 to 0.95, so two models scoring 0.85 and 0.875 are indistinguishable. Bigger
sets, confidence intervals, or paired tests (such as McNemar's on the same examples) are
how you tell real improvements from noise.

## Leakage and in-sample evaluation

The keyword lists were written while reading the evaluation set, so the baseline's
score is **in-sample**. The same trap applies to prompt engineering: iterating on a
prompt against your test set quietly turns it into a training set. Keep a held-out split
you never look at while tuning, and score on it rarely.

## Regression gates

Evaluation that cannot fail a build tends to be ignored. Encoding floors in
`eval_config.toml` turns "the model got worse" into a red check, and lowering a floor
becomes a visible, reviewable diff. Floors should sit a little below the current score:
tight enough to catch a real drop, loose enough not to trip on noise.

## Protocols and dependency inversion

`Classifier` and `LLMProvider` are `typing.Protocol`s: structural interfaces. The runner
depends on the interface, implementations depend on nothing in the runner, and
`isinstance` checks work via `@runtime_checkable`. That is what lets an offline stub, a
local model and a hosted LLM be scored by identical code.

## Parsing LLM output defensively

An LLM returns free text. `LLMClassifier.parse` accepts only a known label and maps
anything else to a declared fallback, so a malformed completion becomes a measurable
error instead of a crash or an unknown label. Real labs often go further with constrained
decoding or structured output.

## Reproducibility

`uv.lock` pins every transitive dependency; `uv sync --locked` fails if the lock is
stale. The stub provider is deterministic. Results record the date, commit, model and
dataset so a number can be traced back to the code that produced it.

## Containers and 12-factor config

A multi-stage build compiles the environment in one stage and copies only the result into
a slim runtime, so compilers and caches never ship. The process runs as an unprivileged
user, and configuration comes from environment variables so the same image runs anywhere.

## Secret hygiene

Git history is permanent and public repos are scraped constantly. Defence in depth: a
pre-push hook catches leaks before they leave the machine, a required CI check catches
them if the hook was skipped, and both scan the full history. Some sensitive strings are
*names*, not credentials, and need a private denylist that is itself never committed and
never echoed. Security checks should fail closed: missing configuration must be an error,
not a pass.

## 10 interview questions

1. Your classifier has 95% accuracy on a dataset where 95% of examples are one class.
   What do you conclude, and which metrics would you report instead?
2. Define precision, recall and F1. Why is F1 a harmonic rather than arithmetic mean, and
   when would you prefer an F-beta score with beta other than 1?
3. What is the difference between macro-, micro- and weighted-averaged F1 for multi-class
   classification? Why does micro-F1 equal accuracy in the single-label case?
4. How should a metric handle a class that is never predicted (0/0 precision), or a
   predicted label that never appears in the gold set? What goes wrong if you skip them?
5. Model A scores 0.85 and model B 0.875 accuracy on 40 examples. Is B better? How would
   you decide, and what would you change about the evaluation?
6. What is test-set leakage? Describe how it can happen through prompt engineering, and how
   you would structure data splits to prevent it.
7. You want CI to fail when model quality regresses. How do you choose thresholds, keep the
   gate from being flaky, and handle evaluations that call a non-deterministic LLM?
8. Why put an LLM behind a narrow `Protocol` such as `complete(prompt) -> str`? What do you
   gain for testing, and what would make you widen the interface?
9. Walk through a multi-stage Dockerfile for a Python service. Why run as non-root, why a
   slim base image, and what belongs in the build stage versus the runtime stage?
10. A teammate pushed an API key and then deleted it in the next commit. Is the repo safe?
    Describe the remediation steps and the controls that would have prevented it.
