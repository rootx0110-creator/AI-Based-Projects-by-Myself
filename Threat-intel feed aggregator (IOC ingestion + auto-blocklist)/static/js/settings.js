"use strict";

async function loadSettings() {
  const s = await window.api.get("/api/settings");
  document.getElementById("sConf").value = s.min_confidence;
  document.getElementById("sAuto").value = s.auto_blocklist;
  document.getElementById("sExp").value = s.expiry_days;
}

async function save() {
  const s = {
    min_confidence: document.getElementById("sConf").value,
    auto_blocklist: document.getElementById("sAuto").value,
    expiry_days: document.getElementById("sExp").value,
  };
  await window.api.post("/api/settings", s);
  document.getElementById("settingsMsg").textContent = "Saved " + new Date().toLocaleTimeString();
  window.toast("Settings saved", "ok");
}

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  document.getElementById("btnSaveSettings").addEventListener("click", save);
});