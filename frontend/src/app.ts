import { LitElement, css, html, nothing } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { createVocabClient } from './api/client.ts';
import { ApiError } from './api/errors.ts';
import type { DeckSummary } from './api/types.ts';

type DeckListStatus = 'loading' | 'ready' | 'error';

const vocabClient = createVocabClient();

/**
 * Standalone navigation shell for server-authoritative decks.
 *
 * This element deliberately retains only transient display and form state. Deck
 * mutations must be followed by a successful fresh GET /vocab/decks before the
 * UI makes any success or selection claim about the server's deck data.
 */
@customElement('flashcard-app')
export class FlashcardApp extends LitElement {
  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      color: var(--color-text-primary, #0f172a);
      background: var(--color-bg, #f8fafc);
      font-family: var(--font-sans, sans-serif);
    }

    .shell { max-width: 960px; margin: 0 auto; padding: var(--space-8, 2rem) var(--space-4, 1rem); }
    header { display: flex; align-items: end; justify-content: space-between; gap: var(--space-4, 1rem); margin-bottom: var(--space-6, 1.5rem); }
    h1, h2, p { margin-top: 0; }
    h1 { margin-bottom: var(--space-1, .25rem); font-size: var(--font-size-3xl, 1.875rem); }
    h2 { margin-bottom: var(--space-2, .5rem); font-size: var(--font-size-xl, 1.25rem); }
    .subtitle, .muted { color: var(--color-text-secondary, #475569); }
    .panel { padding: var(--space-6, 1.5rem); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-lg, .5rem); background: var(--color-surface, #fff); box-shadow: var(--shadow-sm, 0 1px 2px rgba(0,0,0,.05)); }
    .toolbar, .deck-heading, .form-row, .actions { display: flex; gap: var(--space-3, .75rem); align-items: center; }
    .toolbar, .deck-heading { justify-content: space-between; }
    .form-row { margin: var(--space-5, 1.25rem) 0; align-items: end; }
    label { display: grid; gap: var(--space-1, .25rem); flex: 1; font-size: var(--font-size-sm, .875rem); font-weight: var(--font-weight-medium, 500); }
    input { width: 100%; padding: var(--space-2, .5rem) var(--space-3, .75rem); color: inherit; background: var(--color-surface, #fff); border: 1px solid var(--color-border-hover, #cbd5e1); border-radius: var(--radius-sm, .25rem); font: inherit; }
    button { min-height: 2.5rem; padding: var(--space-2, .5rem) var(--space-4, 1rem); color: var(--color-text-primary, #0f172a); border: 1px solid var(--color-border-hover, #cbd5e1); border-radius: var(--radius-sm, .25rem); background: var(--color-surface, #fff); cursor: pointer; font: inherit; font-weight: var(--font-weight-medium, 500); }
    button:hover:not(:disabled) { background: var(--color-surface-hover, #f1f5f9); }
    button:focus-visible, input:focus-visible { outline: 3px solid var(--color-primary-light, #dbeafe); outline-offset: 2px; }
    button.primary { color: var(--color-text-inverse, #fff); border-color: var(--color-primary, #2563eb); background: var(--color-primary, #2563eb); }
    button.primary:hover:not(:disabled) { background: var(--color-primary-hover, #1d4ed8); }
    button.danger { color: var(--color-danger, #dc2626); }
    button:disabled { cursor: wait; opacity: .6; }
    .notice { margin-bottom: var(--space-4, 1rem); padding: var(--space-3, .75rem); border-radius: var(--radius-sm, .25rem); }
    .notice.error { color: #991b1b; background: var(--color-danger-light, #fef2f2); }
    .notice.success { color: #166534; background: var(--color-success-light, #f0fdf4); }
    .deck-list { display: grid; gap: var(--space-3, .75rem); padding: 0; margin: var(--space-5, 1.25rem) 0 0; list-style: none; }
    .deck { display: grid; grid-template-columns: 1fr auto; gap: var(--space-4, 1rem); align-items: center; padding: var(--space-4, 1rem); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-md, .375rem); }
    .deck-open { min-height: 0; padding: 0; border: 0; background: transparent; text-align: left; }
    .deck-open:hover:not(:disabled) { background: transparent; text-decoration: underline; }
    .deck-name { display: block; font-weight: var(--font-weight-semibold, 600); }
    .deck-stats { display: block; margin-top: var(--space-1, .25rem); color: var(--color-text-secondary, #475569); font-size: var(--font-size-sm, .875rem); }
    .empty, .loading { padding: var(--space-8, 2rem) 0; text-align: center; color: var(--color-text-secondary, #475569); }
    .confirm { border-color: var(--color-warning, #d97706); background: var(--color-warning-light, #fffbeb); }
    @media (max-width: 560px) { header, .form-row, .deck-heading { align-items: stretch; flex-direction: column; } .deck { grid-template-columns: 1fr; } }
  `;

  @state() private decks: DeckSummary[] = [];
  @state() private deckStatus: DeckListStatus = 'loading';
  @state() private errorMessage = '';
  @state() private successMessage = '';
  @state() private newDeckName = '';
  @state() private selectedDeckId: number | null = null;
  @state() private pendingDeleteDeckId: number | null = null;
  @state() private isCreating = false;
  @state() private isDeleting = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.loadDecks();
  }

  /**
   * Reconcile displayed decks with the server and return that authoritative list.
   * A refresh failure is intentionally observable to callers, so mutation flows
   * cannot turn it into a false success message.
   */
  private async loadDecks(): Promise<DeckSummary[] | null> {
    this.deckStatus = 'loading';
    this.errorMessage = '';
    this.successMessage = '';
    try {
      const decks = await vocabClient.getDecks();
      this.decks = decks;
      if (this.selectedDeckId !== null && !decks.some((deck) => deck.id === this.selectedDeckId)) {
        this.selectedDeckId = null;
      }
      this.deckStatus = 'ready';
      return decks;
    } catch (error) {
      this.deckStatus = 'error';
      this.errorMessage = this.messageFor(error, 'Decks could not be loaded.');
      return null;
    }
  }

  private async createDeck(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const name = this.newDeckName.trim();
    if (!name) {
      this.successMessage = '';
      this.errorMessage = 'Enter a deck name before creating it.';
      return;
    }

    this.isCreating = true;
    this.errorMessage = '';
    this.successMessage = '';
    try {
      const createdDeck = await vocabClient.createDeck(name);
      this.newDeckName = '';
      const refreshedDecks = await this.loadDecks();
      if (refreshedDecks === null) {
        this.errorMessage = `“${createdDeck.name}” may have been created, but the deck list could not be refreshed.`;
        return;
      }
      const refreshedDeck = refreshedDecks.find((deck) => deck.id === createdDeck.id);
      if (!refreshedDeck) {
        this.errorMessage = `The server did not return “${createdDeck.name}” after creation. It was not opened.`;
        return;
      }
      this.selectedDeckId = refreshedDeck.id;
      this.successMessage = `Created and opened “${refreshedDeck.name}”.`;
    } catch (error) {
      this.successMessage = '';
      this.errorMessage = this.messageFor(error, 'Deck could not be created.');
    } finally {
      this.isCreating = false;
    }
  }

  private async deleteDeck(deck: DeckSummary): Promise<void> {
    this.isDeleting = true;
    this.errorMessage = '';
    this.successMessage = '';
    try {
      const result = await vocabClient.deleteDeck(deck.id);
      if (!result.deleted) {
        throw new Error('The server did not confirm deletion.');
      }
      this.pendingDeleteDeckId = null;
      const refreshedDecks = await this.loadDecks();
      if (refreshedDecks === null) {
        this.errorMessage = `“${deck.name}” may have been deleted, but the deck list could not be refreshed.`;
        return;
      }
      if (refreshedDecks.some((refreshedDeck) => refreshedDeck.id === deck.id)) {
        this.errorMessage = `The server still returned “${deck.name}” after deletion. The deletion was not confirmed.`;
        return;
      }
      if (this.selectedDeckId === deck.id) this.selectedDeckId = null;
      this.successMessage = `Deleted “${deck.name}”. Notes with review history were preserved by the server.`;
    } catch (error) {
      this.successMessage = '';
      this.errorMessage = this.messageFor(error, 'Deck could not be deleted.');
    } finally {
      this.isDeleting = false;
    }
  }

  private messageFor(error: unknown, fallback: string): string {
    if (error instanceof ApiError && error.detail) return error.detail;
    if (error instanceof Error && error.message) return error.message;
    return fallback;
  }

  private selectedDeck(): DeckSummary | undefined {
    return this.decks.find((deck) => deck.id === this.selectedDeckId);
  }

  private renderNotices() {
    return html`
      ${this.errorMessage ? html`<div class="notice error" role="alert">${this.errorMessage}</div>` : nothing}
      ${this.successMessage ? html`<div class="notice success" role="status">${this.successMessage}</div>` : nothing}
    `;
  }

  private renderDeckList() {
    if (this.deckStatus === 'loading') {
      return html`<p class="loading" role="status">Loading decks…</p>`;
    }
    if (this.deckStatus === 'error') {
      return html`<div class="empty"><p>We could not reach your deck list.</p><button @click=${this.loadDecks}>Try again</button></div>`;
    }
    if (this.decks.length === 0) {
      return html`<div class="empty"><p>No decks yet. Create one to begin organizing German vocabulary.</p></div>`;
    }
    return html`
      <ul class="deck-list" aria-label="Your decks">
        ${this.decks.map((deck) => html`
          <li class="deck">
            <button class="deck-open" @click=${() => { this.selectedDeckId = deck.id; this.successMessage = ''; }} aria-label=${`Open ${deck.name}`}>
              <span class="deck-name">${deck.name}</span>
              <span class="deck-stats">${deck.card_count} ${deck.card_count === 1 ? 'card' : 'cards'} · ${deck.due_count} due · ${deck.mastery_percent}% mastered</span>
            </button>
            ${this.pendingDeleteDeckId === deck.id ? html`
              <div class="actions confirm" aria-label=${`Confirm deletion of ${deck.name}`}>
                <button class="danger" ?disabled=${this.isDeleting} @click=${() => void this.deleteDeck(deck)}>${this.isDeleting ? 'Deleting…' : 'Confirm delete'}</button>
                <button ?disabled=${this.isDeleting} @click=${() => { this.pendingDeleteDeckId = null; }}>Cancel</button>
              </div>
            ` : html`
              <button class="danger" @click=${() => { this.pendingDeleteDeckId = deck.id; this.successMessage = ''; }}>Delete</button>
            `}
          </li>
        `)}
      </ul>
    `;
  }

  private renderDeckDetail(deck: DeckSummary) {
    return html`
      <section class="panel" aria-labelledby="deck-title">
        <div class="deck-heading">
          <div>
            <h2 id="deck-title">${deck.name}</h2>
            <p class="muted">${deck.card_count} ${deck.card_count === 1 ? 'card' : 'cards'} · ${deck.due_count} due · ${deck.mastery_percent}% mastered</p>
          </div>
          <button @click=${() => { this.selectedDeckId = null; }}>All decks</button>
        </div>
        <p>This deck is ready for the next workflow. Card data and review scheduling remain on the server.</p>
      </section>
    `;
  }

  render() {
    const selectedDeck = this.selectedDeck();
    const showDeckList = this.deckStatus !== 'ready' || !selectedDeck;
    return html`
      <div class="shell">
        <header>
          <div>
            <h1>Flashcards</h1>
            <div class="subtitle">German vocabulary</div>
          </div>
          <button @click=${this.loadDecks} ?disabled=${this.deckStatus === 'loading'}>${this.deckStatus === 'loading' ? 'Refreshing…' : 'Refresh decks'}</button>
        </header>
        ${this.renderNotices()}
        ${showDeckList ? html`
          <main class="panel">
            <div class="toolbar"><h2>Your decks</h2><span class="muted" aria-live="polite">${this.deckStatus === 'ready' ? 'Server-synced' : ''}</span></div>
            <form class="form-row" @submit=${this.createDeck}>
              <label>New deck name
                <input .value=${this.newDeckName} @input=${(event: InputEvent) => { this.newDeckName = (event.target as HTMLInputElement).value; }} ?disabled=${this.isCreating} maxlength="200" autocomplete="off" />
              </label>
              <button class="primary" type="submit" ?disabled=${this.isCreating}>${this.isCreating ? 'Creating…' : 'Create deck'}</button>
            </form>
            ${this.renderDeckList()}
          </main>
        ` : this.renderDeckDetail(selectedDeck)}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'flashcard-app': FlashcardApp;
  }
}
