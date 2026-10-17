// The interface follows the language the owner chose. Strings are translated once by Sarvam Translate
// (backend/tools/translate_ui.py writes shared/ui-strings.json) so the app itself speaks Hindi, Kannada, Tamil, Telugu,
// Marathi or Bengali, not only its voice. English is the source text; `?ui=english` pins the interface to English.
import UI from "../../shared/ui-strings.json";

const forced = typeof location !== "undefined" ? new URLSearchParams(location.search).get("ui") : null;

export function translator(lang) {
  const code = forced || lang;
  const map = code && code !== "english" ? UI[code] : null;
  if (!map) return s => s;
  return s => map[s] || s;
}

export const UI_LANGS = Object.keys(UI);
