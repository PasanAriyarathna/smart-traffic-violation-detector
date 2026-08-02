import cv2
import os
import argparse


def extract_frames_evenly(video_path, output_dir, frames_per_video=30):
    """
    Extracts a fixed number of frames evenly spread across the full
    length of a video (instead of using a fixed frame-skip interval),
    so short and long clips are represented proportionally.
    """
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames <= 0:
        print(f"⚠️ Could not read: {video_path}")
        cap.release()
        return 0

    step = max(1, total_frames // frames_per_video)

    count = 0
    saved_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if count % step == 0 and saved_count < frames_per_video:
            frame_name = os.path.join(output_dir, f"frame_{saved_count:04d}.jpg")
            cv2.imwrite(frame_name, frame)
            saved_count += 1
        count += 1

    cap.release()
    print(f"✅ {os.path.basename(video_path)} -> {saved_count} frames "
          f"(step={step}, total_frames={total_frames})")
    return saved_count


def main():
    parser = argparse.ArgumentParser(description="Extract frames from dashcam video clips.")
    parser.add_argument('--input', required=True, help='Folder containing raw video clips')
    parser.add_argument('--output', required=True, help='Folder to save extracted frames')
    parser.add_argument('--frames_per_video', type=int, default=30,
                         help='Number of frames to extract per video (default: 30)')
    args = parser.parse_args()

    video_folder = args.input
    output_folder = args.output

    if not os.path.exists(video_folder):
        print(f"❌ Folder not found: {video_folder}")
        return

    print(f"✅ Found video folder: {video_folder}")

    total_frames_extracted = 0
    video_count = 0
    failed_videos = []

    for video_file in os.listdir(video_folder):
        if video_file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            video_path = os.path.join(video_folder, video_file)
            video_name = os.path.splitext(video_file)[0]
            video_output_dir = os.path.join(output_folder, video_name)

            frames_saved = extract_frames_evenly(video_path, video_output_dir, args.frames_per_video)

            if frames_saved > 0:
                total_frames_extracted += frames_saved
                video_count += 1
            else:
                failed_videos.append(video_file)

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Videos processed successfully: {video_count}")
    print(f"Total frames extracted: {total_frames_extracted}")
    if failed_videos:
        print(f"⚠️ Failed videos ({len(failed_videos)}): {failed_videos}")
    print(f"Frames saved to: {output_folder}")


if __name__ == "__main__":
    main()