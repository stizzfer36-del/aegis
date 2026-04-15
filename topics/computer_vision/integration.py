"""Computer Vision — OpenCV / YOLO / SAM integrations."""
from __future__ import annotations


class ComputerVisionTopic:
    name = "computer_vision"
    tools = ["opencv", "yolo", "sam", "deepface", "insightface", "bytetrack", "mmdetection"]

    def detect_objects(self, image_path: str, model: str = "yolov8n") -> list:
        try:
            from ultralytics import YOLO
            model_obj = YOLO(model)
            results = model_obj(image_path)
            return [r.boxes.data.tolist() for r in results]
        except ImportError:
            return [{"error": "ultralytics not installed"}]
