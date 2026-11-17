import re
import unicodedata
from enum import StrEnum


class Exam(StrEnum):
    MORPHOLOGY = "morphology"
    HBA1C = "hba1c"
    LIPIDS = "lipids"
    UACR = "uacr"
    PRESSURE = "pressure"
    FERRITIN = "ferritin"
    B12 = "b12"
    ECG = "ecg"
    SPIROMETRY = "spirometry"
    SLEEP = "sleep"
    ULTRASOUND = "ultrasound"
    DIX = "dix"
    ORTHOSTATIC = "orthostatic"
    TSH = "tsh"
    FT4 = "ft4"
    URINE = "urine"
    DOPPLER = "doppler"
    CT = "ct"
    CHEST_XRAY = "chest-xray"
    SINUS_XRAY = "sinus-xray"
    SINUS_CT = "sinus-ct"
    HEAD_CT = "head-ct"
    HEAD_MRI = "head-mri"
    CELIAC = "celiac"


TEST_NAMES = {
    Exam.MORPHOLOGY: ("morfologia", "morfologie", "morfologia krwi", "cbc", "pelna morfologia", "obwodowa morfologia krwi"),
    Exam.HBA1C: ("hba1c", "hemoglobina glikowana", "hemoglobine glikowana", "hemoglobina glikozylowana", "a1c"),
    Exam.LIPIDS: ("lipidogram", "profil lipidowy", "panel lipidowy", "profil lipidow"),
    Exam.UACR: ("uacr", "acr", "albumina kreatynina w moczu", "wskaznik albumina kreatynina", "stosunek albuminy do kreatyniny w moczu"),
    Exam.PRESSURE: ("cisnienie", "cisnienie tetnicze", "pomiar cisnienia"),
    Exam.FERRITIN: ("ferrytyna", "ferrytyne"),
    Exam.B12: ("witamina b12", "witamine b12", "b12"),
    Exam.ECG: ("ekg", "ecg", "elektrokardiogram", "ekg spoczynkowe", "12 odprowadzeniowe ekg"),
    Exam.SPIROMETRY: ("spirometria", "spirometrie"),
    Exam.SLEEP: ("poligrafia", "poligrafia snu", "badanie snu"),
    Exam.ULTRASOUND: ("usg brzucha", "usg jamy brzusznej", "usg jamy brzusznej i miednicy"),
    Exam.DIX: ("dix hallpike", "dix hallpike a", "proba dix hallpike", "proba hallpike a"),
    Exam.ORTHOSTATIC: ("proba ortostatyczna", "test ortostatyczny", "pomiar cisnienia na lezaco i stojaco"),
    Exam.TSH: ("tsh", "tyreotropina"),
    Exam.FT4: ("ft4", "f t 4", "wolna tyroksyna", "wolne t4", "t4 wolne"),
    Exam.URINE: ("badanie moczu", "mocz", "badanie ogolne moczu", "ogolne badanie moczu", "analiza moczu", "bom"),
    Exam.DOPPLER: ("doppler", "usg doppler", "usg doppler zyl", "usg doppler zyl konczyn dolnych", "usg zyl konczyn dolnych", "doppler zyl nogi"),
    Exam.CT: ("tk", "tk bez kontrastu", "tomografia bez kontrastu", "tk drog moczowych bez kontrastu"),
    Exam.CHEST_XRAY: ("rtg pluc", "rtg klatki", "rtg klatki piersiowej", "rtg kp", "zdjecie klatki piersiowej"),
    Exam.SINUS_XRAY: ("rtg zatok", "rtg zatok przynosowych", "zdjecie zatok"),
    Exam.SINUS_CT: ("tk zatok", "tk zatok przynosowych", "tomografia zatok"),
    Exam.HEAD_CT: ("tk glowy", "tomografia glowy"),
    Exam.HEAD_MRI: ("mr glowy", "mri glowy", "rezonans glowy", "rezonans magnetyczny glowy"),
    Exam.CELIAC: ("ttg", "ttg iga", "anty ttg iga", "przeciwciala przeciw transglutaminazie tkankowej iga", "serologia celiakii"),
}


def normalize_test_name(text):
    text = unicodedata.normalize("NFKD", text.casefold().replace("ł", "l"))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = " ".join(re.findall(r"[a-z0-9]+", text))
    text = re.sub(r"^(?:(?:prosze o|prosze wykonac|zlec|zlecam|zmierz|wykonaj) )+", "", text)
    text = re.sub(r"\br t g\b|\brentgen\b", "rtg", text)
    return re.sub(r"\be k g\b", "ekg", text)

