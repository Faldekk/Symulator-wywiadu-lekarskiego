const form = document.querySelector("form");
const input = document.querySelector("#message");
const button = form.querySelector("button");
const messages = document.querySelector("#messages");
const status = document.querySelector('#status');
const history = [];
const testOrder = document.querySelector("#test-order");
const testForm = document.querySelector("#test-form");
const testName = document.querySelector("#test-name");
const orderedTests = new Set();

testForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = testName.value.trim();
  if (!name || testName.readOnly) return;
  const submit = testForm.querySelector("button");
  submit.disabled = true;
  testName.readOnly = true;
  try {
    const response = await fetch("/api/tests" + caseQuery, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, observed: [...facts.keys()] }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Nie udało się zlecić badania.");
    if (testOrder.hidden) return;
    if (orderedTests.has(data.test)) {
      status.textContent = "Wynik tego badania jest już w panelu pacjenta.";
      return;
    }
    orderedTests.add(data.test);
    showLabs(data);
    addMessage("Symulacja", data.result);
    status.textContent = "";
    testForm.reset();
    testOrder.open = false;
  } catch (error) {
    status.textContent = error.message;
  } finally {
    submit.disabled = false;
    testName.readOnly = false;
  }
});
const facts = new Map();
const legacyCaseIds = ["headache", "thirst", "checkup", "home-reading"];
const currentUrl = new URL(location.href);
const selectedCase = currentUrl.searchParams.get("case_id");
const caseNumber = Number(selectedCase) || legacyCaseIds.indexOf(selectedCase) + 1 || 1;
const difficulty = document.querySelector("#difficulty");
difficulty.value = currentUrl.searchParams.get("difficulty") === "hard" ? "hard" : "normal";
const caseQuery = "?case_id=" + caseNumber + "&difficulty=" + difficulty.value;
let trust = 55;
let factCount = 0;
let visitStage = "Wywiad w toku";

difficulty.addEventListener("change", () => {
  currentUrl.searchParams.set("case_id", caseNumber);
  currentUrl.searchParams.set("difficulty", difficulty.value);
  location.href = currentUrl.href;
});

function showStats() {
  document.querySelector("#visit-stats").hidden = false;
  document.querySelector("#trust-meter").value = trust;
  document.querySelector("#trust-value").textContent = trust + "/100";
  document.querySelector("#interview-progress").textContent = "Zebrane informacje: " + facts.size + "/" + factCount;
  document.querySelector("#visit-stage").textContent = visitStage;
}

function showCaseLinks(cases) {
  const list = document.querySelector(".case-list");
  for (const number of cases) {
    const link = document.createElement("a");
    link.href = "?case_id=" + number + "&difficulty=" + difficulty.value;
    link.textContent = "Przypadek " + number;
    if (number === caseNumber) link.setAttribute("aria-current", "page");
    list.append(link);
  }
  document.querySelector("#current-case").textContent = "Przypadek " + caseNumber;
  const randomButton = document.querySelector("#random-case");
  const otherCases = cases.filter((number) => number !== caseNumber);
  randomButton.disabled = !otherCases.length;
  randomButton.addEventListener("click", () => {
    const choice = otherCases[Math.floor(Math.random() * otherCases.length)];
    location.href = "?case_id=" + choice + "&difficulty=" + difficulty.value;
  });
}

function showFacts(details) {
  for (const [key, fact] of Object.entries(details)) facts.set(key, fact);
  document.querySelector("#empty-facts").hidden = facts.size > 0;
  const list = document.querySelector("#facts");
  list.replaceChildren();
  for (const { label, value } of facts.values()) {
    const title = document.createElement("dt");
    const detail = document.createElement("dd");
    title.textContent = label;
    detail.textContent = value;
    list.append(title, detail);
  }
}

function showLabs({ labs, lab_note, normal_count, source, test, finding, indication, matched_facts }) {
  if (!labs.length && !normal_count && !finding) return;

  document.querySelector("#lab-panel").hidden = false;
  const group = document.createElement("section");
  group.className = "lab-card";
  const title = document.createElement("h4");
  title.textContent = test;
  const summary = document.createElement("p");
  summary.className = "lab-summary";
  summary.textContent = finding ? source : (labs.length ? "Poza zakresem: " + labs.length : "Bez odchyleń")
    + " · W zakresie: " + normal_count + " · " + source;
  group.append(title, summary);
  if (finding) {
    const findingText = document.createElement("p");
    findingText.textContent = finding;
    group.append(findingText);
  }

  for (const lab of labs) {
    const row = document.createElement("p");
    row.className = "lab-row";
    const value = document.createElement("strong");
    value.textContent = lab.name + " · " + lab.value;
    const detail = document.createElement("span");
    detail.textContent = lab.status + " · Punkt odniesienia: " + lab.range;
    row.append(value, detail);
    group.append(row);
  }

  if (indication) {
    const explanation = document.createElement("p");
    explanation.className = "lab-summary";
    explanation.textContent = indication;
    if (matched_facts.length) explanation.textContent += " " + matched_facts.join(", ") + ".";
    group.append(explanation);
  }

  if (lab_note) {
    const note = document.createElement("p");
    note.className = "lab-summary";
    note.textContent = lab_note;
    group.append(note);
  }
  document.querySelector("#labs").append(group);
}

function addMessage(role, text) {
  const message = document.createElement("p");
  message.className = role === "Lekarz" ? "message doctor" : "message";
  message.textContent = role + ": " + text;
  if (role === "Pacjent") {
    const listen = document.createElement("button");
    listen.type = "button";
    listen.className = "listen";
    listen.textContent = "Odsłuchaj";
    listen.addEventListener("click", () => playPatient(text));
    message.append(" ", listen);
  }
  messages.append(message);
  messages.scrollTop = messages.scrollHeight;
}

function showActions(options) {
  if (!options.length) return;
  actions.hidden = false;
  for (const { id, label } of options) {
    if (actions.querySelector('[data-action="' + id + '"]')) continue;
    const choice = document.createElement("button");
    choice.type = "button";
    choice.dataset.action = id;
    choice.textContent = label;
    choice.addEventListener("click", async () => {
      choice.disabled = true;
      try {
        const response = await fetch("/api/actions/" + encodeURIComponent(id) + caseQuery, { method: "POST" });
        if (!response.ok) throw new Error();
        const data = await response.json();
        const { result, finished } = data;
        addMessage("Symulacja", result);
        showLabs(data);
        status.textContent = "";
        if (finished) {
          visitStage = "Wizyta zakończona";
          showStats();
          actions.hidden = true;
          form.hidden = true;
          testOrder.hidden = true;
          finishRecording();
          stopVoice();
        }
      } catch {
        choice.disabled = false;
        status.textContent = "Nie udało się wykonać czynności. Spróbuj ponownie.";
      }
    });
    actions.append(choice);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || button.disabled) return;

  button.disabled = true;
  input.readOnly = true;
  status.textContent = "Wysyłanie…";

  try {
    const response = await fetch("/api/chat" + caseQuery, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, history: history.slice(-8), trust }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Nie udało się wysłać wiadomości.");
    const { reply } = data;
    history.push({ role: "user", content: text }, { role: "assistant", content: reply });
    addMessage("Lekarz", text);
    addMessage("Pacjent", reply);
    showFacts(data.facts);
    if (!form.hidden) {
      trust = data.trust;
      if (data.plan_ready) visitStage = "Lekarz przedstawił ocenę lub plan";
      showStats();
    }
    if (!form.hidden) showActions(data.actions);
    input.value = "";
    status.textContent = "";
    if (autoVoice.checked && !form.hidden) playPatient(reply);
  } catch (error) {
    status.textContent = error instanceof TypeError ? "Brak połączenia z serwerem." : error.message;
  } finally {
    button.disabled = false;
    input.readOnly = false;
    input.focus();
  }
});

if (location.protocol === "file:") {
  form.hidden = true;
  status.textContent = "Uruchom plik „Uruchom czat.cmd” z folderu projektu i otwórz http://127.0.0.1:8000/.";
} else {
  button.disabled = true;
  if (legacyCaseIds.includes(selectedCase)) {
    currentUrl.searchParams.set("case_id", String(caseNumber));
    window.history.replaceState(null, "", currentUrl);
  }
  fetch("/api/cases")
    .then((response) => response.json())
    .then(({ cases }) => showCaseLinks(cases))
    .catch(() => { status.textContent = "Nie udało się wczytać listy przypadków."; });
  fetch("/api/case" + caseQuery)
    .then((response) => {
      if (!response.ok) throw new Error();
      return response.json();
    })
    .then(({ opening, profile, trust: initialTrust, fact_count }) => {
      trust = initialTrust;
      factCount = fact_count;
      showStats();
      document.querySelector("#profile-demographics").textContent = profile.sex + ", lat " + profile.age;
      document.querySelector("#profile-background").textContent = profile.background;
      if (profile.history?.length) {
        const entries = document.querySelector("#history-entries");
        for (const { when, detail } of profile.history) {
          const entry = document.createElement("li");
          const title = document.createElement("strong");
          title.textContent = when;
          entry.append(title, document.createTextNode(detail));
          entries.append(entry);
        }
        document.querySelector("#patient-history").hidden = false;
      }
      addMessage("Pacjent", opening);
      document.querySelector("#case-summary").textContent = opening;
      testOrder.hidden = false;
    })
    .catch(() => { status.textContent = "Nie udało się wczytać przypadku. Odśwież stronę."; })
    .finally(() => { button.disabled = false; });
}









