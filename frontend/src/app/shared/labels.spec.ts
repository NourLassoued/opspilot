import { statusLabel, timeAgo } from './labels';

describe('labels', () => {
  it('traduit les statuts', () => {
    expect(statusLabel('AWAITING_APPROVAL')).toBe('Attend votre décision');
    expect(statusLabel('RESOLVED')).toBe('Résolu');
  });

  it('affiche une durée lisible', () => {
    const now = new Date('2026-11-23T10:00:00Z').getTime();
    expect(timeAgo('2026-11-23T09:59:40Z', now)).toBe("à l'instant");
    expect(timeAgo('2026-11-23T09:57:00Z', now)).toBe('il y a 3 min');
    expect(timeAgo('2026-11-23T07:00:00Z', now)).toBe('il y a 3 h');
  });
});
