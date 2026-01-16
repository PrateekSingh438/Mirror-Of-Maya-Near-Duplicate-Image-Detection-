import cv2
import numpy as np
from PIL import Image

def get_tta_views(image_path):
    try:
        pil_img = Image.open(image_path).convert("RGB")
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        views = []
        
        views.append(pil_img)
        
        blur_img = cv2.GaussianBlur(cv_img, (5, 5), 0)
        views.append(Image.fromarray(cv2.cvtColor(blur_img, cv2.COLOR_BGR2RGB)))
        
        gray_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        gray_rgb = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2RGB)
        views.append(Image.fromarray(gray_rgb))
        
        return views
        
    except Exception:
        return None
