const mic = document.querySelector("#mic");
const autoVoice = document.querySelector("#auto-voice");
const player = document.querySelector("#voice-player");

let recorder;
let audioUrl;
let playback = 0;

function stopVoice() {
  playback += 1;
  player.pause();
  player.hidden = true;
  player.removeAttribute("src");
  if (audioUrl) URL.revokeObjectURL(audioUrl);
  audioUrl = undefined;
}

async function playPatient(text) {
  stopVoice();
  const request = playback;
  try {
    const response = await fetch("/api/voice/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) throw new Error();
    const audio = await response.blob();
    if (request !== playback) return;
    audioUrl = URL.createObjectURL(audio);
    player.src = audioUrl;
    player.hidden = false;
    await player.play();
  } catch {
    if (request === playback) status.textContent = "Nie udało się automatycznie odtworzyć głosu. Użyj odtwarzacza lub kliknij „Odsłuchaj”.";
  }
}

autoVoice.addEventListener("change", () => {
  if (!autoVoice.checked) stopVoice();
});

function finishRecording() {
  if (recorder?.state === "recording") recorder.stop();
}

mic.addEventListener("click", async () => {
  if (recorder?.state === "recording") {
    finishRecording();
    return;
  }
  if (button.disabled || !navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    if (!button.disabled) status.textContent = "Mikrofon jest niedostępny w tej przeglądarce.";
    return;
  }

  mic.disabled = true;
  button.disabled = true;
  let stream;
  try {
    stopVoice();
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (form.hidden) return;
    recorder = new MediaRecorder(stream);
    const chunks = [];
    recorder.addEventListener("dataavailable", (event) => chunks.push(event.data));
    recorder.addEventListener("stop", async () => {
      clearTimeout(limit);
      stream.getTracks().forEach((track) => track.stop());
      mic.textContent = "Nagraj pytanie";
      mic.disabled = true;
      if (!form.hidden) status.textContent = "Rozpoznawanie mowy…";
      try {
        if (form.hidden) return;
        const audio = new Blob(chunks, { type: recorder.mimeType });
        const response = await fetch("/api/voice/transcribe", { method: "POST", body: audio });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Błąd transkrypcji.");
        input.value = [input.value.trim(), data.text].filter(Boolean).join(" ").slice(0, input.maxLength);
        status.textContent = "Sprawdź tekst i kliknij „Wyślij”.";
        input.focus();
      } catch (error) {
        status.textContent = error.message;
      } finally {
        recorder = undefined;
        mic.disabled = false;
        button.disabled = false;
      }
    });
    recorder.start();
    const limit = setTimeout(finishRecording, 30_000);
    mic.textContent = "Zakończ nagranie";
    mic.disabled = false;
    status.textContent = "Nagrywanie…";
  } catch {
    status.textContent = "Nie udało się uruchomić mikrofonu. Sprawdź uprawnienia przeglądarki.";
  } finally {
    if (recorder?.state !== "recording") {
      stream?.getTracks().forEach((track) => track.stop());
      recorder = undefined;
      mic.disabled = false;
      button.disabled = false;
    }
  }
});


