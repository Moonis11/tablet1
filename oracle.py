import easyocr
import numpy as np
from PIL import Image
import cv2

reader = easyocr.Reader(['en', 'ru'], gpu=False)

def extract_drug_info_by_cropping(pil_image):
    # PIL rasmni OpenCV formatga o'tkazish
    image = np.array(pil_image.convert("RGB"))
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    results = reader.readtext(image)

    if not results:
        return "", 0

    # Eng kattasi va aniqrog'ini tanlash
    data = []
    for (bbox, text, prob) in results:
        x_min = min([point[0] for point in bbox])
        x_max = max([point[0] for point in bbox])
        y_min = min([point[1] for point in bbox])
        y_max = max([point[1] for point in bbox])
        height = y_max - y_min
        width = x_max - x_min
        area = height * width
        data.append({
            "text": text,
            "prob": prob,
            "area": area
        })
    # Eng katta maydonli va yuqori aniqlikdagi text
    data.sort(key=lambda x: (x["area"] * 0.7 + x["prob"] * 100 * 0.3), reverse=True)
    best = data[0]
    return best["text"], int(best["prob"] * 100)
