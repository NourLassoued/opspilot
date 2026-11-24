import { Component, computed, input } from '@angular/core';
import { IncidentStatus } from '../core/models';
import { STATUS } from './labels';

@Component({
  selector: 'app-status-badge',
  template: `<span class="badge" [attr.data-tone]="info().tone">
    @if (pulsing()) {<span class="dot"></span>}{{ info().label }}
  </span>`,
})
export class StatusBadge {
  readonly status = input.required<IncidentStatus>();
  protected readonly info = computed(() => STATUS[this.status()] ?? { label: this.status(), tone: 'neutral' });
  protected readonly pulsing = computed(() => ['INVESTIGATING', 'EXECUTING', 'AWAITING_APPROVAL'].includes(this.status()));
}
