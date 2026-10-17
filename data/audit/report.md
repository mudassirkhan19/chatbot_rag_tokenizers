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

## Model comparison

Each model at the threshold with its best F1, and its run time over every rule pass in the population.

| model | threshold | precision | recall | F1 | s per Candidate | full run (min) |
|---|---|---|---|---|---|---|
| Qwen/Qwen3-4B-Instruct-2507@cdbee75f | 0.95 | 0.579 | 0.847 | 0.688 | 0.78 | 94.1 |
| Qwen/Qwen3-1.7B@70d244cc | 0.9 | 0.459 | 0.974 | 0.624 | 0.27 | 33.0 |
| ibm-granite/granite-4.0-micro@56111ae1 | 0.8 | 0.725 | 0.744 | 0.734 | 0.63 | 75.7 |
| gemma4:e2b-mlx@e98b54fe@0.40.5 | 0.005 | 0.744 | 0.821 | 0.781 | 0.06 | 7.2 |
| tev1:4b@4d24c6f6@0.40.5 | 0.8 | 0.810 | 0.872 | 0.840 | 0.89 | 106.4 |
| tev1:0.8b@b661d565@0.40.5 | 0.7 | 0.467 | 0.898 | 0.615 | 0.03 | 4.1 |

## Rules and judge: Qwen/Qwen3-4B-Instruct-2507@cdbee75f17c01a7cc42f958dc650907174af0554

Scoring took 0.78 s per Candidate over 120 rule passes: about 94.1 min for the 7203 rule passes in the population, plus loading the model.

| threshold | precision | recall | F1 |
|---|---|---|---|
| 0.001 | 0.515 | 0.924 | 0.661 |
| 0.005 | 0.515 | 0.898 | 0.655 |
| 0.01 | 0.515 | 0.898 | 0.655 |
| 0.02 | 0.523 | 0.898 | 0.661 |
| 0.05 | 0.540 | 0.873 | 0.667 |
| 0.1 | 0.540 | 0.873 | 0.667 |
| 0.2 | 0.549 | 0.873 | 0.674 |
| 0.3 | 0.557 | 0.873 | 0.680 |
| 0.4 | 0.567 | 0.873 | 0.687 |
| 0.5 | 0.567 | 0.873 | 0.687 |
| 0.6 | 0.567 | 0.873 | 0.687 |
| 0.7 | 0.559 | 0.847 | 0.674 |
| 0.8 | 0.559 | 0.847 | 0.674 |
| 0.9 | 0.569 | 0.847 | 0.681 |
| 0.95 | 0.579 | 0.847 | 0.688 |

Best F1 0.688 at threshold 0.95.

## Rules and judge: Qwen/Qwen3-1.7B@70d244cc86ccca08cf5af4e1e306ecf908b1ad5e

Scoring took 0.27 s per Candidate over 120 rule passes: about 33.0 min for the 7203 rule passes in the population, plus loading the model.

| threshold | precision | recall | F1 |
|---|---|---|---|
| 0.001 | 0.379 | 1.000 | 0.550 |
| 0.005 | 0.387 | 1.000 | 0.558 |
| 0.01 | 0.395 | 1.000 | 0.566 |
| 0.02 | 0.407 | 1.000 | 0.579 |
| 0.05 | 0.411 | 1.000 | 0.583 |
| 0.1 | 0.420 | 1.000 | 0.592 |
| 0.2 | 0.434 | 1.000 | 0.605 |
| 0.3 | 0.434 | 1.000 | 0.605 |
| 0.4 | 0.439 | 1.000 | 0.610 |
| 0.5 | 0.439 | 1.000 | 0.610 |
| 0.6 | 0.439 | 1.000 | 0.610 |
| 0.7 | 0.443 | 0.974 | 0.609 |
| 0.8 | 0.448 | 0.974 | 0.614 |
| 0.9 | 0.459 | 0.974 | 0.624 |
| 0.95 | 0.459 | 0.974 | 0.624 |

Best F1 0.624 at threshold 0.9.

## Rules and judge: ibm-granite/granite-4.0-micro@56111ae135df9c53a78c99028e7bc24035a9e979

Scoring took 0.63 s per Candidate over 120 rule passes: about 75.7 min for the 7203 rule passes in the population, plus loading the model.

| threshold | precision | recall | F1 |
|---|---|---|---|
| 0.001 | 0.343 | 1.000 | 0.511 |
| 0.005 | 0.365 | 1.000 | 0.535 |
| 0.01 | 0.379 | 1.000 | 0.550 |
| 0.02 | 0.395 | 1.000 | 0.566 |
| 0.05 | 0.449 | 1.000 | 0.620 |
| 0.1 | 0.470 | 1.000 | 0.640 |
| 0.2 | 0.488 | 1.000 | 0.656 |
| 0.3 | 0.543 | 0.974 | 0.697 |
| 0.4 | 0.554 | 0.923 | 0.693 |
| 0.5 | 0.577 | 0.872 | 0.694 |
| 0.6 | 0.628 | 0.821 | 0.711 |
| 0.7 | 0.652 | 0.769 | 0.706 |
| 0.8 | 0.725 | 0.744 | 0.734 |
| 0.9 | 0.828 | 0.616 | 0.706 |
| 0.95 | 0.889 | 0.411 | 0.562 |

Best F1 0.734 at threshold 0.8.

## Rules and judge: gemma4:e2b-mlx@e98b54fe1913178321e1d9cd007d12a465de77a8f8eae37af69d2501ca03c6b5@0.40.5

Scoring took 0.06 s per Candidate over 120 rule passes: about 7.2 min for the 7203 rule passes in the population, plus loading the model.

| threshold | precision | recall | F1 |
|---|---|---|---|
| 0.001 | 0.642 | 0.872 | 0.739 |
| 0.005 | 0.744 | 0.821 | 0.781 |
| 0.01 | 0.756 | 0.795 | 0.775 |
| 0.02 | 0.757 | 0.718 | 0.737 |
| 0.05 | 0.794 | 0.693 | 0.740 |
| 0.1 | 0.844 | 0.693 | 0.761 |
| 0.2 | 0.833 | 0.641 | 0.725 |
| 0.3 | 0.857 | 0.616 | 0.717 |
| 0.4 | 0.857 | 0.616 | 0.717 |
| 0.5 | 0.889 | 0.616 | 0.728 |
| 0.6 | 0.923 | 0.616 | 0.739 |
| 0.7 | 0.920 | 0.590 | 0.719 |
| 0.8 | 1.000 | 0.590 | 0.742 |
| 0.9 | 1.000 | 0.564 | 0.722 |
| 0.95 | 1.000 | 0.539 | 0.700 |

Best F1 0.781 at threshold 0.005.

## Rules and judge: tev1:4b@4d24c6f6d61a48d9b72902f4805c5f1da53010736b834b0372377fb4bb7e53d3@0.40.5

Scoring took 0.89 s per Candidate over 120 rule passes: about 106.4 min for the 7203 rule passes in the population, plus loading the model.

| threshold | precision | recall | F1 |
|---|---|---|---|
| 0.001 | 0.326 | 1.000 | 0.492 |
| 0.005 | 0.334 | 1.000 | 0.501 |
| 0.01 | 0.340 | 1.000 | 0.507 |
| 0.02 | 0.352 | 1.000 | 0.521 |
| 0.05 | 0.391 | 1.000 | 0.562 |
| 0.1 | 0.439 | 1.000 | 0.610 |
| 0.2 | 0.514 | 1.000 | 0.679 |
| 0.3 | 0.566 | 1.000 | 0.723 |
| 0.4 | 0.592 | 1.000 | 0.743 |
| 0.5 | 0.656 | 0.974 | 0.784 |
| 0.6 | 0.673 | 0.949 | 0.788 |
| 0.7 | 0.726 | 0.949 | 0.822 |
| 0.8 | 0.810 | 0.872 | 0.840 |
| 0.9 | 0.849 | 0.719 | 0.778 |
| 0.95 | 0.923 | 0.616 | 0.739 |

Best F1 0.840 at threshold 0.8.

## Rules and judge: tev1:0.8b@b661d56508169d2b6c4cab5a047409f50bd9694a215bc232469d44291f4bdbf1@0.40.5

Scoring took 0.03 s per Candidate over 120 rule passes: about 4.1 min for the 7203 rule passes in the population, plus loading the model.

| threshold | precision | recall | F1 |
|---|---|---|---|
| 0.001 | 0.326 | 1.000 | 0.492 |
| 0.005 | 0.337 | 1.000 | 0.504 |
| 0.01 | 0.340 | 1.000 | 0.507 |
| 0.02 | 0.343 | 1.000 | 0.511 |
| 0.05 | 0.346 | 1.000 | 0.514 |
| 0.1 | 0.369 | 1.000 | 0.539 |
| 0.2 | 0.387 | 1.000 | 0.558 |
| 0.3 | 0.407 | 1.000 | 0.579 |
| 0.4 | 0.412 | 0.949 | 0.574 |
| 0.5 | 0.452 | 0.949 | 0.612 |
| 0.6 | 0.461 | 0.898 | 0.609 |
| 0.7 | 0.467 | 0.898 | 0.615 |
| 0.8 | 0.473 | 0.872 | 0.613 |
| 0.9 | 0.492 | 0.769 | 0.600 |
| 0.95 | 0.501 | 0.744 | 0.598 |

Best F1 0.615 at threshold 0.7.

The best threshold is chosen on this same Audit set, so its F1 is an optimistic estimate.
