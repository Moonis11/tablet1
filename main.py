from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import re
import pandas as pd
from oracle import extract_drug_info_by_cropping

app = FastAPI()

# 🔓 CORS – frontend uchun ruxsat
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "🧪 Tablet API ishlamoqda. POST /analyze/ endpointdan foydalaning."}


# 📦 CSV faylni yuklash va ustun nomlarini tozalash
def load_csv():
    df = pd.read_csv("alternativa1.csv", encoding="utf-8")
    df.columns = df.columns.str.strip()  # Ustun nomlaridagi bo‘sh joylarni olib tashlash
    if 'Asl dorining nomi' not in df.columns:
        raise ValueError("CSV faylda 'Asl dorining nomi' ustuni topilmadi.")
    return df.dropna(how='all', axis=1)  # Faqat bo‘sh ustunlar bo‘lsa, olib tashlash


# 🔍 Dori nomini tozalash
def clean_drug_name(raw_name):
    return re.split(r"®", raw_name)[0].strip()


# 🔤 Kirilldan lotinga transliteratsiya
def transliterate_ru_to_lat(text):
    ru_to_lat = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z','и':'i','й':'y',
        'к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f',
        'х':'x','ц':'ts','ч':'ch','ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
        'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'Yo','Ж':'Zh','З':'Z','И':'I','Й':'Y',
        'К':'K','Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F',
        'Х':'X','Ц':'Ts','Ч':'Ch','Ш':'Sh','Щ':'Shch','Ъ':'','Ы':'Y','Ь':'','Э':'E','Ю':'Yu','Я':'Ya'
    }
    return ''.join(ru_to_lat.get(c, c) for c in text)


# 🧠 CSVdan kerakli dori ma'lumotlarini topish
def get_drug_info_from_csv(user_dori, df):
    user_dori = user_dori.strip().lower()

    # Yordamchi ustunlar
    df['Asl dorining nomi lower'] = df['Asl dorining nomi'].astype(str).str.strip().str.lower()
    df['Tasir etuvchi modda lower'] = df['Tasir etuvchi modda'].astype(str).str.strip().str.lower()

    # Asosiy dori bo‘yicha qator
    if user_dori not in df['Asl dorining nomi lower'].values:
        return None

    row = df[df['Asl dorining nomi lower'] == user_dori].iloc[0]
    
    tasir_modda = row['Tasir etuvchi modda'].strip().lower()
    alternativalar = df[
        (df['Tasir etuvchi modda lower'] == tasir_modda) &
        (df['Asl dorining nomi lower'] != user_dori)
    ][['Asl dorining nomi', 'Tasir etuvchi modda', 'Ishlab chiqargan mamlakat nomi']]

    return {
        "drug_name": user_dori,
        "kasalliklar": row.get('Qaysi kasalliklarda qo‘llaniladi', ''),
        "instruksiya": row.get('Instruksiya (foydalanish tartibi)', ''),
        "tasir_modda": tasir_modda,
        "alternativalar": alternativalar.to_dict(orient="records")
    }


# 📸 API endpoint: rasmni qabul qilib, dori ma’lumotini chiqaradi
@app.post("/analyze/")
async def analyze_image(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    # OCR model orqali dori nomini aniqlash
    raw_name = extract_drug_info_by_cropping(image)
    cleaned = clean_drug_name(raw_name)

    # Kirillmi? Lotinga aylantiramiz
    has_cyrillic = bool(re.search('[\u0400-\u04FF]', cleaned))
    if has_cyrillic:
        drug_name = transliterate_ru_to_lat(cleaned).lower()
    else:
        drug_name = cleaned.lower()

    # CSV orqali izlash
    try:
        df = load_csv()
        info = get_drug_info_from_csv(drug_name, df)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    if not info:
        return {
            "status": "not_found",
            "original_name": cleaned,
            "latin_name": drug_name
        }

    return {
        "status": "found",
        "original_name": cleaned,
        "latin_name": drug_name,
        **info
    }
