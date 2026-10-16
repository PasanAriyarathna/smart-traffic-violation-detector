# Red-Light Candidate Human Review Checklist

For each row in the exported predictions CSV (or each `NEEDS_REVIEW` event in `events.jsonl`):

1. **Timestamp** — Open the annotated video at `video_timestamp`. Does the frame match the evidence JPEG?
2. **Signal state** — Compare `signal_state` to your reviewed intervals in `signal_state_intervals.csv`. If `unknown`, the rule should not have fired; treat as **FP** unless config error.
3. **Stop line** — Does the tracked vehicle center cross the yellow configured line in the direction of `approach_side` (see geometry config)?
4. **Vehicle identity** — Is `tracking_id` the same vehicle across the crossing (check overlay / track continuity)?
5. **Approach direction** — Was the vehicle approaching the intersection on the intended side (not leaving or turning away)?
6. **Legal vs technical** — A **TP** label means the candidate matches your review protocol (geometry + reviewed red interval), not a confirmed traffic-law violation.
7. **Ambiguity** — Use **AMBIGUOUS** when occlusion, track swap, or signal timing is unclear.
8. **Missed events** — Log independently in `red_light_fn_log_template.csv` (not in the prediction CSV).

## Partial evaluation

If `signal_state_intervals.csv` is incomplete, do not treat candidate counts as final metrics. Re-run the detector after full signal merge.
