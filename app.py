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
from difflib import get_close_matches
from io import BytesIO
import base64

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

def image_to_base64(image):
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()


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

    kirillcha_nomi = row.get("Asl dorining nomi (kiril)", "")
    lotincha_nomi = row.get("Asl dorining nomi", "")

    # Agar kirillcha yo‘q bo‘lsa, transliteratsiya qilib olamiz
    if not kirillcha_nomi:
       kirillcha_nomi = transliterate_lat_to_cyr(lotincha_nomi)

    nomi = f"{lotincha_nomi} / {kirillcha_nomi}"

    
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
    # 🔠 Lotincha / Кириллча ko‘rinishda chiqarish
    alternativalar["Asl dorining nomi"] = alternativalar["Asl dorining nomi"].apply(
    lambda x: f"{transliterate_lat_to_cyr(str(x))} / {x}" if not is_cyrillic(x) else f"{x} / {transliterate_ru_to_lat(str(x))}"
    )

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

def is_cyrillic(text):
    return any('а' <= c <= 'я' or 'А' <= c <= 'Я' for c in text)
def transliterate_lat_to_cyr(text):
    lat_to_cyr = {
        'shch': 'щ', 'yo': 'ё', 'yu': 'ю', 'ya': 'я', 'ch': 'ч', 'sh': 'ш', 'ts': 'ц',
        'a': 'а', 'b': 'б', 'd': 'д', 'e': 'е', 'f': 'ф', 'g': 'г', 'h': 'ҳ', 'i': 'и',
        'j': 'ж', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п', 'q': 'қ',
        'r': 'р', 's': 'с', 't': 'т', 'u': 'у', 'v': 'в', 'x': 'х', 'y': 'й', 'z': 'з',
        "'": 'ъ', 'ʼ': 'ъ', '’': 'ъ', '`': 'ъ'
    }

    specials = ['shch', 'yo', 'yu', 'ya', 'ch', 'sh', 'ts']
    i = 0
    result = ''
    while i < len(text):
        matched = False
        for s in specials:
            if text[i:i+len(s)].lower() == s:
                rep = lat_to_cyr[s]
                result += rep.upper() if text[i].isupper() else rep
                i += len(s)
                matched = True
                break
        if not matched:
            ch = text[i]
            rep = lat_to_cyr.get(ch.lower(), ch)
            result += rep.upper() if ch.isupper() else rep
            i += 1
    return result


def normalize_input(text):
    text = str(text).strip()
    text = re.sub(r'[\u200c\u202f\xa0\ufeff]+', '', text)  # noaniq belgilarni tozalash
    text = re.sub(r'\s+', '', text)  # bo‘sh joylarni olib tashlash

    if is_cyrillic(text):
        lotincha = transliterate_ru_to_lat(text)
        kirilcha = text
    else:
        kirilcha = transliterate_lat_to_cyr(text)
        lotincha = text

    return lotincha.lower(), kirilcha.capitalize()


def find_drug(drug_name, df):
    drug_name = normalize_input(drug_name)
    df['Asl dorining nomi'] = df['Asl dorining nomi'].astype(str).str.lower().str.strip()

    # Aniq moslik
    exact = df[df['Asl dorining nomi'] == drug_name]
    if not exact.empty:
        return exact

    # Yaqin moslik (ixtiyoriy)
    matches = get_close_matches(drug_name, df['Asl dorining nomi'].tolist(), n=1, cutoff=0.5)
    if matches:
        return df[df['Asl dorining nomi'] == matches[0]]

    return None

def section_title(title_text):
    st.markdown(
        f"<div style='background-color: #FDE9EA; color: white; padding: 12px 18px; font-size: 30px; font-weight: 700; border-radius: 8px; margin-top: 25px; margin-bottom: 10px; font-family: Segoe UI;'>{title_text}</div>",
        unsafe_allow_html=True
    )
   
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

st.set_page_config(page_title="Tablet App", layout="wide")
st.markdown("""
    <style>
        footer {visibility: hidden;}
        body, .stApp {
            background-color: white !important;
            color: black !important;
        }
        .stMarkdown div {
            color: black !important;
        }
    </style>
""", unsafe_allow_html=True)
st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)

is_mobile = st.sidebar.toggle("📱 Telefon holatida ko‘rsatish", value=False)
languages = {"Uzbek": "uz", "Русский": "ru", "English": "en"}
translations = {
    "title": {"uz": "🧪 TabletAI", "ru": "🧪 ТаблетAI", "en": "🧪 TabletAI"},
    "upload_label": {"uz": "Rasm yuklang", "ru": "Загрузите изображение", "en": "Upload an image"},
    "detecting": {"uz": "🔍 Dori nomi aniqligi...", "ru": "🔍 Точность названия препарата...", "en": "🔍 Drug name accuracy..."},
    "not_found": {"uz": "💬 Oops! Izlangan dori vositasi bazada hozircha yo‘q. Lekin tizim muntazam yangilanmoqda. Keyinroq yana urinib ko‘ring.", "ru": "💬 Упс! Искомое лекарство пока отсутствует в базa данных. Но система регулярно обновляется. Попробуйте позже.",
                  "en": "💬 Oops! The medicine you're looking for is not yet in database. But the system is constantly being updated. Please try again later."},
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



def clear_image():
    st.session_state.uploaded_image = None

def style_alternativalar(df):
    return df.style.set_properties(**{
        'background-color': 'white',
        'color': 'black'
    })
def render_alternativalar_html(df):
    df = df.reset_index(drop=True)
    html = df.to_html(classes='alt-table', border=1, justify='left', index=True)
    style = """
    <style>
        .alt-table {
            border-collapse: collapse;
            width: 100%;
            font-size: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: black;
        }
        .alt-table th, .alt-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        .alt-table thead th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .alt-table tbody tr:hover {
            background-color: #f5f5f5;
        }
    </style>
    """
    st.markdown(style + html, unsafe_allow_html=True)


if 'uploaded_image' not in st.session_state:
    st.session_state.uploaded_image = None
    st.title("Rasm yuklash va o'chirish")


if st.session_state.uploaded_image is None:
    uploaded_file = st.file_uploader("Rasm yuklang", type=["png", "jpg", "jpeg"])
    
    
    if uploaded_file is not None:
        st.session_state.uploaded_image = uploaded_file
        st.rerun()  # yoki st.rerun() sizning streamlit versiyangizga qarab



if st.session_state.uploaded_image is not None:
    try:
        image = Image.open(st.session_state.uploaded_image)
        image = resize_image(image)
        image = fix_orientation(image)
        
        img_base64 = image_to_base64(image)

        col0, col1, col2 = st.columns([0.05, 0.3, 0.7])

        with col0:
            clear_clicked = st.button("❌", key="clear_image_button")
            st.markdown("""
                <style>
                div[data-testid="stButton"] button {
                    margin-top: 7px;
                    background-color: white !important;
                    color: black !important;
                    border: 1px solid #ccc !important;
                    border-radius: 6px !important;
                        margin-top: 20px;
                }
                </style>
            """, unsafe_allow_html=True)

            if clear_clicked:
               st.session_state.uploaded_image = None
               st.rerun()

        # Rasmni ko‘rsatish
        with col1:
            st.markdown(f"""
                <div style="position: relative; display: inline-block; width: 100%;">
                    <img src="data:image/png;base64,{img_base64}" style="width: 100%; border-radius: 12px; margin-top: 20px;" />
                </div>
            """, unsafe_allow_html=True)

        # Ma'lumotlar ustuni
        with col2:
            with st.spinner(translations["detecting"][lang]):
                drug_text, confidence = extract_drug_info_by_cropping(image)
                cleaned = clean_drug_name(drug_text)
                has_cyrillic = bool(re.search('[\u0400-\u04FF]', cleaned))
                drug_name = transliterate_ru_to_lat(cleaned) if has_cyrillic else cleaned

                df = pd.read_csv("alternativa1.csv")
                result = get_drug_info_from_csv(drug_name, df, lang)

            if clear_clicked:
                st.session_state.uploaded_image = None
                st.experimental_rerun()

            if result:
                nomi, kasallik, instruktsiya, alternativalar, narx = result

                # Dori nomi va narxini ko‘rsatish
                components.html(f"""
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        background-color: #FDE9EA;
                        padding: 20px 24px;
                        border-radius: 12px;
                        font-family: 'Segoe UI', sans-serif;
                        font-weight: 400;
                        margin-top: 20px;
                        margin-bottom: 4px;
                        color: black;
                        
                    ">
                        <div style="font-size: 30px;">{translations['drug_name'][lang]}: {nomi}</div>
                        <div style="font-size: 30px; text-align: right;">{translations['price_label'][lang]}: {narx}</div>
                    </div>
                """, height=130)
                if is_mobile:
    # Telefon ko‘rinishi uchun ustma-ust
                   st.markdown(f"""
        <div style="
            background-color: #FDE9EA;
            padding: 20px;
            border-radius: 12px;
            font-family: 'Segoe UI', sans-serif;
            margin-top: 20px;
            margin-bottom: 4px;
            color: black;
        ">
            <div style="font-size: 24px; margin-bottom: 10px;">
                {translations['drug_name'][lang]}: {nomi}
            </div>
            <div style="font-size: 22px;">
                {translations['price_label'][lang]}: {narx if pd.notna(narx) else '-'}
            </div>
        </div>
               """, unsafe_allow_html=True)
                else:
    # Katta ekranlar uchun yonma-yon
                 st.markdown(f"""
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: #FDE9EA;
            padding: 20px 24px;
            border-radius: 12px;
            font-family: 'Segoe UI', sans-serif;
            font-weight: 400;
            margin-top: 20px;
            margin-bottom: 4px;
            color: black;
        ">
            <div style="font-size: 30px;">{translations['drug_name'][lang]}: {nomi}</div>
            <div style="font-size: 24px;">{translations['price_label'][lang]}: {narx if pd.notna(narx) else '-'}</div>
        </div>
    """, unsafe_allow_html=True)
                # OCR aniqlik foizini ko‘rsatish
                st.markdown(f"<div style='color:#999;font-size:13px;padding-top:5px;'>{translations['detecting'][lang].split('...')[0]}: {confidence}%</div>", unsafe_allow_html=True)

                # Expander funksiyasi
                def styled_expander(title, content_func, expanded=False):
                    st.markdown(f"""
                        <div style="
                            background-color: #FDE9EA;
                            color: black;
                            font-size: 30px;
                            font-weight: 400;
                            padding: 10px 15px;
                            border-radius: 8px;
                            margin-bottom: 10px;
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        ">{title}</div>
                    """, unsafe_allow_html=True)
                    with st.expander("", expanded=expanded):
                        content_func()

                # Alternativ dorilar
                styled_expander(
    translations["alt_drugs"][lang],
    lambda: st.dataframe(alternativalar, use_container_width=True),
    expanded=False
)
                
                # Kasalliklar
                styled_expander(translations["illness"][lang],lambda: st.markdown(f"<div style='font-size:25px; line-height:1.5;'>{kasallik}</div>", unsafe_allow_html=True), expanded=False)
                
                # Instruksiya
                formatted_instruksiya = "<br>".join(
                    [re.sub(r"^(➤|\d+[\.\)]|\-|\•)?\s*", "", line).rstrip('.') + "." for line in str(instruktsiya).split("\n") if line.strip()]
                )
                #styled_expander(translations["usage"][lang], lambda: st.markdown(formatted_instruksiya, unsafe_allow_html=True), expanded=False)
                styled_expander(
                    translations["usage"][lang],
                    lambda: st.markdown(
                      f"<div style='font-size:25px; line-height:1.5;'>{formatted_instruksiya}</div>", unsafe_allow_html=True
                    ),
                    expanded=False
                    )
                # Diskleymer
                st.markdown(f"""
                    <div style='
                        width: 100%;
                        margin: 40px auto 20px auto;
                        padding: 18px 24px;
                        background-color: #FDE9EA;
                        color: #ffffff;
                        font-size: 17px;
                        font-weight: 600;
                        border-radius: 12px;
                        font-family: "Segoe UI", Tahoma, sans-serif;
                        text-align: center;
                        box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.1);
                    '>{translations['disclaimer'][lang]}</div>
                """, unsafe_allow_html=True)

            else:
                st.markdown(f"""
                    <div style='
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        text-align: center;
                        padding: 30px;
                        background-color: #FDE9EA;
                        border: 1px solid #ffeeba;
                        border-radius: 10px;
                        color: white;
                        font-size: 17px;
                        font-weight: 500;
                        font-family: "Segoe UI", sans-serif;
                        margin-top: 40px;
                    '>{translations["not_found"][lang]}</div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Xatolik: {e}")
        st.text(traceback.format_exc())
