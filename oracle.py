import cv2
import easyocr
import numpy as np
import re

reader = easyocr.Reader(['en', 'ru'], gpu=False)

def extract_drug_info_by_cropping(pil_image):
    image = np.array(pil_image.convert("RGB"))  # PIL -> NumPy
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)  # OpenCV format

    results = reader.readtext(image)

    data = []
    for (box, text, conf) in results:
        top = int(box[0][1])
        bottom = int(box[2][1])
        height = bottom - top
        area = height * (box[1][0] - box[0][0])
        data.append({
            'text': text,
            'height': height,
            'area': area,
            'conf': conf
        })

    if not data:
        return "", 0

    # Eng katta va balandligi bo'yicha topilgan matnni tanlaymiz
    data.sort(key=lambda x: (x['height'] * 0.6 + x['area'] * 0.4), reverse=True)
    drug_name_data = data[0]
    raw_drug_name = drug_name_data['text']
    confidence = int(drug_name_data['conf'] * 100)

    # Faol dori nomi sifatida faqat katta harflar so'zlarini ajratib olish
    words = re.findall(r'\b[A-ZА-ЯЁ]{2,}\b', raw_drug_name.upper())
    drug_name = " ".join(words)

    return drug_name, confidence
