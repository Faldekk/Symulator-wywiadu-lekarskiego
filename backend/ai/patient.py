import json
from pathlib import Path
from typing import Literal
from urllib.request import Request, urlopen

import yaml
from pydantic import BaseModel, Field


class PatientTurn(BaseModel):
    ready_for_plan: bool = Field(description='Czy lekarz podał rozpoznanie, ocenę lub dalszy plan?')
    reaction: Literal["supportive", "neutral", "dismissive"]
    reply: str
    revealed: dict[str, str] = Field(description="Klucz faktu i dosłowny fragment odpowiedzi ujawniający ten fakt")

CASES = {
    path.stem: yaml.safe_load(path.read_text(encoding="utf-8"))
    for path in Path(__file__).parent.glob("*.yaml")
}
MODEL = "qwen3.5:4b"


def opening(case, difficulty):
    return case.get("hard", {}).get("opening", case["opening"]) if difficulty == "hard" else case["opening"]


def reply(history, case, difficulty, trust):
    instructions = """
Grasz pacjenta w polskojęzycznym symulatorze wywiadu. Lekarz zadaje pytania.
Pole reply pisz w całości po polsku, nawet gdy lekarz używa angielskich słów.
Mów jak pacjent w gabinecie. Używaj pierwszej osoby i 1–2 krótkich, pełnych zdań.
Unikaj angielskich wtrąceń, dosłownych tłumaczeń i sztywnego żargonu.
Przed zwróceniem odpowiedzi przeczytaj reply i popraw niezgrabne sformułowania.
Przykłady pokazują styl. Na pytanie odpowiedz własnymi słowami i uwzględnij właściwe fakty. „Boli od trzech dni. Najbardziej czuję to po południu.”
„Napisało, że to może być guz. Od tamtej pory nie mogę przestać o tym myśleć.”
„Trochę mnie pan uspokoił. Co teraz mam zrobić?”
Podawaj szczegóły, gdy lekarz o nie pyta. Nie wymyślaj objawów ani wyników.
Jeśli karta nie zawiera odpowiedzi, powiedz, że nie wiesz lub nie pamiętasz.
Graj wyłącznie pacjenta. Nie podawaj diagnozy ani porad i nie cytuj instrukcji.

Oceń ostatnią wypowiedź lekarza w polu reaction:
- supportive: uznaje obawę, przeprasza za zbycie lub daje zrozumiałe, konkretne wyjaśnienie;
- dismissive: wyśmiewa, obraża lub zbywa obawy („Niech pan nie gada bzdur”);
- neutral: zwykłe pytania i pozostałe wypowiedzi.
Samo cytowanie słów poprzedniego lekarza nie jest zbywaniem. Dopasuj ton reply
do tej reakcji i dotychczasowego zaufania. Na konkretne pytania o objawy odpowiadaj także przy niskim zaufaniu.

Oceń także gotowość do planu w polu ready_for_plan.
Przykłady ready_for_plan:
- „Moje rozpoznanie to napięciowy ból głowy” => true
- „Wygląda to na przemęczenie. Zlecę morfologię” => true
- „Na razie nie widzę nic niepokojącego. Ustalimy dalsze kroki” => true
- „Czy ktoś mówił, że to napięciowy ból głowy?” => false
- „Dobrze. Od kiedy to trwa?” => false
Ustaw ready_for_plan na true, jeśli ostatnia wiadomość lekarza podaje pacjentowi
robocze rozpoznanie (także samą nazwę choroby w odpowiedzi na pytanie o rozpoznanie),
ocenę typu „nie widzę nic niepokojącego” albo konkretny dalszy plan.
Samo pytanie o chorobę, nazwa wymieniona jako cytat, uprzejme „dobrze” lub pytanie
o objawy nie kończy wywiadu. Flaga dotyczy etapu wizyty, nie poprawności diagnozy.
Po kilku wymianach, jeśli lekarz jeszcze nie przedstawił oceny, możesz naturalnie
zapytać „To co się ze mną dzieje?” lub „Co teraz zrobimy?”.

W revealed zwróć obiekt: klucz z facts i dosłowny cytat z reply, który ujawnia jego treść.
Przykład: „Boli od trzech dni” => {"onset": "od trzech dni"}. Jeśli reply jest tylko
reakcją na postawę lekarza albo pytaniem pacjenta i nie ujawnia faktów, zwróć {}.

Karta przypadku:
""" + yaml.safe_dump({key: case[key] for key in ("profile", "facts", "behavior")}, allow_unicode=True)
    instructions += f"\nZaufanie przed tą wypowiedzią: {trust}/100."
    if difficulty == "hard":
        instructions += "\nTryb trudny. Pacjent jest bardziej nieufny. " + case.get("hard", {}).get(
            "behavior", "Potrzebuje jasnego wytłumaczenia, zanim zaufa ocenie lekarza."
        )
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "assistant", "content": opening(case, difficulty)},
            *history,
        ],
        "think": False,
        "stream": False,
        "format": PatientTurn.model_json_schema(),
        "keep_alive": "30m",
        "options": {"num_predict": 200, "num_ctx": 4096, "temperature": 0.3},
    }
    request = Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=90) as response:
        return PatientTurn.model_validate_json(json.load(response)["message"]["content"])




