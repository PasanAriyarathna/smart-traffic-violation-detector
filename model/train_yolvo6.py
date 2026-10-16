from pathlib import Path
import argparse
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(
        description="Train and evaluate the traffic violation YOLO detector."
    )
    parser.add_argument(
        "--data",
        default="datasets/training_copy/data.yaml",
        help="Path to the YOLO dataset YAML file",
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="Starting model weights or a pretrained model name",
    )
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--name", default="traffic_violation_training")
    args = parser.parse_args()

    data_path = Path(args.data).resolve()
    if not data_path.is_file():
        parser.error(f"Dataset YAML not found: {data_path}")
    if args.epochs < 1 or args.imgsz < 32 or args.batch < 1:
        parser.error("epochs, imgsz, and batch must be positive valid values.")

    output_dir = Path("runs/detect")
    output_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(args.model)
    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(output_dir.resolve()),
        name=args.name,
        exist_ok=False,
        plots=True,
        save=True,
    )

    best_weights = output_dir / args.name / "weights" / "best.pt"
    if not best_weights.is_file():
        raise FileNotFoundError(
            f"Training finished, but best weights were not found: {best_weights}"
        )

    print(f"\nBest model saved to: {best_weights.resolve()}")

    trained_model = YOLO(str(best_weights))
    metrics = trained_model.val(
        data=str(data_path),
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        plots=True,
        project=str(output_dir.resolve()),
        name=f"{args.name}_evaluation",
    )

    print("\nEvaluation metrics:")
    print(f"Precision:    {metrics.box.mp:.4f}")
    print(f"Recall:       {metrics.box.mr:.4f}")
    print(f"mAP50:        {metrics.box.map50:.4f}")
    print(f"mAP50-95:     {metrics.box.map:.4f}")


if __name__ == "__main__":
    main()
