# Model card: keyword intent baseline

A template model card, filled in for the baseline that ships with this repo. Labs built
from the template should copy this structure for every model they gate on.

## Model details

| Field | Value |
|---|---|
| Name | `KeywordClassifier`, model id `keyword-baseline-v1` (config name `keyword`) |
| Version | v1 (package 0.1.0) |
| Type | Rule-based bag-of-words scorer; no learned parameters |
| Owner | Andrew Pyle |
| License | Apache-2.0 |
| Inputs | One short English support message (free text) |
| Outputs | One of `account`, `billing`, `bug`, `feedback` |

Each label has a hand-written keyword set. A message is tokenised to lowercase words and
each label scores one point per matching token. The highest score wins; a tie or a
message with no matches falls back to `feedback`.

Two comparison models ship alongside it: `majority-baseline-v1` (always predicts the most frequent
training label) and `stub-keyword-v1` (the `LLMClassifier` adapter over an offline stub
provider that delegates to the keyword baseline, used to exercise the prompt and parse
path without a network).

## Intended use

- **Primary:** a reference baseline that demonstrates the eval loop and regression gate,
  and the bar any learned or LLM-based classifier must beat.
- **Users:** engineers building or reviewing labs created from this template.
- **Out of scope:** routing real customer messages, any decision affecting a person,
  non-English text, multi-intent messages, or any domain other than the toy one here.

## Data

- **Evaluation set:** `fixtures/support_intents.jsonl`, 40 hand-written synthetic
  messages, 10 per label. Authored for this repo; no real customers, tickets, products
  or personal data. Provenance is recorded in [FIXTURES.md](FIXTURES.md).
- **Training set:** none. The keyword lists were written by reading the evaluation set,
  so **the reported scores are in-sample** and overstate performance on new text.

## Metrics

| Metric | Why |
|---|---|
| Accuracy | Easy to read; meaningful here because the classes are balanced |
| Macro-F1 | Weights every intent equally, so a model cannot hide a failing class behind a large one |
| Per-class precision / recall / F1 | Shows *which* intent is failing |
| Confusion matrix | Shows *what* each intent is mistaken for |

Gate (in `eval_config.toml`): accuracy >= 0.80 and macro-F1 >= 0.80.

## Results (2026-10-01, commit `dc29470`, n=40)

| Model | Accuracy | Macro-F1 |
|---|---|---|
| `keyword-baseline-v1` | 0.8750 | 0.8813 |
| `stub-keyword-v1` (via `LLMClassifier`) | 0.8750 | 0.8813 |
| `majority-baseline-v1` | 0.2500 | 0.1000 |

Per class for `keyword-baseline-v1`:

| Label | Precision | Recall | F1 |
|---|---|---|---|
| account | 1.00 | 0.90 | 0.95 |
| billing | 1.00 | 0.80 | 0.89 |
| bug | 1.00 | 0.80 | 0.89 |
| feedback | 0.67 | 1.00 | 0.80 |

All five errors are predictions of `feedback`, the fallback label. Four messages match
no keyword at all ("receipts" is plural where the list has "receipt"; a nonprofit
discount question; an app that "logs me out"; a workspace ownership transfer). One is a
tie: "Dragging a card to another column throws an error" scores one point for `billing`
("card") and one for `bug` ("error"). Feedback's low precision is the cost of that
fallback.

With n=40, one message moves accuracy by 2.5 points; differences smaller than that are
noise, and the 95% Wilson interval on 0.875 is roughly 0.74 to 0.95.

## Limitations

- In-sample evaluation; expect lower scores on unseen text.
- No negation or context handling ("not a bug" contains "bug").
- Keyword lists are English-only and brittle to synonyms and typos.
- The fallback label absorbs every unrecognised message, which inflates its recall.
- A 40-row set is enough to exercise the gate, not to compare close models.

## Ethical considerations

- The data is synthetic and contains no personal information; no consent issues arise.
- A real deployment would route people's requests. Silent misrouting (here, defaulting to
  `feedback`) delays help for the people the model fails. A production model should
  abstain to a human queue rather than guess.
- Synthetic text written by one author reflects that author's phrasing. Before trusting a
  model on real users, evaluate it on representative, consented, appropriately licensed
  data, and report results per subgroup where that data allows.

## Caveats and recommendations

Treat this baseline as a floor and a demonstration. Before replacing it, add a held-out
split that was never used to write rules or prompts, and report confidence intervals
alongside point scores.
