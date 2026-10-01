# Design notes

Decisions behind the template, and the alternatives that were considered and rejected.
The bar for anything in a template is high: every file is copied into every lab.

## 1. Evaluation is a CI gate with thresholds in version control

`ailab-eval` exits 1 when a metric falls below its floor in `eval_config.toml`, so a model
regression fails the build exactly like a failing test.

- *Rejected: report-only evals (a notebook or dashboard).* Nobody blocks a merge on a
  chart. A number that cannot fail the build drifts.
- *Rejected: compare against the previous run's score.* That needs stored state and lets
  quality ratchet down by small steps. Explicit floors in the diff force the conversation
  in code review when someone lowers one.
- *Rejected: thresholds only in CI YAML.* They must apply identically on a laptop, in
  Docker and in CI, so they live in the config file and can be overridden by environment.

### The results file is a versioned contract

`eval_results.json` is consumed by other tools (a host application can pull the CI
artifact through the GitHub API), so its required keys are fixed under `schema_version`
1 and pinned by a test. Diagnostics live in extra keys that may change freely.

- *Rejected: only printing results to the log.* Machines should not scrape logs.
- *Rejected: an unversioned dict.* Any rename would silently break consumers.

## 2. Small `Protocol` seams instead of a framework

`Classifier` (`provider`, `model`, `predict`) and `LLMProvider` (`name`, `model`,
`complete`) are structural
types. Anything with those attributes plugs in, with no base class to inherit.

- *Rejected: LangChain, LlamaIndex or a vendor SDK in the template.* Heavy dependency trees
  for two methods, and a vendor choice every lab would inherit. Labs add the SDK they need
  behind `LLMProvider`.
- *Rejected: abstract base classes.* `Protocol` gives the same type checking without
  coupling implementations to this package.
- *Rejected: a batch `predict_many` API from the start.* Useful for real LLM throughput,
  but premature here; it can be added as an optional method when a lab needs it.

## 3. An offline stub provider, no network in tests or CI

`StubProvider` answers prompts deterministically, so the prompt-build, completion and
parse path runs in every test and CI job without keys, cost or flakiness.

- *Rejected: recorded HTTP cassettes.* They couple tests to one vendor's wire format.
- *Rejected: calling a live model in CI.* Non-deterministic, costs money, needs secrets in
  every PR including forks, and turns provider outages into red builds.

## 4. Metrics written by hand, not scikit-learn

Accuracy, per-class P/R/F1, macro-F1 and the confusion matrix are about 70 lines.

- *Rejected: scikit-learn.* A large dependency for four functions, and hand-written code
  makes the conventions explicit: labels are the union of gold and predicted (an invented
  label is penalised), and 0/0 scores 0.0 (scikit-learn's `zero_division=0`). Labs that
  need more metrics should add the library then.

## 5. Macro-F1 alongside accuracy

Accuracy hides a failing minority class. Macro-F1 averages per-class F1 unweighted, so
every intent counts equally. Both are gated.

- *Rejected: micro-F1.* For single-label classification it equals accuracy.
- *Rejected: weighted-F1 as the gate.* It weights by support and so shares accuracy's
  blind spot.

## 6. uv with a committed lockfile, hatchling, src layout

`uv sync --locked` gives the same environment on every machine and in Docker. The src
layout means tests import the installed package, not files that happen to be on the path.

- *Rejected: pip + requirements.txt.* No lock of transitive dependencies by default, and
  slower.
- *Rejected: Poetry.* Works, but slower and a second tool where uv already manages Python.
- *Rejected: flat layout.* It hides packaging mistakes until the wheel is installed
  somewhere else.

## 7. Multi-stage, non-root, 12-factor container

The builder stage uses the official uv image to build `/opt/venv` from the lockfile. The
runtime stage is `python:3.12-slim` plus that venv: no uv, no compiler, a fixed UID
10001, and every setting is an environment variable.

- *Rejected: single stage.* Ships build tooling and caches; larger attack surface.
- *Rejected: distroless or Alpine.* Distroless complicates debugging for a learning repo;
  Alpine's musl breaks many scientific wheels that labs will need.
- *Rejected: config baked into the image.* The defaults are, but anything can be
  overridden at `docker run` time without a rebuild.

## 8. Secret wall: a git hook and a required CI check

Two layers, because each fails differently: hooks are skippable (`--no-verify`, or never
installed), and CI only catches a leak after it has reached the remote.

- **gitleaks** with the default rules plus custom Doppler rules catches credentials.
- **The denylist scan** catches what gitleaks cannot know about: private names and
  infrastructure identifiers. Private patterns come from a secret or a local file and are
  never committed or printed, because the list itself would leak what it protects.
- **Fail closed.** If the private list is missing, the scan fails. A silent pass would be
  indistinguishable from a clean repo. Fork PRs, which cannot read secrets, are the one
  explicit exception.
- **Full history, not just the working tree.** Deleting a leaked line in a later commit
  does not remove it from the repository.
- **Pinned and checksum-verified gitleaks in CI.** A floating "latest" download is a
  supply-chain risk in the very job meant to protect the repo.
- *Rejected: a third-party gitleaks GitHub Action.* Adds a dependency with its own
  licensing and token requirements; running the pinned binary is simpler and auditable.
- *Rejected: pre-commit framework.* Another runtime and config format for a single hook;
  `core.hooksPath` needs nothing.

## 9. Things deliberately left out

Experiment tracking, data versioning, notebooks, a web API, and multiple Python
versions. Each is useful in some lab and noise in most; a template should be easy to
read in one sitting and easy to extend.
