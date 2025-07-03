import streamlit as st
from PIL import Image
import pandas as pd
import re
import traceback
import base64
from voiceapp import AudioProcessor
from imageapp import (
    resize_image, fix_orientation, image_to_base64, clean_drug_name,
    transliterate_ru_to_lat, is_cyrillic, get_drug_info_from_csv
)
from oracle import extract_drug_info_by_cropping

st.set_page_config(page_title="Tablet AI", layout="wide")

languages = {"Uzbek": "uz", "Русский": "ru", "English": "en", "Кирил": "kiril"}

translations = {
    "title": {
        "uz": "🧪 TabletAI",
        "ru": "🧪 ТаблетAI",
        "en": "🧪 TabletAI",
        "kiril": "🧪 ТаблетAI"
    },
    "upload_label": {
        "uz": "Rasm yuklang",
        "ru": "Загрузите изображение",
        "en": "Upload an image",
        "kiril": "Расм юкланг"
    },
    "detecting": {
        "uz": "🔍 Dori nomi aniqlanmoqda...",
        "ru": "🔍 Название лекарства определяется...",
        "en": "🔍 Detecting drug name...",
        "kiril": "🔍 Дори номи аниқланмоқда..."
    },
    "not_found": {
        "uz": "💬 Dori topilmadi.",
        "ru": "💬 Лекарство не найдено.",
        "en": "💬 Drug not found.",
        "kiril": "💬 Дори топилмади."
    },
    "alt_drugs": {
        "uz": "Alternativ dorilar",
        "ru": "Альтернативные лекарства",
        "en": "Alternative Drugs",
        "kiril": "Альтернатив дорилар"
    },
    "illness": {
        "uz": "Kasalliklar",
        "ru": "Заболевания",
        "en": "Illnesses",
        "kiril": "Касалликлар"
    },
    "usage": {
        "uz": "Instruksiya",
        "ru": "Инструкция",
        "en": "Instruction",
        "kiril": "Инструкция"
    },
    "disclaimer": {
        "uz": " Diqqat: bu dastur tibbiy maslahat emas.",
        "ru": " Внимание: это не медицинская консультация.",
        "en": " Note: This is not medical advice.",
        "kiril": " Диққат: бу дастур тиббий маслаҳат емас."
    },
    "price_label": {
        "uz": "Narxi",
        "ru": "Цена",
        "en": "Price",
        "kiril": "Нархи"
    },
    "drug_name": {
        "uz": "Dori nomi",
        "ru": "Название",
        "en": "Drug name",
        "kiril": "Дори номи"
    },
    "history_title": {
        "uz": "Tekshiruv tarixi",
        "ru": "История проверок",
        "en": "Search History",
        "kiril": "Текширув тарихи"
    },
    "image_upload_title": {
        "uz": "Rasm yuklang",
        "ru": "Загрузите изображение",
        "en": "Upload Image",
        "kiril": "Расм юкланг"
    },
    "voice_recording_title": {
        "uz": "Ovoz yozilmoqda...",
        "ru": "Голос записывается...",
        "en": "Recording voice...",
        "kiril": "Овоз ёзилмоқда..."
    }
}


lang_choice = st.sidebar.radio("Til / Language / Язык", list(languages.keys()))
lang = languages[lang_choice]

def transliterate_to_cyrillic(text):
    mapping = {
        'a': 'а', 'b': 'б', 'd': 'д', 'e': 'е', 'f': 'ф', 'g': 'г', 'h': 'ҳ',
        'i': 'и', 'j': 'ж', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о',
        'p': 'п', 'q': 'қ', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у', 'v': 'в',
        'x': 'х', 'y': 'й', 'z': 'з', 'ʼ': 'ъ', "'": 'ъ', 'sh': 'ш', 'ch': 'ч',
        'ng': 'нг', 'ya': 'я', 'yo': 'ё', 'yu': 'ю', 'ts': 'ц', 'é': 'э'
    }

    for latin, cyrillic in sorted(mapping.items(), key=lambda x: -len(x[0])):
        text = re.sub(rf'\b{latin}\b', cyrillic, text, flags=re.IGNORECASE)
        text = re.sub(latin, cyrillic, text, flags=re.IGNORECASE)
    return text

# 🔹 ALT DRUG ICON + Sarlavha
def get_base64_image(image_path):
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    
# ✅ SHU YERGA QO‘YING!
def clear_image():
    st.session_state.uploaded_image = None
    st.session_state.voice_mode = False
    st.session_state.current_expanded = None

# Light mode styling
st.markdown("""
    <style>
    html, body, [class*="css"]  {
        background-color: #ffffff;
        color: #111111;
    }
    .stButton>button {
        background-color: #f0f0f0;
        color: #333;
        border: 1px solid #ccc;
        padding: 0.5em 1em;
        border-radius: 6px;
    }
    .stMarkdown h3 {
        color: #004d40;
    }
    </style>
""", unsafe_allow_html=True)

st.title(translations["title"][lang])


df = pd.read_csv("alternativa1.csv")

for key, default in {
    "uploaded_image": None,
    "voice_mode": False,
    "history": [],
    "current_expanded": None,
    "history_expanded": set(),
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

def add_to_history(item_type, data, result):
    if result:
        if len(st.session_state.history) >= 10:
            st.session_state.history.pop(0)
        st.session_state.history.append({
            "type": item_type,
            "data": data,
            "result": result
        })

def render_drug_info(result, expanded=True):
    

    nomi, kasallik, instruktsiya, alternativalar, narx = result

    if lang == "ru":
        nomi = transliterate_to_cyrillic(nomi).capitalize()

    if lang == "kiril":
        nomi = transliterate_to_cyrillic(nomi).capitalize()
        kasallik = transliterate_to_cyrillic(kasallik)
        instruktsiya = transliterate_to_cyrillic(instruktsiya)
        alternativalar.columns = [transliterate_to_cyrillic(col) for col in alternativalar.columns]
        alternativalar = alternativalar.applymap(lambda x: transliterate_to_cyrillic(str(x)))
 
    # 🔹 ALT DRUG ICON + Sarlavha
    def get_base64_image(image_path):
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()


    drug_icon = get_base64_image("images/drug_icon.png")
    

# Dori nomi va narxi bir qatorda
    st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 1px solid #ccc; padding-bottom: 10px;'>
    <!-- Dori nomi chapda -->
    <div style='display: flex; align-items: center; gap: 10px;'>
        <img src='data:image/png;base64,{drug_icon}' width='30'>
        <span style='font-size: 30px; font-weight: bold;'>{nomi}</span>
    </div>
    
</div>
""", unsafe_allow_html=True)
    
    price_icon = get_base64_image("images/price_icon.png")
    if not price_icon:
       st.warning("Price icon yuklanmadi!")
    else:
       st.markdown(f"""
    <div style='display: flex; align-items: center; gap: 12px; font-size: 30px; font-weight: bold; color: white;'>
        <img src='data:image/png;base64,{price_icon}' width='26'>
        <span>{narx}</span>
    </div>
    <hr style="margin-top: 0; margin-bottom: 10px; border: 1px #ddd;">
    """, unsafe_allow_html=True)
    


    alt_icon = get_base64_image("images/alt_drugs_icon.png")

    st.markdown(f"""
<div style='display:flex; align-items:center; gap:10px; margin-bottom:10px;'>
    <img src='data:image/png;base64,{alt_icon}' width='30'>
    <span style='font-size:30px; font-weight:bold;'>{translations['alt_drugs'][lang]}</span>
</div>
""", unsafe_allow_html=True)
    with st.expander("", expanded=True):
        st.dataframe(alternativalar, use_container_width=True)


    illness_icon = get_base64_image("images/illness_icon.png")

    st.markdown(f"""
<div style='display:flex; align-items:center; gap:10px; margin-bottom:10px;'>
    <img src='data:image/png;base64,{illness_icon}' width='30'>
    <span style='font-size:30px; font-weight:bold;'>{translations['illness'][lang]}</span>
</div>
""", unsafe_allow_html=True)   

    with st.expander("", expanded=False):
        st.markdown(f"<div style='font-size:20px'>{kasallik}</div>", unsafe_allow_html=True)
   
   
     # 🧾 Instruksiya
    instruction_icon = get_base64_image("images/instruction_icon.png")

    st.markdown(f"""
<div style='display:flex; align-items:center; gap:10px; margin-bottom:10px;'>
    <img src='data:image/png;base64,{instruction_icon}' width='30'>
    <span style='font-size:30px; font-weight:bold;'>{translations['usage'][lang]}</span>
</div>
""", unsafe_allow_html=True)
    with st.expander("", expanded=False):
        formatted_instruksiya = "<br>".join([
            re.sub(r"^(\u2022|\d+[\.\)]|\-|\u2022)?\s*", "", line).rstrip('.') + "."
            for line in str(instruktsiya).split("\n") if line.strip()
        ])
        st.markdown(f"<div style='font-size:20px'>{formatted_instruksiya}</div>", unsafe_allow_html=True)
 
 
 #  Disclaimer
    disclaimer_icon = get_base64_image("images/disclaimer_icon.png")
    st.markdown(f"""
<div style='display: flex; align-items: center; background-color:#194522;
            padding: 15px; border-radius: 10px; border: 1px solid #ccc;
            font-size: 20px; color: white; gap: 12px;'>
    <img src='data:image/png;base64,{disclaimer_icon}' width='40'>
    <div>
        <span style='font-weight: bold;'> {translations['disclaimer'][lang]}</span>
    </div>
</div>
""", unsafe_allow_html=True)

       
    

def render_history():
    global history_icon
    st.markdown("---")
    history_icon = get_base64_image("images/history_icon.png") 
    st.markdown(f"""
<div style='display: flex; align-items: center; gap: 10px; margin-top: 20px; margin-bottom: 10px;'>
    <img src='data:image/png;base64,{history_icon}' width='28'>
    <span style='font-size: 26px; font-weight: bold;'>{translations['history_title'][lang]}</span>
</div>
""", unsafe_allow_html=True)
    max_visible = 3
    full_history = st.session_state.history[-10:][::-1]  # So‘nggi 10 ta, teskari tartibda
    short_history = full_history[:max_visible]
    hidden_history = full_history[max_visible:]

    def render_entry(item, idx):
        try:
            result = item["result"]
            nomi = result[0]
            narx = result[4]
            item_type = item["type"]
        except KeyError:
            return
        
        drug_icon = get_base64_image("images/drug_icon.png")
        price_icon = get_base64_image("images/price_icon.png")

        col1, col2 = st.columns([1, 9])
        with col1:
            if item_type == "image":
                try:
                    img = Image.open(item["data"])
                    img = resize_image(img, max_size=(60, 60))
                    img = fix_orientation(img)
                    st.image(img, width=50)
                except:
                    st.markdown("🖼️")
            else:
                st.markdown("🎤", unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
        <div style='display:flex; align-items:center; gap:10px; font-size:18px; font-weight:bold; margin-bottom:5px;'>
            <img src='data:image/png;base64,{drug_icon}' width='22'>
            <span>{nomi}</span>
            <img src='data:image/png;base64,{price_icon}' width='20'>
            <span>{narx}</span>
        </div>
        """, unsafe_allow_html=True)
            toggle_key = f"history_expand_{idx}"
            is_expanded = st.toggle("Ko‘proq ma’lumot", key=toggle_key)
            if is_expanded:
                with st.container():
                    render_drug_info(result, expanded=False)

    for idx, item in enumerate(short_history):
        render_entry(item, idx)

    if hidden_history:
        if st.toggle("🕽️ Davomini ko‘rish", key="show_more_history"):
            for idx, item in enumerate(hidden_history, start=max_visible):
                render_entry(item, idx)


if st.session_state.uploaded_image is None and not st.session_state.voice_mode:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### {translations['image_upload_title'][lang]}")
        uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"], key="upload")
        if uploaded_file:
            st.session_state.uploaded_image = uploaded_file
            st.rerun()
    with col2:
        st.markdown(f"### {translations['voice_recording_title'][lang]}")
        if st.button("🎤 Voice boshlash"):
            st.session_state.voice_mode = True
            st.rerun()


elif st.session_state.voice_mode:
    import streamlit_webrtc

    ctx = streamlit_webrtc.webrtc_streamer(
        key="speech",
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"video": False, "audio": True},
        async_processing=True
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### {translations['voice_recording_title'][lang]}")
    with col2:
        if st.button("🔍 Izlash"):
            if ctx.audio_processor:
                transcript = ctx.audio_processor.get_transcript()
                if transcript:
                    if lang == "kiril":
                        transcript = transliterate_to_cyrillic(transcript)
                    st.success(f"🎧 {translations['drug_name'][lang]}: {transcript}")
                    result = get_drug_info_from_csv(transcript, df, lang)
                    if result:
                        add_to_history("voice", transcript, result)
                        render_drug_info(result)
                    else:
                        st.warning(translations["not_found"][lang])
                else:
                    st.warning("❗ Ovoz aniqlanmadi")
        if st.button("❌ Voice rejimini to‘xtatish"):
            st.session_state.voice_mode = False
            st.rerun()

            st.markdown("""
<style>
    div.stButton > button#clear_image_button {
        background-color: #e74c3c;  /* Qizil fon */
        color: white;               /* Oq shrift */
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 20px;
        border: none;
        transition: background-color 0.3s ease;
        cursor: pointer;
    }
    div.stButton > button#clear_image_button:hover {
        background-color: #c0392b;  /* Hover paytida qorong‘i qizil */
    }
                        
</style>
""", unsafe_allow_html=True)
            
    st.markdown("""
<style>
.glass-box {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 15px;
    padding: 20px;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}
</style>
""", unsafe_allow_html=True)

elif st.session_state.uploaded_image is not None:
    col1, col2 = st.columns([0.4, 0.6])
    with col1:
        st.markdown("<div class='glass-box'>", unsafe_allow_html=True)

        image = Image.open(st.session_state.uploaded_image)
        image = fix_orientation(resize_image(image, max_size=(300, 300)))
        image = image.convert("RGB") 

        def image_to_base64(image):
            from io import BytesIO
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()

        img_base64 = image_to_base64(image)

        st.markdown(""" 
            <style>
        .image-border-wrapper {
            display: flex;
            justify-content: center;
            margin-top: 10px;
            margin-bottom: 10px;
        }
        .image-border {
            border: 3px solid #B0C4DE;
            border-radius: 15px;
            padding: 4px;
            display: inline-block;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }
        </style> 
         """, unsafe_allow_html=True)

        st.markdown(f"""
            <div class="image-border-wrapper">
                <div class="image-border">
                     <img src="data:image/png;base64,{img_base64}" width="250">
                </div>
            </div>
            """, unsafe_allow_html=True)
        

        if st.button("❌ Rasmni o‘chirish", key="clear_image_button"):
            clear_image()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        try:
            image = Image.open(st.session_state.uploaded_image)
            image = resize_image(image)
            image = fix_orientation(image)
            with st.spinner(translations["detecting"][lang]):
                text, confidence = extract_drug_info_by_cropping(image)
                cleaned = clean_drug_name(text)
                drug_name = transliterate_ru_to_lat(cleaned) if is_cyrillic(cleaned) else cleaned
                result = get_drug_info_from_csv(drug_name, df, lang)
            if result:
                add_to_history("image", st.session_state.uploaded_image, result)
                render_drug_info(result)
            else:
                st.warning(translations["not_found"][lang])
        except Exception as e:
            st.error("❌ Xatolik yuz berdi:")
            st.text(traceback.format_exc())

if st.session_state.history:
    render_history()
