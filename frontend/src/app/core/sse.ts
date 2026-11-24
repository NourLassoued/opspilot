/** Un événement Server-Sent Events : "event: incident" + "data: {...}". */
export interface SseEvent {
  event: string;
  data: string;
}

/**
 * Découpe le texte reçu en événements SSE (séparés par une ligne vide).
 * Renvoie les événements complets et le morceau incomplet à garder pour la suite.
 */
export function parseSse(buffer: string): { events: SseEvent[]; rest: string } {
  const blocks = buffer.replace(/\r\n/g, '\n').split('\n\n');
  const rest = blocks.pop() ?? '';
  const events: SseEvent[] = [];
  for (const block of blocks) {
    let event = 'message';
    const data: string[] = [];
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
    }
    if (data.length) events.push({ event, data: data.join('\n') });
  }
  return { events, rest };
}
