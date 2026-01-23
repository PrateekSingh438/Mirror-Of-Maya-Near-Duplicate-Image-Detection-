"""Minimal data loader utilities"""
from PIL import Image

def load_image(path):
    """Load image as RGB PIL Image"""
    try:
        return Image.open(path).convert("RGB")
    except:
        return None