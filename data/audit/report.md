# Audit report

180 labelled Candidates (31 labels changed from the draft, 0 unlabelled) from `data/audit/audit-set.csv`. Each is weighted by its stratum's size over the labelled rows from it, so the figures estimate precision and recall over the 26388 Candidates in the strata with labels.

| stratum | Candidates | labelled | labelled yes |
|---|---|---|---|
| rules-rejected | 19185 | 60 | 0 |
| judge-excluded | 3588 | 60 | 5 |
| judge-included | 3615 | 60 | 34 |

## Rule stage alone

A Candidate counts as relevant when it passes the rules in the current config. Its recall is the most the judge can reach.

| precision | recall | F1 |
|---|---|---|
| 0.326 | 1.000 | 0.492 |

## Rules and judge: Qwen/Qwen3-4B-Instruct-2507@cdbee75f17c01a7cc42f958dc650907174af0554

Scoring took 0.78 s per Candidate over 120 rule passes: about 94.1 min for the 7203 rule passes in the population, plus loading the model.

| threshold | precision | recall | F1 |
|---|---|---|---|
| 0.1 | 0.540 | 0.873 | 0.667 |
| 0.2 | 0.549 | 0.873 | 0.674 |
| 0.3 | 0.557 | 0.873 | 0.680 |
| 0.4 | 0.567 | 0.873 | 0.687 |
| 0.5 | 0.567 | 0.873 | 0.687 |
| 0.6 | 0.567 | 0.873 | 0.687 |
| 0.7 | 0.559 | 0.847 | 0.674 |
| 0.8 | 0.559 | 0.847 | 0.674 |
| 0.9 | 0.569 | 0.847 | 0.681 |

Best F1 0.687 at threshold 0.4.

The best threshold is chosen on this same Audit set, so its F1 is an optimistic estimate.
