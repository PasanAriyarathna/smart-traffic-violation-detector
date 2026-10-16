# Research Prototype Runbook

This runbook lists commands that were verified locally. Replace paths if your clone differs.

## 1. Detection on video

```powershell
$py = "$env:LOCALAPPDATA\venvs\smart-traffic-yolo\Scripts\python.exe"
$proj = "D:\Campus\semester 6\Intelligent system\smart-traffic-violation-detector"
Set-Location $proj

& $py model\violation_detector.py --source "datasets\raw_clips\no helmet events\not wearing helmets.mp4"
```

Optional plate OCR (install `requirements-ocr.txt` first):

```powershell
& $py model\violation_detector.py --source "path\to\video.mp4" --enable-plate-ocr
```

Red-light rule (after editing `configs/examples/red_light_template.json` for your video):

```powershell
& $py model\violation_detector.py --source "datasets\raw_clips\red light events\red light.mp4" `
  --red-light-config configs\examples\red_light_template.json
```

## 2. YOLO metrics (paper Table)

```powershell
& $py model\evaluate_yolo.py
& $py docs\research_paper\build_paper.py
```

Output PDF: `docs/research_paper/Smart_Traffic_Violation_Detection_Research_Paper.pdf`

## 3. Review backend

```powershell
& $py -m pip install -r requirements-backend.txt
$env:PYTHONPATH = $proj
& $py -m uvicorn backend.app.main:app --reload --port 8000
```

Import JSONL from a detector run:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/events/import" `
  -ContentType "application/json" `
  -Body '{"jsonl_path": "runs/violation_detector/YOUR_RUN/events.jsonl"}'
```

Open dashboard: http://127.0.0.1:8000/

## 4. Blockchain (local tests)

```powershell
Set-Location blockchain
npm install
npm test
```

Sepolia deploy (copy `.env.example` to repo-root `.env`, fill secrets, never commit):

```powershell
npm run deploy:sepolia
```

Set `VIOLATION_LOGGER_ADDRESS` in `.env`, restart backend, verify an event, then:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/events/{event_id}/log-chain" `
  -ContentType "application/json" `
  -Body '{"evidence_hash_hex":"<64-char-hex>","plate_hash_hex":"<64-char-hex>"}'
```

Latency is returned in the JSON response and stored in SQLite.

## 5. Still requires your labeled data

- **OCR CER:** create CSV (`image_path,ground_truth_plate`) and run `scripts/evaluate_plate_cer.py`.
- **Rule accuracy:** manually score helmet / red-light / overtaking candidates (FP/FN tables).
- **Baseline:** YOLOv5 + MySQL comparison (methodology Section 4) is not automated in this repo yet.
