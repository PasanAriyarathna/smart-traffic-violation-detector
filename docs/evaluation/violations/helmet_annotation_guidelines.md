# Helmet Review-Candidate Annotation Guidelines

## Rule under evaluation

The prototype emits **review candidates** when a tracked **person** is geometrically associated with a **motorcycle** and no **helmet** detection overlaps an expanded approximate head region. This is **not** proof of a traffic-law violation.

## Labels (candidate-level)

| Label | Use when |
|-------|----------|
| **TP** | The candidate is a **plausible review case**: rider association looks correct and the head region suggests **no clearly visible helmet** on the associated rider. |
| **FP** | False alarm: wrong association, helmet clearly visible, not a rider, pedestrian, duplicate/noise, or evidence insufficient to justify review. |
| **Ambiguous** | Occlusion, distance, blur, or angle prevents a confident TP/FP decision. |
| **Unreviewed** | No human decision yet. |

## Fields in `helmet_reviewed_annotations.csv`

- `association_correct`: yes / no / unclear  
- `helmet_visible`: yes / no / unclear  
- `rider_visible`: yes / no / unclear  
- `evidence_quality`: good / fair / poor  
- `confidence_in_review`: 1–5 (optional)  

## False negatives (recall)

FN counts require a **separate full-video review** (or sampled protocol) documented in `helmet_fn_log.csv`. Do **not** label FN on candidate rows.

## Metrics

- **Precision** = TP / (TP + FP) on rows labeled TP or FP.  
- **Recall** = TP / (TP + FN_video) only when FN_video is independently recorded.  
- **F1** = harmonic mean when both P and R are defined.

## Privacy

Do not publish identifiable faces or plates in the paper; use cropped evidence already blurred where applicable.
