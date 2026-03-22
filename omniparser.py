"""
OmniParser v2 wrapper for the desktop-control skill.

Uses:
- YOLOv8 (icon_detect/model.pt) for bounding box detection
- Florence-2 fine-tuned (icon_caption) for labeling each element
- easyocr for text extraction

Returns a list of dicts: {label, bbox, center_x, center_y, confidence}
"""

import os
import sys
import time
import warnings
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image
import torch
import numpy as np

MODEL_DIR = Path(os.environ.get("OMNIPARSER_MODEL_DIR",
    Path.home() / ".openclaw/models/omniparser"))
FLORENCE_PROC_DIR = Path(os.environ.get("FLORENCE_PROC_DIR",
    Path.home() / ".openclaw/models/florence2-base"))

ICON_DETECT_MODEL = MODEL_DIR / "icon_detect" / "model.pt"
ICON_CAPTION_MODEL = MODEL_DIR / "icon_caption"

_yolo_model = None
_caption_model = None
_caption_processor = None
_ocr_reader = None


def _load_yolo():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        _yolo_model = YOLO(str(ICON_DETECT_MODEL))
    return _yolo_model


def _load_caption_model():
    global _caption_model, _caption_processor
    if _caption_model is None:
        from transformers import AutoProcessor, AutoModelForCausalLM
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        dtype = torch.float16 if device == "mps" else torch.float32

        # Use the base Florence-2 processor (has tokenizer/image processor)
        # but load the fine-tuned OmniParser caption weights
        _caption_processor = AutoProcessor.from_pretrained(
            str(FLORENCE_PROC_DIR), trust_remote_code=True
        )
        _caption_model = AutoModelForCausalLM.from_pretrained(
            str(ICON_CAPTION_MODEL), trust_remote_code=True, torch_dtype=dtype
        ).to(device)
        _caption_model.eval()
    return _caption_model, _caption_processor


def _load_ocr():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            _ocr_reader = easyocr.Reader(["en"], gpu=torch.backends.mps.is_available())
        except ImportError:
            _ocr_reader = None
    return _ocr_reader


def _caption_batch(crops: List[Image.Image]) -> List[str]:
    """Caption a batch of image crops using Florence-2."""
    model, processor = _load_caption_model()
    device = next(model.parameters()).device
    dtype = next(model.parameters()).dtype

    prompt = "<CAPTION>"
    labels = []

    # Process in batches of 16
    batch_size = 16
    for i in range(0, len(crops), batch_size):
        batch = crops[i:i + batch_size]
        try:
            inputs = processor(
                images=batch,
                text=[prompt] * len(batch),
                return_tensors="pt",
                do_resize=False,
            ).to(device=device, dtype=dtype)

            with torch.no_grad():
                generated = model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=64,
                    do_sample=False,
                )
            texts = processor.batch_decode(generated, skip_special_tokens=True)
            labels.extend([t.strip() for t in texts])
        except Exception as e:
            # Fallback: label as unknown
            labels.extend([f"element" for _ in batch])

    return labels


def detect_elements(
    image_path: str,
    caption: bool = True,
    box_threshold: float = 0.05,
    iou_threshold: float = 0.7,
) -> List[Dict]:
    """
    Run OmniParser v2 on a screenshot.

    Args:
        image_path: Path to screenshot PNG/JPEG
        caption: Whether to generate text captions (slower but needed for find_element)
        box_threshold: YOLO confidence threshold
        iou_threshold: NMS IOU threshold

    Returns:
        List of dicts: {label, bbox, center_x, center_y, confidence}
        bbox is [x1, y1, x2, y2] in pixels
    """
    t0 = time.time()
    image = Image.open(image_path).convert("RGB")
    w, h = image.size

    # 1. YOLO detection
    yolo = _load_yolo()
    results = yolo(image, conf=box_threshold, iou=iou_threshold, verbose=False)
    boxes_data = results[0].boxes

    if boxes_data is None or len(boxes_data) == 0:
        return []

    xyxy = boxes_data.xyxy.cpu().numpy()
    confs = boxes_data.conf.cpu().numpy()

    elements = []
    crops = []

    for i, (box, conf) in enumerate(zip(xyxy, confs)):
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        # Clamp to image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        if x2 <= x1 or y2 <= y1:
            continue

        crop = image.crop((x1, y1, x2, y2))
        # Resize crop to 64x64 for Florence-2 (consistent size)
        crop_resized = crop.resize((64, 64), Image.LANCZOS)
        crops.append(crop_resized)

        elements.append({
            "label": f"element_{i}",
            "bbox": [x1, y1, x2, y2],
            "center_x": (x1 + x2) // 2,
            "center_y": (y1 + y2) // 2,
            "confidence": float(conf),
        })

    # 2. Caption each element
    if caption and crops:
        labels = _caption_batch(crops)
        for elem, label in zip(elements, labels):
            if label and label != "unanswerable" and len(label) > 1:
                elem["label"] = label

    # 3. OCR — add text regions not captured by YOLO
    ocr = _load_ocr()
    if ocr is not None:
        try:
            import numpy as np
            ocr_results = ocr.readtext(np.array(image))
            for (bbox_pts, text, conf) in ocr_results:
                if conf < 0.5 or not text.strip():
                    continue
                pts = np.array(bbox_pts)
                x1, y1 = int(pts[:, 0].min()), int(pts[:, 1].min())
                x2, y2 = int(pts[:, 0].max()), int(pts[:, 1].max())
                elements.append({
                    "label": text.strip(),
                    "bbox": [x1, y1, x2, y2],
                    "center_x": (x1 + x2) // 2,
                    "center_y": (y1 + y2) // 2,
                    "confidence": float(conf),
                    "source": "ocr",
                })
        except Exception:
            pass

    elapsed = time.time() - t0
    return elements
