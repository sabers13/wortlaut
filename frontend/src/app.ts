import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';

@customElement('flashcard-app')
export class FlashcardApp extends LitElement {
  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      color: var(--color-text-primary, #0f172a);
      background-color: var(--color-bg, #f8fafc);
      font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
    }

    .shell {
      max-width: 960px;
      margin: 0 auto;
      padding: var(--space-6, 1.5rem) var(--space-4, 1rem);
    }

    header {
      margin-bottom: var(--space-6, 1.5rem);
      padding-bottom: var(--space-4, 1rem);
      border-bottom: 1px solid var(--color-border, #e2e8f0);
    }

    h1 {
      margin: 0;
      font-size: var(--font-size-2xl, 1.5rem);
      font-weight: var(--font-weight-bold, 700);
      color: var(--color-text-primary, #0f172a);
    }

    .subtitle {
      margin-top: var(--space-1, 0.25rem);
      color: var(--color-text-secondary, #475569);
      font-size: var(--font-size-sm, 0.875rem);
    }

    main {
      background: var(--color-surface, #ffffff);
      border: 1px solid var(--color-border, #e2e8f0);
      border-radius: var(--radius-md, 0.375rem);
      padding: var(--space-6, 1.5rem);
      box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      padding: var(--space-1, 0.25rem) var(--space-2, 0.5rem);
      background-color: var(--color-success-light, #f0fdf4);
      color: var(--color-success, #16a34a);
      border-radius: var(--radius-sm, 0.25rem);
      font-size: var(--font-size-xs, 0.75rem);
      font-weight: var(--font-weight-medium, 500);
    }
  `;

  @state()
  private appTitle: string = 'Flashcards';

  render() {
    return html`
      <div class="shell">
        <header>
          <h1>${this.appTitle}</h1>
          <div class="subtitle">German Vocabulary &amp; Spaced Repetition</div>
        </header>
        <main>
          <div class="status-badge">Ready</div>
          <p>Flashcards root shell initialized.</p>
        </main>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'flashcard-app': FlashcardApp;
  }
}
