import brd from "../../../shared/brd.json";
import meeting from "../../../shared/meeting.json";

export const { CHECKLIST, SECTIONS, ANSWER_SECTIONS } = brd;
export const MEETING = meeting;
export const meetingLanguage = transcript => Object.entries(meeting.transcript).find(([, text]) => (transcript || "").startsWith(text))?.[0] || null;

// "[Owner] words" lines carry the speaker; requirements inherit the speaker of the line that contains their quote.
export const speakerLine = (speaker, text) => (speaker ? `[${speaker}] ` : "") + text.trim();
export function speakerOf(quote, transcript) {
  if (!quote) return null;
  const line = (transcript || "").split("\n").find(l => l.includes(quote));
  return line?.match(/^\[([^\]]{1,60})\]/)?.[1] || null;
}

// Sarvam returns chunk-level timestamps (phrases, not words). Map a quote to the chunks it overlaps.
export function clipFor(quote, evidence) {
  const ts = evidence?.timestamps, text = evidence?.transcript || "";
  if (!quote || !ts?.words?.length) return { start: null, end: null };
  const qStart = text.indexOf(quote), qEnd = qStart + quote.length;
  let cursor = 0, start = null, end = null;
  ts.words.forEach((chunk, i) => {
    const at = text.indexOf(chunk, cursor);
    const overlaps = at >= 0 && qStart >= 0 ? at < qEnd && at + chunk.length > qStart : chunk.includes(quote) || quote.includes(chunk);
    if (at >= 0) cursor = at + chunk.length;
    if (overlaps) {
      start = start == null ? ts.start_time_seconds[i] : Math.min(start, ts.start_time_seconds[i]);
      end = end == null ? ts.end_time_seconds[i] : Math.max(end, ts.end_time_seconds[i]);
    }
  });
  if (start == null || end == null) return { start: null, end: null };
  const s = Math.max(0, Math.floor(start * 10) / 10), e = Math.min(evidence.duration || Infinity, Math.ceil(end * 10) / 10);
  return e > s ? { start: s, end: e } : { start: null, end: null };
}
