import streamlit as st
import pandas as pd
from PIL import Image, ExifTags
from oracle import extract_drug_info_by_cropping

import re
from difflib import get_close_matches
import traceback

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
    if 'Asl dorining nomi' not in df.columns:
        raise ValueError("❌ CSV faylda 'Asl dorining nomi' ustuni topilmadi.")
    return df

def fuzzy_match_drug_name(drug_name, df):
    all_drugs = df['Asl dorining nomi lower'].tolist()
    match = get_close_matches(drug_name.lower(), all_drugs, n=1, cutoff=0.7)
    return match[0] if match else None

def get_drug_info_from_csv(user_dori, df, lang):
    user_dori = user_dori.strip().lower()
    df['Asl dorining nomi lower'] = df['Asl dorining nomi'].astype(str).str.strip().str.lower()
    df['Tasir etuvchi modda lower'] = df['Tasir etuvchi modda'].astype(str).str.strip().str.lower()

    if user_dori not in df['Asl dorining nomi lower'].values:
        fuzzy_match = fuzzy_match_drug_name(user_dori, df)
        if fuzzy_match:
            user_dori = fuzzy_match
        else:
            return None

    row = df[df['Asl dorining nomi lower'] == user_dori].iloc[0]

    if lang == "ru":
        kasalliklar = row.get("Qaysi kasalliklarda qo‘llaniladi rus", "")
        instruktsiya = row.get("Instruksiya (foydalanish tartibi  rus", "")
        form_col = "Dori shakli ruscha"
        country_col = "Ishlab chiqargan mamlakat nomi rus"
    elif lang == "en":
        kasalliklar = row.get("Qaysi kasalliklarda qo‘llaniladi eng", "")
        instruktsiya = row.get("Instruksiya (foydalanish tartibi)  eng", "")
        form_col = "Dori shakli eng"
        country_col = "Ishlab chiqargan mamlakat nomi eng"
    else:
        kasalliklar = row.get("Qaysi kasalliklarda qo‘llaniladi", "")
        instruktsiya = row.get("Instruksiya (foydalanish tartibi)", "")
        form_col = "Dori shakli"
        country_col = "Ishlab chiqargan mamlakat nomi"

    tasir_modda = row.get('Tasir etuvchi modda', '').strip().lower()
    narx = row.get('Narxi (taxminiy)', '')

    alternativalar = df[
        (df['Tasir etuvchi modda lower'] == tasir_modda) &
        (df['Asl dorining nomi lower'] != user_dori)
    ][[
        'Asl dorining nomi',
        'Tasir etuvchi modda',
        form_col,
        country_col,
        'Narxi (taxminiy)'
    ]].rename(columns={
        form_col: "Dori shakli",
        country_col: "Ishlab chiqargan mamlakat nomi"
    })

    return user_dori, kasalliklar, instruktsiya, alternativalar, tasir_modda, narx

def clean_drug_name(raw_name):
    cleaned = re.split(r"[\u00AE\u00A9\u2122]", raw_name)[0].strip()
    cleaned = re.sub(r"[^a-zA-Zа-яА-ЯёЁ0-9\- ]", "", cleaned)
    return cleaned

def transliterate_ru_to_lat(text):
    ru_to_lat = {...}  # same as before, omitted for brevity
    return ''.join(ru_to_lat.get(c, c) for c in text)

def section_title(title_text):
    st.markdown(f"""<div style='...'>{title_text}</div>""", unsafe_allow_html=True)

languages = {"🇺🇿 Uzbek": "uz", "🇷🇺 Русский": "ru", "en English": "en"}
translations = {...}  # same as before, omitted for brevity

st.set_page_config(page_title="Tablet App", layout="wide")
st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)

lang_choice = st.sidebar.radio("Til / Язык / Language  :", list(languages.keys()))
lang = languages[lang_choice]

uploaded_file = st.file_uploader(label="", type=["jpg", "jpeg", "png", "jfif"], label_visibility="collapsed")

if uploaded_file:
    try:
        image = Image.open(uploaded_file)
        image = resize_image(image)
        image = fix_orientation(image)

        col1, col2 = st.columns([1, 2], gap="large")
        with col1:
            st.image(image, caption="📸", use_container_width=True)

        with col2:
            with st.spinner(translations["detecting"][lang]):
                drug_text, confidence = extract_drug_info_by_cropping(image)
                cleaned = clean_drug_name(drug_text)
                has_cyrillic = bool(re.search('[\u0400-\u04FF]', cleaned))

                if has_cyrillic:
                    drug_name_lat = transliterate_ru_to_lat(cleaned)
                    drug_name_display = f"{cleaned} ({drug_name_lat})"
                    drug_name = drug_name_lat.lower()
                else:
                    drug_name_display = cleaned
                    drug_name = cleaned.lower()

                df = load_csv()
                drug_info = get_drug_info_from_csv(drug_name, df, lang)

                if drug_info:
                    nomi, kasallik, instruktsiya, alternativalar, tasir_modda, narx = drug_info
                    narx_html = f"<span style='color:#ffffff; font-weight:600;'>💵 Narx: {narx}</span>" if narx else ""
                    st.markdown(f"<div style='...'>💊 Dori nomi: {drug_name_display.upper()}</div>", unsafe_allow_html=True)

                    st.markdown(f"<div style='font-size: 13px; color: #b0b0b0;'>{translations['detecting'][lang]} OCR aniqlik darajasi: {confidence}%</div>", unsafe_allow_html=True)

                    section_title(translations["alt_drugs"][lang])
                    st.dataframe(
                        alternativalar.rename(columns={
                            "Asl dorining nomi": "Drug",
                            "Tasir etuvchi modda": "Ingredient",
                            "Dori shakli": "Form",
                            "Ishlab chiqargan mamlakat nomi": "Country",
                            "Narxi (taxminiy)": "Price"
                        }),
                        use_container_width=True,
                        height=220
                    )

                    section_title(translations["illness"][lang])
                    st.write(kasallik)

                    section_title(translations["usage"][lang])
                    formatted_instruksiya = "\n".join([f"- {line.strip()}" for line in instruktsiya.split("\n") if line.strip()])
                    st.markdown(formatted_instruksiya)
                else:
                    st.warning(translations["not_found"][lang])

    except Exception as e:
        st.error(f"Xatolik yuz berdi: {e}")
        st.text(traceback.format_exc())
else:
    st.info(translations["upload_label"][lang])
