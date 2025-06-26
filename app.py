import streamlit as st
import pandas as pd
from oracle import extract_drug_info_by_cropping
from PIL import Image
import re
from difflib import get_close_matches

st.set_page_config(page_title="Tablet App", layout="wide")

# Til sozlamalari
languages = {
    "🇺🇿 Uzbek": "uz",
    "🇷🇺 Русский": "ru",
    "en English": "en"
}

translations = {
    "title": {
        "uz": "🧪 Tablet: Dori rasmi orqali aniqlash",
        "ru": "🧪 Таблет: Распознавание лекарства по фото",
        "en": "🧪 Tablet: Drug Recognition by Image"
    },
    "upload_label": {
        "uz": "Rasm yuklang",
        "ru": "Загрузите изображение",
        "en": "Upload an image"
    },
    "detecting": {
        "uz": "🔍 Dori nomi aniqlanmoqda...",
        "ru": "🔍 Определение названия лекарства...",
        "en": "🔍 Detecting drug name..."
    },
    "not_found": {
        "uz": "❗ Bu dori CSVda topilmadi.",
        "ru": "❗ Это лекарство не найдено в таблице.",
        "en": "❗ This drug was not found in the database."
    },
    "drug_label": {
        "uz": "💊 Dori nomi",
        "ru": "💊 Название лекарства",
        "en": "💊 Drug Name"
    },
    "alt_drugs": {
        "uz": "🔄 Alternativ dorilar (mamlakati bilan)",
        "ru": "🔄 Альтернативные лекарства (с указанием страны)",
        "en": "🔄 Alternative Drugs (with country)"
    },
    "illness": {
        "uz": "📋 Qaysi kasalliklarda qo‘llaniladi",
        "ru": "📋 При каких болезнях используется",
        "en": "📋 Conditions Treated"
    },
    "usage": {
        "uz": "💊 Instruksiya",
        "ru": "💊 Инструкция",
        "en": "💊 Instructions"
    },
    "not_detected": {
        "uz": "❗ Dori nomi aniqlanmadi. Rasmni aniqroq yuklang.",
        "ru": "❗ Не удалось определить название. Загрузите более чёткое изображение.",
        "en": "❗ Could not detect the drug name. Please upload a clearer image."
    }
}

lang_choice = st.sidebar.radio("Til / Язык / Language  :", list(languages.keys()))
lang = languages[lang_choice]

st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)

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

def get_drug_info_from_csv(user_dori, df):
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

    kasalliklar = row.get('Qaysi kasalliklarda qo‘llaniladi', '')
    instruktsiya = row.get('Instruksiya (foydalanish tartibi)', '')
    tasir_modda = row.get('Tasir etuvchi modda', '').strip().lower()
    narx = row.get('Narxi (taxminiy)', '')

    alternativalar = df[
        (df['Tasir etuvchi modda lower'] == tasir_modda) &
        (df['Asl dorining nomi lower'] != user_dori)
    ][[
        'Asl dorining nomi',
        'Tasir etuvchi modda',
        'Dori shakli',
        'Ishlab chiqargan mamlakat nomi',
        'Narxi (taxminiy)'
    ]]

    return user_dori, kasalliklar, instruktsiya, alternativalar, tasir_modda, narx

def clean_drug_name(raw_name):
    cleaned = re.split(r"[\u00AE\u00A9\u2122]", raw_name)[0].strip()
    cleaned = re.sub(r"[^a-zA-Zа-яА-ЯёЁ0-9\- ]", "", cleaned)
    return cleaned

def transliterate_ru_to_lat(text):
    ru_to_lat = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z',
        'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
        'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh',
        'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z',
        'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R',
        'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'X', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh',
        'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    return ''.join(ru_to_lat.get(c, c) for c in text)

def section_title(title_text):
    st.markdown(
        f"""
        <div style='background-color: #123024; color: white; padding: 10px 15px; font-size: 20px; font-weight: bold; border-radius: 6px; margin-top: 20px;'>
            {title_text}
        </div>
        """,
        unsafe_allow_html=True
    )

st.title(translations["title"][lang])
uploaded_file = st.file_uploader(label="", type=["jpg", "jpeg", "png", "jfif"], label_visibility="collapsed")

if uploaded_file:
    image = Image.open(uploaded_file)
    col1, col2 = st.columns([1, 2], gap="large")

    with col1:
        st.image(image, caption="📸")

    with col2:
        with st.spinner(translations["detecting"][lang]):
            try:
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
                drug_info = get_drug_info_from_csv(drug_name, df)

                if drug_info:
                    nomi, kasallik, instruktsiya, alternativalar, tasir_modda, narx = drug_info
                else:
                    nomi = kasallik = instruktsiya = alternativalar = tasir_modda = narx = None

                narx_html = f"<span style='color:#ffffff;'>💵 Narx: {narx}</span>" if narx else ""
                st.markdown(
                    f"""
                    <div style='display: flex; justify-content: space-between; align-items: center; font-size: 22px; font-weight: 600; padding: 15px 8px; background-color: #013220; border-radius: 10px;'>
                        <span style='color:white;'>💊 Dori nomi: {drug_name_display.upper()}</span>
                        {narx_html}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"<div style='font-size: 14px; color: gray;'>OCR aniqlik darajasi: {confidence}%</div>",
                    unsafe_allow_html=True
                )

                if drug_info:
                    section_title(translations["alt_drugs"][lang])
                    alternativalar = alternativalar.reset_index(drop=True)
                    alternativalar.index += 1  # 1 dan boshlab raqamlash
                    st.dataframe(
                        alternativalar.rename(columns={
                            "Asl dorining nomi": "Drug",
                            "Tasir etuvchi modda": "Ingredient",
                            "Dori shakli": "Form",
                            "Ishlab chiqargan mamlakat nomi": "Country",
                            "Narxi (taxminiy)": "Price"
                        }),
                        use_container_width=True
                    )

                    section_title(translations["illness"][lang])
                    st.write(kasallik)

                    section_title(translations["usage"][lang])
                    formatted_instruksiya = "\n".join(
                        [f"- {line.strip()}" for line in instruktsiya.split("\n") if line.strip()]
                    )
                    st.markdown(formatted_instruksiya)
                else:
                    st.warning(translations["not_found"][lang])
            except Exception as e:
                st.error(f"❗ {e}")

    # Ogohlantirish
    st.markdown(
    """
    <div style='margin-top: 40px; padding: 15px; border-radius: 8px; background-color: #123024; color: #e8f5e9; font-size: 16px; border-left: 6px solid #4caf50;'>
        ⚠️ <strong>Ogohlantirish:</strong> Ilovada ko‘rsatilgan dori vositalari va ularning qo‘llanilishi faqat ma’lumot berish uchun. To‘g‘ri tashxis va davolash uchun shifokorga murojaat qiling.
    </div>
    """,
    unsafe_allow_html=True
)
else:
    st.info(translations["upload_label"][lang])
