import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.ai import patient
from backend.conversation.exams import Exam, TEST_NAMES, normalize_test_name
from backend.main.voice import router as voice_router

app = FastAPI()
app.include_router(voice_router)
Difficulty = Literal["normal", "hard"]
LEGACY_CASES = ("headache", "thirst", "checkup", "home-reading")


@app.get("/api/cases")
def case_catalog():
    return {"cases": list(range(1, 5)) + sorted(int(key) for key in patient.CASES if key.isdigit())}


def get_case(case_id: str):
    if case_id in ("1", "2", "3", "4"):
        case_id = LEGACY_CASES[int(case_id) - 1]
    case = patient.CASES.get(case_id)
    if case is None:
        raise HTTPException(404, "Nieznany przypadek.")
    return case


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=1500)


class ChatMessage(BaseModel):
    text: str = Field(max_length=1500)
    trust: int | None = Field(default=None, ge=0, le=100)
    history: list[Turn] = Field(default_factory=list, max_length=8)


class TestOrder(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    observed: list[str] = Field(default_factory=list, max_length=32)


@app.get("/api/case")
def case_opening(case_id: str = "headache", difficulty: Difficulty = "normal"):
    case = get_case(case_id)
    return {
        "opening": patient.opening(case, difficulty),
        "profile": case["profile"],
        "trust": 25 if difficulty == "hard" else 55,
        "fact_count": len(case["facts"]),
    }


@app.post("/api/chat")
def chat(message: ChatMessage, case_id: str = "headache", difficulty: Difficulty = "normal"):
    case = get_case(case_id)
    text = message.text.strip()
    if not text:
        raise HTTPException(422, "Wpisz wiadomość.")

    history = [turn.model_dump() for turn in message.history]
    history.append({"role": "user", "content": text})
    trust = message.trust if message.trust is not None else (25 if difficulty == "hard" else 55)
    try:
        turn = patient.reply(history, case, difficulty, trust)
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(503, "Brak odpowiedzi z Ollamy. Sprawdź, czy działa i ma model qwen3.5:4b.") from error
    explicit_plan = re.match(
        r"(?i)^(?:(?:moje )?(?:robocze )?rozpoznanie\s*(?:to\s+|:\s*)|plan\s*:\s*)[^?]+(?:[.!]|$)",
        text,
    )
    if not turn.reply.strip():
        raise HTTPException(502, "Model zwrócił pustą odpowiedź. Spróbuj ponownie.")
    return {
        "reply": turn.reply.strip(),
        "trust": max(0, min(100, trust + {"supportive": 12, "neutral": 0, "dismissive": -18}[turn.reaction])),
        "plan_ready": bool(turn.ready_for_plan or explicit_plan),
        "facts": {
            key: {
                "label": case["fact_labels"][key],
                "value": case["facts"][key],
            }
            for key, quote in turn.revealed.items()
            if key in case["fact_labels"] and key in case["facts"]
            and len(quote.strip()) >= 5 and quote.strip().casefold() in turn.reply.casefold()
        },
        "actions": [
            {"id": key, "label": value["label"]}
            for key, value in case_actions(case).items()
            if key != "morphology" and "labs" not in value and "finding" not in value
        ] if turn.ready_for_plan or explicit_plan else [],
    }


def case_actions(case):
    return {**patient.CASES["headache"]["actions"], **case["actions"]}


def abnormal_labs(rows):
    results = []
    for row in rows:
        value = row["value"]
        low, high = row.get("lower"), row.get("upper")
        if low is not None and value < low:
            status = "Poniżej normy"
        elif high is not None and (value > high or value == high and row.get("upper_exclusive")):
            status = "Powyżej normy"
        else:
            continue
        operator = "<" if row.get("upper_exclusive") else "≤"
        limits = " / ".join(
            f"{sign} {bound:g} {row['unit']}"
            for sign, bound in (("≥", low), (operator, high))
            if bound is not None
        )
        results.append({
            "name": row["name"],
            "value": f"{value:g}".replace(".", ",") + " " + row["unit"],
            "range": limits.replace(".", ","),
            "status": status,
        })
    return results


@app.post("/api/actions/{action_id}")
def visit_action(action_id: str, case_id: str = "headache"):
    case = get_case(case_id)
    action = case_actions(case).get(action_id)
    if action is None:
        raise HTTPException(404, "Nieznana czynność.")

    rows = action.get("labs", [])
    if action_id == "morphology" and "finding" not in action and "labs" not in action:
        rows = patient.CASES["headache"]["labs"]
    labs = abnormal_labs(rows)
    note = action.get("note", "")
    normal_count = len(rows) - len(labs)

    result = action["result"]
    if action_id == "finish" and "diagnosis" in case:
        diagnosis = case["diagnosis"]
        result += " Rozpoznanie w karcie przypadku: " + diagnosis["label"] + "."
        if diagnosis.get("note"):
            result += " " + diagnosis["note"]
        if diagnosis.get("differentiation"):
            result += " " + diagnosis["differentiation"]
    return {
        "result": result,
        "finished": action_id == "finish",
        "labs": labs,
        "lab_note": note,
        "finding": action.get("finding", ""),
        "normal_count": normal_count,
        "source": action.get("source", "Scenariusz"),
        "test": "Morfologia" if action_id == "morphology" else action.get(
            "title", action["label"].removeprefix("Zleć ")
        ),
    }


@app.post("/api/tests")
def order_test(order: TestOrder, case_id: str = "headache"):
    case = get_case(case_id)
    name = normalize_test_name(order.name)
    if name in {"rtg", "usg", "tk", "tomografia", "mr", "mri", "rezonans"}:
        raise HTTPException(422, "Podaj okolicę ciała, której ma dotyczyć badanie.")
    for key, action in case_actions(case).items():
        if key != "morphology" and "labs" not in action and "finding" not in action:
            continue
        exam = Exam(key)
        names = TEST_NAMES[exam]
        if name == normalize_test_name(action["label"]) or name in names:
            result = visit_action(exam.value, case_id)
            expected = case.get("indications", {}).get(exam.value, [])
            matched = [key for key in expected if key in order.observed and key in case["facts"]]
            result["indication"] = (
                "W zebranym wywiadzie jest przesłanka do tego badania." if matched
                else "Wywiad nie wykazał jeszcze przesłanki zapisanej dla tego badania."
                if expected else "Karta nie przypisuje temu badaniu wskazania."
            )
            result["matched_facts"] = [case["fact_labels"][key] for key in matched]
            return result
    if any(name in aliases for aliases in TEST_NAMES.values()):
        raise HTTPException(404, "Zlecenie rozpoznane. W tym scenariuszu nie ma przygotowanego wyniku tego badania.")
    raise HTTPException(404, "Nie udało się rozpoznać nazwy badania. Wpisz pełną nazwę lub inny skrót.")



frontend = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")











