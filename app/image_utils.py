import cv2
import numpy as np
import io
from typing import List, Tuple, Optional

def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """Load image from bytes into OpenCV format."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def encode_image_to_bytes(image: np.ndarray) -> bytes:
    """Encodes OpenCV image to bytes (JPEG)."""
    success, encoded_image = cv2.imencode('.jpg', image)
    return encoded_image.tobytes()
