from PIL import Image
def load_image(path):
    try:
        return Image.open(path).convert("RGB")
    except:
        return None