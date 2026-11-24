import { parseSse } from './sse';

describe('parseSse', () => {
  it('découpe les événements complets et garde le morceau incomplet', () => {
    const { events, rest } = parseSse('event:ready\ndata:ok\n\nevent:incident\ndata:{"id":1}\n\nevent:inci');
    expect(events).toEqual([
      { event: 'ready', data: 'ok' },
      { event: 'incident', data: '{"id":1}' },
    ]);
    expect(rest).toBe('event:inci');
  });

  it('accepte les fins de ligne Windows', () => {
    expect(parseSse('event:incident\r\ndata:{"id":2}\r\n\r\n').events[0].data).toBe('{"id":2}');
  });

  it('ignore un bloc sans données', () => {
    expect(parseSse(':commentaire\n\n').events).toEqual([]);
  });
});
