import { LitElement, css, html, nothing } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { createVocabClient } from './api/client.ts';
import { ApiError } from './api/errors.ts';
import type { Candidate, CandidateSense, DeckSummary, MeaningLanguage } from './api/types.ts';

type DeckListStatus = 'loading' | 'ready' | 'error';
type LookupStatus = 'idle' | 'loading' | 'ready' | 'error';

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
    input, select, textarea { width: 100%; padding: var(--space-2, .5rem) var(--space-3, .75rem); color: inherit; background: var(--color-surface, #fff); border: 1px solid var(--color-border-hover, #cbd5e1); border-radius: var(--radius-sm, .25rem); font: inherit; }
    textarea { min-height: 8rem; resize: vertical; }
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
    .workflow-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr)); gap: var(--space-5, 1.25rem); margin-top: var(--space-6, 1.5rem); }
    .workflow { padding-top: var(--space-5, 1.25rem); border-top: 1px solid var(--color-border, #e2e8f0); }
    .workflow h3 { margin: 0 0 var(--space-2, .5rem); font-size: var(--font-size-lg, 1.125rem); }
    .workflow form { display: grid; gap: var(--space-3, .75rem); }
    .choice-list, .candidate-list { display: grid; gap: var(--space-2, .5rem); margin: 0; padding: 0; list-style: none; }
    .choice { display: flex; align-items: center; gap: var(--space-2, .5rem); font-weight: var(--font-weight-medium, 500); }
    .choice input { width: auto; }
    .candidate { width: 100%; min-height: 0; text-align: left; }
    .candidate.selected { border-color: var(--color-primary, #2563eb); background: var(--color-primary-light, #dbeafe); }
    .candidate small { display: block; margin-top: var(--space-1, .25rem); color: var(--color-text-secondary, #475569); }
    .selection { margin: 0; padding: var(--space-3, .75rem); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-sm, .25rem); }
    .selection legend { padding: 0 var(--space-1, .25rem); font-weight: var(--font-weight-semibold, 600); }
    .pending { color: var(--color-text-secondary, #475569); background: var(--color-surface-hover, #f1f5f9); }
    .result { margin: 0; color: var(--color-text-secondary, #475569); font-size: var(--font-size-sm, .875rem); }
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
  @state() private lookupQuery = '';
  @state() private lookupStatus: LookupStatus = 'idle';
  @state() private lookupCandidates: Candidate[] = [];
  @state() private lookupAssetToken = '';
  @state() private selectedCandidate: Candidate | null = null;
  @state() private selectedSenseRef: string | null = null;
  @state() private selectedMeaningLanguages: MeaningLanguage[] = ['de', 'en'];
  @state() private userMeaningDe = '';
  @state() private userMeaningEn = '';
  @state() private manualDeckId: number | null = null;
  @state() private isSavingNote = false;
  @state() private importDeckName = '';
  @state() private importText = '';
  @state() private importFileName = '';
  @state() private isReadingImportFile = false;
  @state() private isImporting = false;
  @state() private isExporting = false;

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
      if (this.manualDeckId !== null && !decks.some((deck) => deck.id === this.manualDeckId)) {
        this.manualDeckId = null;
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
      this.manualDeckId = refreshedDeck.id;
      this.importDeckName = refreshedDeck.name;
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

  private manualDeck(): DeckSummary | undefined {
    return this.decks.find((deck) => deck.id === this.manualDeckId);
  }

  private resetManualSelection(): void {
    this.selectedCandidate = null;
    this.selectedSenseRef = null;
    this.selectedMeaningLanguages = ['de', 'en'];
    this.userMeaningDe = '';
    this.userMeaningEn = '';
  }

  private selectCandidate(candidate: Candidate): void {
    this.selectedCandidate = candidate;
    this.selectedSenseRef = candidate.status === 'resolved'
      ? candidate.senses?.[0]?.sense_semantic_ref ?? null
      : null;
  }

  private toggleMeaningLanguage(language: MeaningLanguage, checked: boolean): void {
    this.selectedMeaningLanguages = checked
      ? [...new Set([...this.selectedMeaningLanguages, language])]
      : this.selectedMeaningLanguages.filter((selected) => selected !== language);
  }

  private async lookup(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const query = this.lookupQuery.trim();
    if (!query) {
      this.errorMessage = 'Enter a German word before looking it up.';
      this.successMessage = '';
      return;
    }

    this.lookupStatus = 'loading';
    this.lookupCandidates = [];
    this.lookupAssetToken = '';
    this.resetManualSelection();
    this.errorMessage = '';
    this.successMessage = '';
    try {
      const result = await vocabClient.lookup(query);
      this.lookupCandidates = result.candidates;
      this.lookupAssetToken = result.asset_token;
      this.lookupStatus = 'ready';
      const soleCandidate = result.candidates.length === 1 ? result.candidates[0] : undefined;
      if (soleCandidate) this.selectCandidate(soleCandidate);
    } catch (error) {
      this.lookupStatus = 'error';
      this.errorMessage = this.messageFor(error, 'German vocabulary could not be looked up.');
    }
  }

  private userMeanings(): Record<string, string> | undefined {
    const meanings: Record<string, string> = {};
    if (this.userMeaningDe.trim()) meanings.de = this.userMeaningDe.trim();
    if (this.userMeaningEn.trim()) meanings.en = this.userMeaningEn.trim();
    return Object.keys(meanings).length ? meanings : undefined;
  }

  private async saveManualNote(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const candidate = this.selectedCandidate;
    const deck = this.manualDeck();
    if (!candidate || !this.lookupAssetToken) {
      this.errorMessage = 'Look up and select a German vocabulary candidate before saving.';
      this.successMessage = '';
      return;
    }
    if (!deck) {
      this.errorMessage = 'Select a deck before saving this vocabulary.';
      this.successMessage = '';
      return;
    }
    if (!this.selectedMeaningLanguages.length) {
      this.errorMessage = 'Select German, English, or both meaning languages.';
      this.successMessage = '';
      return;
    }
    if (candidate.status === 'resolved' && !this.selectedSenseRef) {
      this.errorMessage = 'Select a meaning for this resolved dictionary entry.';
      this.successMessage = '';
      return;
    }
    if (candidate.status === 'derived_compound' && !candidate.component_refs?.length) {
      this.errorMessage = 'This derived compound has no supported component bindings to save.';
      this.successMessage = '';
      return;
    }

    this.isSavingNote = true;
    this.errorMessage = '';
    this.successMessage = '';
    try {
      const result = await vocabClient.createNote({
        asset_token: this.lookupAssetToken,
        lemma_semantic_ref: candidate.lemma_semantic_ref,
        sense_semantic_ref: this.selectedSenseRef,
        status: candidate.status,
        component_refs: candidate.component_refs,
        meaning_languages: this.selectedMeaningLanguages,
        deck_name: deck.name,
        user_meanings: this.userMeanings(),
      });
      const refreshedDecks = await this.loadDecks();
      if (refreshedDecks === null) {
        this.errorMessage = `“${candidate.lemma}” may have been saved, but the deck list could not be refreshed.`;
        return;
      }
      const refreshedDeck = refreshedDecks.find((item) => item.id === result.deck_id);
      if (result.deck_id !== deck.id || !refreshedDeck) {
        this.errorMessage = `The server did not confirm “${candidate.lemma}” in the selected deck. It was not reported as saved.`;
        return;
      }
      this.selectedDeckId = refreshedDeck.id;
      this.manualDeckId = refreshedDeck.id;
      this.successMessage = `Saved “${candidate.lemma}” to “${refreshedDeck.name}”.`;
      this.lookupQuery = '';
      this.lookupCandidates = [];
      this.lookupAssetToken = '';
      this.lookupStatus = 'idle';
      this.resetManualSelection();
    } catch (error) {
      this.successMessage = '';
      this.errorMessage = this.messageFor(error, 'Vocabulary could not be saved.');
    } finally {
      this.isSavingNote = false;
    }
  }

  private async readImportFile(event: Event): Promise<void> {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.isReadingImportFile = true;
    this.errorMessage = '';
    this.successMessage = '';
    try {
      this.importText = await file.text();
      this.importFileName = file.name;
    } catch (error) {
      this.importFileName = '';
      this.errorMessage = this.messageFor(error, 'The selected file could not be read.');
    } finally {
      this.isReadingImportFile = false;
    }
  }

  private async importCsv(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const deckName = this.importDeckName.trim();
    const csvText = this.importText.trim();
    if (!deckName) {
      this.errorMessage = 'Enter the deck name for this CSV import.';
      this.successMessage = '';
      return;
    }
    if (!csvText) {
      this.errorMessage = 'Paste vocabulary lines or choose a CSV/text file before importing.';
      this.successMessage = '';
      return;
    }

    this.isImporting = true;
    this.errorMessage = '';
    this.successMessage = '';
    try {
      const result = await vocabClient.importCsv({ csv_text: csvText, deck_name: deckName });
      const refreshedDecks = await this.loadDecks();
      if (refreshedDecks === null) {
        this.errorMessage = `The import may have completed, but the deck list could not be refreshed.`;
        return;
      }
      const importedDeck = refreshedDecks.find((deck) => deck.id === result.deck_id);
      if (!importedDeck) {
        this.errorMessage = 'The server did not return the import deck after completion. The import was not reported as successful.';
        return;
      }
      this.selectedDeckId = importedDeck.id;
      this.manualDeckId = importedDeck.id;
      this.importDeckName = importedDeck.name;
      this.successMessage = `Imported ${result.total_words} ${result.total_words === 1 ? 'word' : 'words'} into “${importedDeck.name}”: ${result.notes_created} created, ${result.notes_reused} reused.`;
      this.importText = '';
      this.importFileName = '';
    } catch (error) {
      this.successMessage = '';
      this.errorMessage = this.messageFor(error, 'CSV import could not be completed.');
    } finally {
      this.isImporting = false;
    }
  }

  private async exportTsv(deck: DeckSummary): Promise<void> {
    this.isExporting = true;
    this.errorMessage = '';
    this.successMessage = '';
    try {
      const tsv = await vocabClient.exportAnki(deck.id);
      const url = URL.createObjectURL(new Blob([tsv], { type: 'text/tab-separated-values;charset=utf-8' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `${deck.name.replace(/[^a-z0-9._-]+/gi, '-') || 'flashcards'}.tsv`;
      link.click();
      URL.revokeObjectURL(url);
      this.successMessage = `Prepared a TSV export for “${deck.name}”.`;
    } catch (error) {
      this.errorMessage = this.messageFor(error, 'TSV export could not be prepared.');
    } finally {
      this.isExporting = false;
    }
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
            <button class="deck-open" @click=${() => { this.selectedDeckId = deck.id; this.manualDeckId = deck.id; this.importDeckName = deck.name; this.successMessage = ''; }} aria-label=${`Open ${deck.name}`}>
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

  private renderSenseChoices(senses: CandidateSense[]) {
    return html`
      <fieldset class="selection">
        <legend>Dictionary meaning</legend>
        <ul class="choice-list">
          ${senses.map((sense) => html`
            <li>
              <label class="choice">
                <input
                  type="radio"
                  name="sense"
                  .value=${sense.sense_semantic_ref}
                  .checked=${this.selectedSenseRef === sense.sense_semantic_ref}
                  @change=${() => { this.selectedSenseRef = sense.sense_semantic_ref; }}
                />
                <span>${sense.gloss || `Meaning ${sense.ord}`}</span>
              </label>
            </li>
          `)}
        </ul>
      </fieldset>
    `;
  }

  private renderManualCreation() {
    const candidate = this.selectedCandidate;
    const manualDeck = this.manualDeck();
    return html`
      <section class="workflow" aria-labelledby="manual-title">
        <h3 id="manual-title">Add German vocabulary</h3>
        <p class="muted">Look up a German word, choose its dictionary meaning, then let the server create the note.</p>
        <form @submit=${this.lookup}>
          <label>German word
            <input
              .value=${this.lookupQuery}
              @input=${(event: InputEvent) => { this.lookupQuery = (event.target as HTMLInputElement).value; }}
              ?disabled=${this.lookupStatus === 'loading' || this.isSavingNote}
              autocomplete="off"
              placeholder="e.g. anrufen"
            />
          </label>
          <div class="actions"><button class="primary" type="submit" ?disabled=${this.lookupStatus === 'loading' || this.isSavingNote}>${this.lookupStatus === 'loading' ? 'Looking up…' : 'Look up'}</button></div>
        </form>
        ${this.lookupStatus === 'loading' ? html`<p class="result" role="status">Looking up the active dictionary…</p>` : nothing}
        ${this.lookupStatus === 'ready' && !this.lookupCandidates.length ? html`<p class="result">No dictionary candidate was returned. Try a different German form.</p>` : nothing}
        ${this.lookupCandidates.length ? html`
          <fieldset class="selection">
            <legend>Select vocabulary</legend>
            <ul class="candidate-list">
              ${this.lookupCandidates.map((item) => html`
                <li>
                  <button
                    class="candidate ${candidate === item ? 'selected' : ''}"
                    type="button"
                    @click=${() => this.selectCandidate(item)}
                    aria-pressed=${candidate === item ? 'true' : 'false'}
                  >
                    ${item.lemma} · ${item.pos}
                    <small>${item.status === 'resolved' ? 'Dictionary entry' : item.status.replace('_', ' ')}</small>
                  </button>
                </li>
              `)}
            </ul>
          </fieldset>
        ` : nothing}
        ${candidate ? html`
          <form @submit=${this.saveManualNote}>
            ${candidate.status === 'resolved' ? (candidate.senses?.length
              ? this.renderSenseChoices(candidate.senses)
              : html`<p class="result">This result has no selectable sense and cannot be saved as a resolved note.</p>`) : nothing}
            ${candidate.status === 'derived_compound' ? html`<p class="result">The server will retain this compound’s supported component bindings.</p>` : nothing}
            <label>Deck
              <select
                .value=${manualDeck ? String(manualDeck.id) : ''}
                @change=${(event: Event) => { const value = (event.target as HTMLSelectElement).value; this.manualDeckId = value ? Number(value) : null; }}
                ?disabled=${this.isSavingNote}
              >
                <option value="">Select a deck</option>
                ${this.decks.map((item) => html`<option value=${item.id}>${item.name}</option>`)}
              </select>
            </label>
            <fieldset class="selection">
              <legend>Meaning languages</legend>
              <label class="choice"><input type="checkbox" .checked=${this.selectedMeaningLanguages.includes('de')} @change=${(event: Event) => this.toggleMeaningLanguage('de', (event.target as HTMLInputElement).checked)} /> German (DE)</label>
              <label class="choice"><input type="checkbox" .checked=${this.selectedMeaningLanguages.includes('en')} @change=${(event: Event) => this.toggleMeaningLanguage('en', (event.target as HTMLInputElement).checked)} /> English (EN)</label>
            </fieldset>
            <label>Your German meaning <span class="muted">(optional)</span>
              <input .value=${this.userMeaningDe} @input=${(event: InputEvent) => { this.userMeaningDe = (event.target as HTMLInputElement).value; }} ?disabled=${this.isSavingNote} autocomplete="off" />
            </label>
            <label>Your English meaning <span class="muted">(optional)</span>
              <input .value=${this.userMeaningEn} @input=${(event: InputEvent) => { this.userMeaningEn = (event.target as HTMLInputElement).value; }} ?disabled=${this.isSavingNote} autocomplete="off" />
            </label>
            <div class="actions"><button class="primary" type="submit" ?disabled=${this.isSavingNote}>${this.isSavingNote ? 'Saving…' : 'Save vocabulary'}</button></div>
          </form>
        ` : nothing}
      </section>
    `;
  }

  private renderImportExport(deck: DeckSummary) {
    return html`
      <section class="workflow" aria-labelledby="import-export-title">
        <h3 id="import-export-title">Import & export</h3>
        <form @submit=${this.importCsv}>
          <label>CSV import deck name
            <input
              .value=${this.importDeckName}
              @input=${(event: InputEvent) => { this.importDeckName = (event.target as HTMLInputElement).value; }}
              list="deck-names"
              ?disabled=${this.isImporting || this.isReadingImportFile}
              autocomplete="off"
            />
          </label>
          <datalist id="deck-names">${this.decks.map((item) => html`<option value=${item.name}></option>`)}</datalist>
          <label>Vocabulary lines
            <textarea .value=${this.importText} @input=${(event: InputEvent) => { this.importText = (event.target as HTMLTextAreaElement).value; }} ?disabled=${this.isImporting || this.isReadingImportFile} placeholder="Haus&#10;anrufen&#10;Feierabend"></textarea>
          </label>
          <label>Or choose a CSV/text file
            <input type="file" accept=".csv,.txt,text/csv,text/plain" @change=${this.readImportFile} ?disabled=${this.isImporting || this.isReadingImportFile} />
          </label>
          ${this.isReadingImportFile ? html`<p class="result" role="status">Reading file…</p>` : nothing}
          ${this.importFileName ? html`<p class="result">Using text from ${this.importFileName}.</p>` : nothing}
          <div class="actions"><button class="primary" type="submit" ?disabled=${this.isImporting || this.isReadingImportFile}>${this.isImporting ? 'Importing…' : 'Import CSV'}</button></div>
        </form>
        <div class="workflow-grid">
          <div>
            <h3>TSV export</h3>
            <p class="muted">Download the selected deck in the available Anki TSV format.</p>
            <button @click=${() => void this.exportTsv(deck)} ?disabled=${this.isExporting}>${this.isExporting ? 'Preparing TSV…' : `Export “${deck.name}” TSV`}</button>
          </div>
          <div>
            <h3>TSV import</h3>
            <p class="muted">Pending — this product has no accepted TSV import contract yet.</p>
            <button class="pending" disabled>TSV import pending</button>
          </div>
          <div>
            <h3>APKG import</h3>
            <p class="muted">Pending — this product has no accepted APKG import contract yet.</p>
            <button class="pending" disabled>APKG import pending</button>
          </div>
          <div>
            <h3>APKG export</h3>
            <p class="muted">Pending — this product has no accepted APKG export contract yet.</p>
            <button class="pending" disabled>APKG export pending</button>
          </div>
        </div>
      </section>
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
        <p>Card data and review scheduling remain on the server.</p>
        <div class="workflow-grid">
          ${this.renderManualCreation()}
          ${this.renderImportExport(deck)}
        </div>
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
