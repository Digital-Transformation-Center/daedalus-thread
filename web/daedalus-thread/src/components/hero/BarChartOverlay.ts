/**
 * Defense-grade tactical telemetry overlay.
 * Renders stylized labeled metric channels (SPAN, SWEEP, FUSE, CHUB, TAIL, THICK)
 * that adapt dynamically as airframe morphs.
 */

const METRIC_LABELS = ['SPAN', 'SWEEP', 'FUSE', 'PAYLD', 'STAB', 'AERO'];

export class BarChartOverlay {
  private container: HTMLElement;
  private barElements: HTMLDivElement[] = [];
  private valueElements: HTMLSpanElement[] = [];

  /**
   * Initializes the tactical HUD telemetry overlay.
   *
   * @param container Target parent element.
   * @param barCount Number of animated bars to render.
   */
  constructor(container: HTMLElement, barCount = 6) {
    this.container = container;
    this.createGraphic(barCount);
  }

  /**
   * Builds the DOM structure for the defense HUD graphic.
   *
   * @param barCount Number of bars.
   */
  private createGraphic(barCount: number): void {
    const wrapper = document.createElement('div');
    wrapper.className = 'dt-hud-telemetry-panel';
    wrapper.setAttribute('aria-hidden', 'true');

    const header = document.createElement('div');
    header.className = 'dt-hud-telemetry-header';
    header.innerHTML = `
      <span class="dt-hud-pulse-dot"></span>
      <span class="dt-hud-title">AERO SYNTHESIS MATRIX</span>
    `;
    wrapper.appendChild(header);

    const barsGrid = document.createElement('div');
    barsGrid.className = 'dt-hud-bars-grid';

    for (let i = 0; i < barCount; i++) {
      const col = document.createElement('div');
      col.className = 'dt-hud-bar-col';

      const label = document.createElement('span');
      label.className = 'dt-hud-bar-label';
      label.textContent = METRIC_LABELS[i] ?? `CH-${i + 1}`;

      const track = document.createElement('div');
      track.className = 'dt-bar-track';

      const fill = document.createElement('div');
      fill.className = 'dt-bar-fill';
      fill.style.height = '40%';

      track.appendChild(fill);

      const valText = document.createElement('span');
      valText.className = 'dt-hud-bar-val';
      valText.textContent = '40%';

      col.appendChild(track);
      col.appendChild(valText);
      col.appendChild(label);

      barsGrid.appendChild(col);

      this.barElements.push(fill);
      this.valueElements.push(valText);
    }

    wrapper.appendChild(barsGrid);
    this.container.appendChild(wrapper);
  }

  /**
   * Updates bar heights and textual percentage readouts based on normalized parameter values.
   *
   * @param values Array of normalized values between 0.0 and 1.0.
   */
  public update(values: number[]): void {
    for (let i = 0; i < this.barElements.length; i++) {
      const fill = this.barElements[i];
      const valText = this.valueElements[i];
      if (fill) {
        const val = values[i] ?? 0.5;
        const clampedPercent = Math.max(12, Math.min(100, Math.round(val * 100)));
        fill.style.height = `${clampedPercent}%`;
        if (valText) {
          valText.textContent = `${clampedPercent}`;
        }
      }
    }
  }

  /**
   * Cleans up the HUD telemetry elements from the DOM.
   */
  public destroy(): void {
    const wrapper = this.container.querySelector('.dt-hud-telemetry-panel');
    if (wrapper) {
      wrapper.remove();
    }
    this.barElements = [];
    this.valueElements = [];
  }
}

