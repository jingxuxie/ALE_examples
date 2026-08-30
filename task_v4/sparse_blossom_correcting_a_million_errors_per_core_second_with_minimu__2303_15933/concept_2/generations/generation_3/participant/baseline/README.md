# Actual prior champion baseline

`champion.json` is the unmodified, independently passing generation-two v1
artifact, selected after both fresh attempts completed. The v1 score was
1.0104109012101703; v2 scored 1.0104079400244192. Neither is a privileged builder
solution. `generation_2_metrics.json` records its previous official summary;
`metrics.json` records its generation-three result.

The new domain causes actual gap and posterior failures, as well as some
certificate-only failures. The report separates these categories. This valid
failing baseline is not a proof that the strengthened task is feasible, and no
search code or private feasibility artifact is included.
