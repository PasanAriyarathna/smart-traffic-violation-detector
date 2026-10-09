"""Extract evenly spaced frames from videos for manual annotation."""

import argparse
from pathlib import Path

import cv2


NUM_FRAMES = 30
SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
JPEG_QUALITY = 95


def extract_frames(video_path: Path, output_dir: Path, num_frames: int = NUM_FRAMES) -> tuple[int, bool]:
    """Save up to ``num_frames`` frames sampled across the full video duration."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"FAILED: {video_path.name} (could not open video)")
        cap.release()
        return 0, False

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    duration = total_frames / fps if fps > 0 and total_frames > 0 else 0.0
    print(
        f"Video: {video_path.name} | total frames: {total_frames} | "
        f"FPS: {fps:.3f} | duration: {duration:.2f}s"
    )

    if total_frames <= 0:
        cap.release()
        print(f"FAILED: {video_path.name} (frame count unavailable)")
        return 0, False

    # Include the beginning and end; rounded unique indices stay evenly spread.
    sample_count = min(num_frames, total_frames)
    indices = [round(i * (total_frames - 1) / max(sample_count - 1, 1))
               for i in range(sample_count)]
    output_dir.mkdir(parents=True, exist_ok=True)
    extracted = 0
    for output_index, frame_index in enumerate(indices, start=1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok or frame is None:
            print(f"  Could not decode frame {frame_index}; skipping it.")
            continue
        destination = output_dir / f"frame_{output_index:04d}.jpg"
        if cv2.imwrite(str(destination), frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]):
            extracted += 1
        else:
            print(f"  Could not save {destination.name}.")

    cap.release()
    success = extracted > 0
    print(f"Extracted frame count: {extracted}/{num_frames}")
    return extracted, success


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract evenly spaced video frames.")
    parser.add_argument("--input", required=True, help="Folder containing source videos")
    parser.add_argument("--output", required=True, help="Folder for per-video frame folders")
    parser.add_argument("--num-frames", type=int, default=NUM_FRAMES,
                        help=f"Frames to sample per video (default: {NUM_FRAMES})")
    args = parser.parse_args()
    if args.num_frames < 1:
        parser.error("--num-frames must be at least 1")

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    if not input_dir.is_dir():
        parser.error(f"Input folder does not exist: {input_dir}")

    videos = sorted(path for path in input_dir.iterdir()
                    if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS)
    successful = 0
    failed: list[str] = []
    total_extracted = 0

    for video_path in videos:
        video_output = output_dir / video_path.stem
        extracted, ok = extract_frames(video_path, video_output, args.num_frames)
        total_extracted += extracted
        if ok:
            successful += 1
        else:
            failed.append(video_path.name)

    print("\nSUMMARY")
    print(f"Total videos found: {len(videos)}")
    print(f"Successfully processed videos: {successful}")
    print(f"Failed videos: {len(failed)}" + (f" ({', '.join(failed)})" if failed else ""))
    print(f"Total frames extracted: {total_extracted}")
    print(f"Frames saved to: {output_dir}")


if __name__ == "__main__":
    main()
