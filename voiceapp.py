import numpy as np
import tempfile
import os
import soundfile as sf
import pandas as pd
from difflib import get_close_matches
from streamlit_webrtc import AudioProcessorBase
import whisper

# -------------------------
# 1. Whisper modelni kesh bilan yuklash
# -------------------------
_model = None

def load_model():
    """Whisper modelni faqat bir marta yuklaydi."""
    global _model
    if _model is None:
        try:
            _model = whisper.load_model("base")
        except Exception as e:
            print(f"❌ Whisper model yuklashda xatolik: {e}")
            raise e
    return _model


# -------------------------
# 2. Ovozdan matnga konvertatsiya
# -------------------------
def recognize_audio(audio_data: np.ndarray, lang: str = None) -> str:
    """
    Ovoz signalini Whisper modeli yordamida matnga aylantiradi.
    :param audio_data: NumPy array (streamlit_webrtc dan olingan)
    :param lang: optional – "uz", "ru", "en" kabi til kodi
    :return: transkrib qilingan matn
    """
    try:
        model = load_model()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            sf.write(tmpfile.name, audio_data, samplerate=16000)
            audio_path = tmpfile.name

        result = model.transcribe(audio_path, language=lang) if lang else model.transcribe(audio_path)
        os.remove(audio_path)

        text = result.get("text", "")
        return text.strip()

    except Exception as e:
        print(f"❌ Matn tanib olishda xatolik: {e}")
        return ""


# -------------------------
# 3. Streamlit WebRTC audio processori
# -------------------------
class AudioProcessor(AudioProcessorBase):
    """
    Streamlit WebRTC yordamida mikrofondan ovoz yozadi.
    """
    def __init__(self):
        self.frames = []

    def recv(self, frame):
        self.frames.append(frame.to_ndarray())
        return frame

    def get_audio_data(self):
        """
        Barcha yozilgan fragmentlarni birlashtiradi va qaytaradi.
        """
        if self.frames:
            audio = np.concatenate(self.frames, axis=0)
            self.frames = []
            return audio
        return None


# -------------------------
# 4. CSV ma'lumotlar bilan ishlash
# -------------------------
def load_data(csv_path: str = "alternativa1.csv") -> pd.DataFrame:
    """
    CSV fayldan dori ma'lumotlarini yuklaydi.
    :param csv_path: fayl yo‘li
    :return: pandas DataFrame
    """
    try:
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        return df
    except FileNotFoundError:
        print(f"❌ Fayl topilmadi: {csv_path}")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ CSVni o‘qishda xatolik: {e}")
        return pd.DataFrame()


# -------------------------
# 5. Dori nomi va alternativalarini topish
# -------------------------
def find_alternatives(drug_name: str, df: pd.DataFrame):
    """
    Berilgan dori nomiga mos keladigan dori va uning alternativalarini topadi.
    :param drug_name: aytilgan yoki yozilgan nom
    :param df: CSV ma’lumotlar
    :return: (asosiy nom, faol modda, alternativalar ro‘yxati)
    """
    if df.empty:
        return None, None, []

    try:
        match = get_close_matches(drug_name.lower(), df["Dori nomi yoki alternativ"].str.lower(), n=1, cutoff=0.6)
        if not match:
            return None, None, []

        matched_name = match[0]
        original_row = df[df["Dori nomi yoki alternativ"].str.lower() == matched_name]

        if original_row.empty:
            return None, None, []

        active_substance = original_row.iloc[0]["Faol modda"]
        alternatives = df[df["Faol modda"] == active_substance]["Dori nomi yoki alternativ"].tolist()

        return matched_name, active_substance, alternatives
    except Exception as e:
        print(f"❌ Dori topishda xatolik: {e}")
        return None, None, []
