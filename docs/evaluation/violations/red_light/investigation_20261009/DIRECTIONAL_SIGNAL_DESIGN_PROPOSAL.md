# Design proposal — directional signals vs movement (no auto-violation)

## Problem

The current rule fires when (1) a tracked bbox **center** crosses a configured segment and (2) a **scalar** reviewed interval equals `red`. It does **not** read the lamp, distinguish **red ball** vs **green arrow**, or match **movement direction** to **signal aspect**.

## Safe extension (config + event metadata only)

### 1. Reviewed signal aspects (human CSV / JSON)

Extend interval schema (backward compatible):

```json
{
  "start_seconds": 0.0,
  "end_seconds": 11.3,
  "state": "red",
  "aspect": "circular_red",
  "movement_id": "approach_main"
}
```

```json
{
  "start_seconds": 11.3,
  "end_seconds": 14.256,
  "state": "green",
  "aspect": "green_arrow_straight",
  "movement_id": "approach_main"
}
```

- `aspect`: `circular_red` | `circular_amber` | `circular_green` | `green_arrow_straight` | `green_arrow_left` | `unknown` | …
- `movement_id`: links to a **configured movement**, not inferred from video.

### 2. Movement configuration (per camera)

```json
"movements": [
  {
    "movement_id": "approach_main",
    "stop_line": [[120, 540], [1180, 540]],
    "approach_side": 1,
    "travel_direction_deg": 90,
    "applicable_aspects_for_violation": ["circular_red"]
  }
]
```

Rule logic (future): emit candidate only if crossing matches `movement_id` **and** reviewed interval aspect is in `applicable_aspects_for_violation` **and** optional human flag `permissive_arrow_does_not_apply` is false.

### 3. Event record fields (always NEEDS_REVIEW)

- `movement_id`, `reviewed_signal_aspect`, `reviewed_signal_state`
- `crossing_reference`: `bbox_center` | `bbox_foot` | `manual`
- `directionality_status`: `matched` | `unconfigured` | `requires_human_review`

### 4. Explicit non-goals

- No CV classification of arrow vs ball in v1.
- No automatic violation when arrow is green and movement alignment is unknown.

## Track 130 @ 11.788 s

With this design, default would be **no candidate** unless a human interval marked `circular_red` for the motorcycle’s movement at that time; green-arrow intervals would not satisfy `applicable_aspects_for_violation`.
