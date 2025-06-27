import streamlit as st
import pandas as pd
from PIL import Image, ExifTags
from oracle import extract_drug_info_by_cropping
import re
from difflib import get_close_matches
import traceback
import streamlit.components.v1 as components

MAX_SIZE = (1024, 1024)

def resize_image(img):
    img.thumbnail(MAX_SIZE)
    return img

def fix_orientation(img):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = img._getexif()
        if exif is not None:
            orientation_val = exif.get(orientation)
            if orientation_val == 3:
                img = img.rotate(180, expand=True)
            elif orientation_val == 6:
                img = img.rotate(270, expand=True)
            elif orientation_val == 8:
                img = img.rotate(90, expand=True)
    except Exception:
        pass
    return img

@st.cache_data
def load_csv():
    import os
    csv_path = "alternativa1.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ Fayl topilmadi: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8")
    df.columns = df.columns.str.strip()
    return df

def fuzzy_match_drug_name(drug_name, df):
    all_drugs = df['Asl dorining nomi'].astype(str).str.lower().tolist()
    match = get_close_matches(drug_name.lower(), all_drugs, n=1, cutoff=0.7)
    return match[0] if match else None

def get_drug_info_from_csv(user_dori, df, lang):
    user_dori = user_dori.strip().lower()
    df['Asl dorining nomi lower'] = df['Asl dorining nomi'].astype(str).str.lower()
    df['Tasir etuvchi modda lower'] = df['Tasir etuvchi modda'].astype(str).str.lower()

    if user_dori not in df['Asl dorining nomi lower'].values:
        fuzzy_match = fuzzy_match_drug_name(user_dori, df)
        if fuzzy_match:
            user_dori = fuzzy_match
        else:
            return None

    row = df[df['Asl dorining nomi lower'] == user_dori].iloc[0]

    if lang == "ru":
        nomi = row.get("Asl dorining nomi", "")
        kasallik = row.get("Qaysi kasalliklarda qo‘llaniladi rus", "")
        instruktsiya = row.get("Instruksiya (foydalanish tartibi  rus", "")
        form_col = "Dori shakli ruscha"
        country_col = "Ishlab chiqargan mamlakat nomi rus"
    elif lang == "en":
        nomi = row.get("Asl dorining nomi", "")
        kasallik = row.get("Qaysi kasalliklarda qo‘llaniladi eng", "")
        instruktsiya = row.get("Instruksiya (foydalanish tartibi)  eng", "")
        form_col = "Dori shakli eng"
        country_col = "Ishlab chiqargan mamlakat nomi eng"
    else:
        nomi = row.get("Asl dorining nomi", "")
        kasallik = row.get("Qaysi kasalliklarda qo‘llaniladi", "")
        instruktsiya = row.get("Instruksiya (foydalanish tartibi)", "")
        form_col = "Dori shakli"
        country_col = "Ishlab chiqargan mamlakat nomi"

    tasir_modda = row.get("Tasir etuvchi modda", "").strip().lower()
    narx = row.get("Narxi (taxminiy)", "")

    alternativalar = df[
        (df['Tasir etuvchi modda lower'] == tasir_modda) &
        (df['Asl dorining nomi lower'] != user_dori)
    ][[
        "Asl dorining nomi", "Tasir etuvchi modda",
        form_col, country_col, "Narxi (taxminiy)"
    ]].rename(columns={
        form_col: "Dori shakli",
        country_col: "Mamlakat"
    })

    return nomi, kasallik, instruktsiya, alternativalar, tasir_modda, narx

def clean_drug_name(raw_name):
    cleaned = re.split(r"[\u00AE\u00A9\u2122]", raw_name)[0].strip()
    cleaned = re.sub(r"[^a-zA-Zа-яА-ЯёЁ0-9\- ]", "", cleaned)
    return cleaned

def transliterate_ru_to_lat(text):
    ru_to_lat = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'X', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    return ''.join(ru_to_lat.get(c, c) for c in text)

def section_title(title_text):
    st.markdown(
        f"<div style='background-color: #123024; color: white; padding: 12px 18px; font-size: 18px; font-weight: 700; border-radius: 8px; margin-top: 25px; margin-bottom: 10px; font-family: Segoe UI;'>{title_text}</div>",
        unsafe_allow_html=True
    )

# 🔧 --- RASMNI YUKLASHNI YAXSHILASH (drag and drop yo'q, X tugmasi bor) ---
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

# Yashirish: Drag and drop qismi + fayl nomi
st.markdown("""
<style>
div[data-testid="stFileUploader"] > label {display: none;}
span[data-testid="stFileUploaderFileName"] {display: none;}
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Tablet App", layout="wide")
st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)

languages = {
    "🇺🇿 Uzbek": "uz",
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en"
}

translations = {
    "title": {"uz": "🧪 TabletAI", "ru": "🧪 ТаблетAI", "en": "🧪 TabletAI"},
    "upload_label": {"uz": "Rasm yuklang", "ru": "Загрузите изображение", "en": "Upload an image"},
    # ... [qolgan tarjimalar xuddi avvalgidek qoladi]
}

lang_choice = st.sidebar.radio("Til / Язык / Language:", list(languages.keys()))
lang = languages[lang_choice]
st.title(translations["title"][lang])

# Faqat bir martalik yuklash
if not st.session_state.uploaded_image:
    uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    if uploaded_file:
        st.session_state.uploaded_image = uploaded_file

if st.session_state.uploaded_image:
    # Continue app logic as before using st.session_state.uploaded_image instead of uploaded_file
    # Add "❌ O‘chirish" tugmasi
    col_reset, _ = st.columns([1, 5])
    with col_reset:
        if st.button("❌ Rasmni o‘chirish"):
            st.session_state.uploaded_image = None
            st.experimental_rerun()

    # Endi uploaded_file o‘rniga foydalanamiz:
    uploaded_file = st.session_state.uploaded_image
    # ... (qolgan rasmga oid kod davom etadi, sizdagi koddan aynan shu joyga qo‘shiladi)

else:
    st.info(translations["upload_label"][lang])
