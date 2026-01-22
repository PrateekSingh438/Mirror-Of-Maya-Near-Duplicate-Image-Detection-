# Minimal data loader
from PIL import Image
import numpy as np

def load_image(path):
    try:
        return Image.open(path).convert("RGB")
    except:
        return None