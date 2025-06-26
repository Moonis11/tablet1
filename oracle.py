import cv2
import easyocr
import numpy as np
import re

reader = easyocr.Reader(['en', 'ru'], gpu=False)

def preprocess_image(pil_image):
    """PIL rasmni oq-qora qilib, binarizatsiya qiladi"""
    image = np.array(pil_image.convert("RGB"))  # PIL -> NumPy
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    return binary

def extract_drug_info_by_cropping(pil_image):
    # PIL -> NumPy (OpenCV format BGR)
    image = np.array(pil_image.convert("RGB"))
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    # EasyOCR orqali matnlarni o'qish
    results = reader.readtext(image)

    if not results:
        return "", 0  # Agar hech narsa topilmasa

    data = []
    for (box, text, conf) in results:
        top = int(box[0][1])
        bottom = int(box[2][1])
        left = int(box[0][0])
        right = int(box[1][0])
        height = bottom - top
        width = right - left
        area = height * width
        center_y = (top + bottom) / 2
        data.append({
            'text': text,
            'height': height,
            'area': area,
            'center_y': center_y,
            'top': top,
            'bottom': bottom,
            'left': left,
            'right': right,
            'conf': conf
        })

    # Eng katta hajmdagi yoki balandlikdagi matnni topamiz (tartiblash)
    data.sort(key=lambda x: (x['height'] * 0.6 + x['area'] * 0.4), reverse=True)
    drug_name_data = data[0]
    raw_drug_name = drug_name_data['text']
    confidence = int(drug_name_data['conf'] * 100)

    # Dorining nomini filtrlaymiz: faqat harflar va raqamlar, kamida 2 harfli so'zlar
    # Katta harflar va raqamlarni olamiz (yoki sizga moslab o'zgartiring)
    words = re.findall(r'\b[A-Za-zА-Яа-яЁё0-9]{2,}\b', raw_drug_name)
    drug_name = " ".join(words).strip()

    return drug_name, confidence
