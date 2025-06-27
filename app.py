import streamlit as st
import pandas as pd
from PIL import Image, ExifTags
from oracle import extract_drug_info_by_cropping
import re
from difflib import get_close_matches
import traceback
import streamlit.components.v1 as components
import os
from datetime import datetime

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


# CSV yuklash

@st.cache_data
def load_drug_names():
    df = pd.read_csv("alternativa1.csv")
    return df["Asl dorining nomi"].str.lower().str.strip().tolist()


drug_names = load_drug_names()





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

    # Tilga qarab ustunlarni tanlash
    if lang == "ru":
        kasallik = row.get("Qaysi kasalliklarda qo‘llaniladi rus", "")
        instruktsiya = row.get("Instruksiya (foydalanish tartibi  rus", "")
        form_col = "Dori shakli ruscha"
        country_col = "Ishlab chiqargan mamlakat nomi rus"
    elif lang == "en":
        kasallik = row.get("Qaysi kasalliklarda qo‘llaniladi eng", "")
        instruktsiya = row.get("Instruksiya (foydalanish tartibi)  eng", "")
        form_col = "Dori shakli eng"
        country_col = "Ishlab chiqargan mamlakat nomi eng"
    else:
        kasallik = row.get("Qaysi kasalliklarda qo‘llaniladi", "")
        instruktsiya = row.get("Instruksiya (foydalanish tartibi)", "")
        form_col = "Dori shakli"
        country_col = "Ishlab chiqargan mamlakat nomi"

    nomi = row.get("Asl dorining nomi", "")
    narx = row.get("Narxi (taxminiy)", "")
    tasir_modda = row.get("Tasir etuvchi modda", "").strip().lower()

    # Agar form_col yoki country_col CSVda mavjud bo‘lmasa, xatolik bermasligi uchun tekshiramiz
    if form_col not in df.columns or country_col not in df.columns:
        form_col = "Dori shakli"
        country_col = "Ishlab chiqargan mamlakat nomi"

    alternativalar = df[
        (df['Tasir etuvchi modda lower'] == tasir_modda) &
        (df['Asl dorining nomi lower'] != user_dori)
    ][[
        "Asl dorining nomi", "Tasir etuvchi modda", form_col, country_col, "Narxi (taxminiy)"
    ]].rename(columns={
        form_col: "Dori shakli",
        country_col: "Mamlakat"
    })

    return nomi, kasallik, instruktsiya, alternativalar, narx


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

if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

st.set_page_config(page_title="Tablet App", layout="wide")
st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)

languages = {"Uzbek": "uz", "Русский": "ru", "English": "en"}
translations = {
    "title": {"uz": "🧪 TabletAI", "ru": "🧪 ТаблетAI", "en": "🧪 TabletAI"},
    "upload_label": {"uz": "Rasm yuklang", "ru": "Загрузите изображение", "en": "Upload an image"},
    "detecting": {"uz": "🔍 Dori nomi aniqligi...", "ru": "🔍 Точность названия препарата...", "en": "🔍 Drug name accuracy..."},
    "not_found": {"uz": "💬 Oops! Izlangan dori vositasi bazamizda hozircha yo‘q. Lekin tizim muntazam yangilanmoqda. Keyinroq yana urinib ko‘ring.", "ru": "💬 Упс! Искомое лекарство пока отсутствует в нашей базе данных. Но система регулярно обновляется. Попробуйте позже.",
                  "en": "💬 Oops! The medicine you're looking for is not yet in our database. But the system is constantly being updated. Please try again later."},
    "alt_drugs": {"uz": "🔄 Alternativ dorilar", "ru": "🔄 Альтернативные лекарства", "en": "🔄 Alternative Drugs"},
    "illness": {"uz": "📋 Davolash uchun mo‘ljallangan holatlar", "ru": "📋 Состояния, для которых предназначено лечение", "en": "📋 Conditions targeted for treatment"},
    "usage": {"uz": "🧾 Instruksiya", "ru": "🧾 Инструкция", "en": "🧾 Instructions"},
    "not_detected": {"uz": "❗ Dori nomi aniqlanmadi. Rasmni aniqroq yuklang.", "ru": "❗ Не удалось определить название. Загрузите более чёткое изображение.", "en": "❗ Could not detect the drug name. Please upload a clearer image."},
    "disclaimer": {"uz": "📌 Diqqat: Bu dastur tibbiy maslahat o‘rnini bosa olmaydi...", "ru": "📌 Внимание: Это приложение не заменяет консультацию врача...", "en": "📌 Note: This app does not replace medical advice..."},
    "price_label": {"uz": "💵 Narxi", "ru": "💵 Цена", "en": "💵 Price"},
    "drug_name": {"uz": "💊 Dori nomi", "ru": "💊 Название препарата", "en": "💊 Drug name"}
}

lang_choice = st.sidebar.radio("Til / Язык / Language:", list(languages.keys()))
lang = languages[lang_choice]
st.title(translations["title"][lang])

uploaded_file = st.file_uploader(translations["upload_label"][lang], type=["jpg", "jpeg", "png"])

if uploaded_file:
    try:
        image = Image.open(uploaded_file)
        image = resize_image(image)
        image = fix_orientation(image)

        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(image, caption="📸", use_container_width=True)

        with col2:
            with st.spinner(translations["detecting"][lang]):
                drug_text, confidence = extract_drug_info_by_cropping(image)
                cleaned = clean_drug_name(drug_text)
                has_cyrillic = bool(re.search('[\u0400-\u04FF]', cleaned))
                drug_name = transliterate_ru_to_lat(cleaned) if has_cyrillic else cleaned

                df = pd.read_csv("alternativa1.csv")
                result = get_drug_info_from_csv(drug_name, df, lang)


                if result:
                    nomi, kasallik, instruktsiya, alternativalar, narx = result

                    # 💊 Dori nomi + 💵 Narxi (qoramtir yashil fon)
                    components.html(f"""
                        <div style="
                           display: flex;
                           flex-wrap: wrap;
                           justify-content: space-between;
                           align-items: center;
                           background-color: #123024;
                           color: white;
                           padding: 16px 24px;
                           border-radius: 12px;
                           font-family: 'Segoe UI', sans-serif;
                           font-weight: 600;
                           margin-top: 20px;
                           margin-bottom: 4px;
                        ">
                            <div style="font-size: 20px; flex: 1 1 200px;">
                                 {translations["drug_name"][lang]}: {nomi}
                            </div>
                            <div style="font-size: 18px; flex: 1 1 100px; text-align: right;">
                                 {translations["price_label"][lang]}: {narx}
                            </div>
                            <div style="width: 100%; font-size: 16px; margin-top: 10px; display: none;" class="mobile-price">
                                 {translations["price_label"][lang]}: {narx}
                            </div>
                        </div>
                        <style>
                            @media only screen and (max-width: 768px) {{
                                .mobile-price {{
                                    display: block !important;
                                }}
                                div[style*="display: flex;"] > div:nth-child(2) {{
                                    display: none !important;
                                }}
                            }}
                        </style>
                    """, height=130)

                    # 🔍 OCR aniqlik (dori nomining tagiga chiqadi)
                    st.markdown(f"<div style='color:#999;font-size:13px;margin-top:-10px;'>{translations['detecting'][lang].split('...')[0]}: {confidence}%</div>", unsafe_allow_html=True)

                    # 🔄 Alternativ dorilar
                    section_title(translations["alt_drugs"][lang])
                    alternativalar.index = range(1, len(alternativalar) + 1)
                    st.dataframe(alternativalar, use_container_width=True, height=250)

                    # 📋 Kasalliklar
                    section_title(translations["illness"][lang])
                    st.write(kasallik)

                    # 🧾 Instruksiya (har bir qator `.` bilan ajralgan)
                    section_title(translations["usage"][lang])
                    formatted_instruksiya = "<br>".join([re.sub(r"^(➤|\d+[\.\)]|\-|\•)?\s*", "", line).rstrip('.') + "." for line in instruktsiya.split("\n") if line.strip()])
                    st.markdown(formatted_instruksiya, unsafe_allow_html=True)

                    # 📌 Diskleymer
                    st.markdown(f"""
                        <div style='
                            width: 100%;
                            margin: 40px auto 20px auto;
                            padding: 18px 24px;
                            background-color: #123024;
                            color: #ffffff;
                            font-size: 17px;
                            font-weight: 600;
                            border-radius: 12px;
                            font-family: "Segoe UI", Tahoma, sans-serif;
                            text-align: center;
                            box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.1);
                        '>
                            {translations['disclaimer'][lang]}
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning(translations["not_found"][lang])

    except Exception as e:
        st.error(f"Xatolik: {e}")
        st.text(traceback.format_exc())
