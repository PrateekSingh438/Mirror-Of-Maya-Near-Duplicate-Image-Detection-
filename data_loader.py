import cv2
import numpy as np
from PIL import Image
import config

def get_tta_views(image_path):
    
    try:
        pil_img = Image.open(image_path).convert("RGB")
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        views = []
        
        # Original view
        views.append(pil_img)
        
        # Blurred view
        blur_img = cv2.GaussianBlur(
            cv_img, 
            config.GAUSSIAN_BLUR_KERNEL, 
            config.GAUSSIAN_BLUR_SIGMA
        )
        views.append(Image.fromarray(cv2.cvtColor(blur_img, cv2.COLOR_BGR2RGB)))
        
        # Grayscale view
        gray_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        gray_rgb = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2RGB)
        views.append(Image.fromarray(gray_rgb))
        
        return views
        
    except Exception:
        return None