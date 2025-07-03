import pandas as pd
from PIL import Image, ExifTags
from io import BytesIO
import base64
import re
from difflib import get_close_matches


def resize_image(img, max_size=(1024, 1024)):
    img.thumbnail(max_size)
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

def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def clean_drug_name(raw_name):
    cleaned = re.split(r"[\u00AE\u00A9\u2122]", raw_name)[0].strip()
    cleaned = re.sub(r"[^a-zA-Zа-яА-ЯёЁ0-9\- ]", "", cleaned)
    return cleaned

def is_cyrillic(text):
    return any('а' <= c <= 'я' or 'А' <= c <= 'Я' for c in text)

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

    #kirillcha_nomi = row.get("Asl dorining nomi (kiril)", "")
    lotincha_nomi = row.get("Asl dorining nomi", "")

    # if not kirillcha_nomi:
    #     kirillcha_nomi = transliterate_lat_to_cyr(lotincha_nomi)

    nomi = f"{lotincha_nomi} "
    narx = row.get("Narxi (taxminiy)", "")
    tasir_modda = row.get("Tasir etuvchi modda", "").strip().lower()

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

    alternativalar["Asl dorining nomi"] = alternativalar["Asl dorining nomi"].apply(
        lambda x: transliterate_ru_to_lat(str(x)) if is_cyrillic(str(x)) else x
    )

    return nomi, kasallik, instruktsiya, alternativalar, narx
