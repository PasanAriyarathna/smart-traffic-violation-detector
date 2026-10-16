# Overtaking Validation Report

**Date:** 2026-10-09  
**Module:** `model/rules/overtaking.py`  
**Pipeline integration:** `model/violation_detector.py` (`--overtaking-config`)

## Implementation status: **2 — implemented, unit-tested; real-video accuracy not measured**

Overtaking is **not** inferred from generic detection or ByteTrack alone. The rule requires:

- Configured travel and passing lane polygons (normalized coordinates)
- Fixed-camera `progress_direction`
- At least one **prohibited passing zone** polygon and documented `prohibition_basis`
- Sustained trajectories (default ≥6 aligned samples, ≥0.5 s)
- Behind→ahead order in travel lane, entry into passing lane, progress crossing while in passing lane, and intersection with a prohibited zone

Emitted events use:

- `candidate_type`: `possible_overtaking_in_configured_prohibited_zone`
- `review_status`: `NEEDS_REVIEW`
- `legal_status`: `not_determined`

## Unit tests (synthetic trajectories)

**Command:** `python -m pytest tests/test_overtaking_rule.py -v`

| Test | Intent |
|------|--------|
| `test_complete_same_direction_pass_through_configured_zone` | Valid pass → one candidate |
| `test_too_few_observations_do_not_create_candidate` | Temporal threshold |
| `test_order_reversal_without_entering_passing_lane_is_not_overtaking` | No pass without passing lane |
| `test_missing_geometry_or_prohibition_configuration_disables_rule` | Unsupported config → no events |
| `test_tracking_id_change_does_not_stitch_a_maneuver` | ID switch breaks maneuver |
| `test_duplicate_pair_event_is_suppressed` | One event per (passing, passed) pair |
| `test_pass_outside_configured_prohibition_zone_is_not_illegal_candidate` | Zone gating |
| `test_vehicles_side_by_side_in_travel_lane_without_passing_lane_use` | Parallel travel |
| `test_opposite_direction_progress_does_not_create_candidate` | Wrong travel direction |
| `test_lane_change_into_passing_without_progress_crossing_is_not_overtaking` | Passing lane without overtake |
| `test_temporary_detection_loss_clears_trajectory` | Gap > `maximum_track_gap_seconds` |

**Result (2026-10-09):** all overtaking unit tests **passed** (see pytest log in `docs/validation/pytest_full_log.txt` — re-run to refresh).

## Real-video validation: **NOT COMPLETED**

- No committed per-video overtaking JSON config besides `configs/examples/overtaking_template.json`.
- No labeled overtaking ground-truth video set in the repository.
- **Do not** report field accuracy until human review CSVs exist.

## Configuration workflow

1. `python scripts/probe_video_geometry.py --source "<video>"`
2. Copy and edit `configs/examples/overtaking_template.json` to match resolution and lanes.
3. Run: `python model/violation_detector.py --source ... --overtaking-config configs/your_config.json`
4. Export review sheet: `python scripts/export_rule_review_sheet.py --jsonl runs/violation_detector/.../events.jsonl`

## Remaining risks

- Perspective and lane polygons are manual; errors cause FP/FN.
- Illegal vs legal overtaking is **not** decided automatically — only geometry-based **candidates**.
- Track ID switches on real video can fragment maneuvers (partially mitigated by gap clearing).
