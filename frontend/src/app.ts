import { LitElement, css, html, nothing } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { createVocabClient } from './api/client.ts';
import { ApiError } from './api/errors.ts';
import type {
  Candidate,
  CandidateSense,
  CaptureContext,
  DeckSummary,
  DictionarySettingsInfo,
  MeaningLanguage,
  NextCardData,
  RenderedMeaning,
} from './api/types.ts';
import {
  extraInfoOpenOnCardLoad,
  extraInfoOpenOnPreferenceChange,
  extraInfoOpenOnReveal,
  readAlwaysShowExtraInfo,
  writeAlwaysShowExtraInfo,
} from './study/extra-info-preference.ts';

type DeckListStatus = 'loading' | 'ready' | 'error';
type LookupStatus = 'idle' | 'loading' | 'ready' | 'error';
type CaptureStatus = 'idle' | 'loading' | 'ready' | 'error';
type AppView = 'decks' | 'deck' | 'study' | 'chooser' | 'settings';
type StudyStatus = 'idle' | 'loading' | 'ready' | 'empty' | 'error';
type AudioStatus = 'idle' | 'loading' | 'playing' | 'unavailable';
type RecordingStatus = 'idle' | 'recording' | 'ready' | 'saving' | 'save-error';
type SessionMode = 'offline' | 'online' | 'unconfigured';
type DictionarySettingsStatus = 'loading' | 'ready' | 'error';
type DictionarySettingsAction = 'idle' | 'installing' | 'removing' | 'clearing' | 'switching-online' | 'switching-offline';

const confidenceLabels = [
  ['1', 'Not at all'],
  ['2', 'Barely'],
  ['3', 'With effort'],
  ['4', 'Comfortably'],
  ['5', 'Without doubt'],
] as const;

interface CaptureCandidateSelection {
  candidate: Candidate;
  senseRef: string | null;
}

const vocabClient = createVocabClient();

/**
 * ``window.localStorage`` itself can throw on access (private browsing in
 * some browsers, storage disabled by policy), not just its methods, so the
 * accessor is wrapped too. Returns ``null`` when storage is unavailable;
 * every caller already treats that the same as "nothing persisted".
 */
function localStorageOrNull(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

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
    :host { display: block; min-height: 100vh; color: var(--fg); background: var(--bg); font-family: var(--font-sans); }
    .shell { max-width: 1280px; margin: 0 auto; padding: var(--space-48) var(--space-16); }
    header { display: flex; align-items: end; justify-content: space-between; gap: var(--space-16); margin-bottom: var(--space-32); }
    h1, h2, h3, p { margin-top: 0; }
    h1, h2, h3 { font-family: var(--font-display); font-weight: 600; letter-spacing: -.02em; }
    h1 { margin-bottom: var(--space-4); font-size: clamp(2rem, 5vw, 3.25rem); }
    h2 { margin-bottom: var(--space-8); font-size: 1.75rem; }
    .subtitle, .muted, .result, .caption { color: var(--muted); }
    .caption { font-family: var(--font-mono); font-size: .75rem; letter-spacing: .04em; text-transform: uppercase; }
    .panel { padding: var(--space-32); border: 1px solid var(--border); border-radius: var(--radius-panel); background: var(--surface); box-shadow: var(--shadow-sm); }
    .toolbar, .deck-heading, .form-row, .actions { display: flex; gap: var(--space-12); align-items: center; }
    .toolbar, .deck-heading { justify-content: space-between; }
    .form-row { margin: var(--space-24) 0; align-items: end; }
    label { display: grid; gap: var(--space-4); flex: 1; font-size: .875rem; font-weight: 600; }
    input, select, textarea { width: 100%; padding: 10px var(--space-12); color: var(--fg); background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-control); font: inherit; }
    textarea { min-height: 8rem; resize: vertical; }
    button { min-height: 2.6rem; padding: var(--space-8) var(--space-16); color: var(--fg); border: 1px solid var(--border); border-radius: var(--radius-control); background: var(--surface); cursor: pointer; font: inherit; font-weight: 600; }
    button:hover:not(:disabled) { border-color: var(--accent); }
    button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent), white 65%); outline-offset: 2px; }
    button.primary { color: white; border-color: var(--accent); background: var(--accent); }
    button.primary:hover:not(:disabled) { filter: brightness(.94); }
    button.danger { color: var(--danger); }
    button:disabled { cursor: not-allowed; opacity: .55; }
    .notice, .capture-state { margin-bottom: var(--space-16); padding: var(--space-12); border: 1px solid var(--border); border-radius: var(--radius-control); }
    .notice.error, .capture-state.error { color: var(--danger); background: color-mix(in oklch, var(--danger), white 94%); }
    .notice.success { color: var(--success); background: color-mix(in oklch, var(--success), white 94%); }
    .capture-state.warning { border-color: var(--warning); background: color-mix(in oklch, var(--warning), white 91%); }
    .capture-state p { margin-bottom: var(--space-8); }
    .capture-state p:last-child { margin-bottom: 0; }
    .deck-list { display: grid; gap: var(--space-12); padding: 0; margin: var(--space-24) 0 0; list-style: none; }
    .deck { display: grid; grid-template-columns: 1fr auto; gap: var(--space-16); align-items: center; padding: var(--space-16); border: 1px solid var(--border); border-radius: var(--radius-panel); }
    .deck-open { min-height: 0; padding: 0; border: 0; background: transparent; text-align: left; }
    .deck-open:hover:not(:disabled) { background: transparent; text-decoration: underline; }
    .deck-name { display: block; font-family: var(--font-display); font-size: 1.2rem; font-weight: 600; }
    .deck-stats { display: block; margin-top: var(--space-4); color: var(--muted); font-family: var(--font-mono); font-size: .75rem; }
    .empty, .loading { padding: var(--space-48) 0; text-align: center; color: var(--muted); }
    .confirm { border-color: var(--warning); background: color-mix(in oklch, var(--warning), white 92%); }
    .workflow-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr)); gap: var(--space-32); margin-top: var(--space-32); }
    .workflow { padding-top: var(--space-24); border-top: 1px solid var(--border); }
    .capture-workflow { grid-column: 1 / -1; }
    .workflow h3 { margin: 0 0 var(--space-8); font-size: 1.4rem; }
    .workflow form { display: grid; gap: var(--space-12); }
    .choice-list, .candidate-list { display: grid; gap: var(--space-8); margin: 0; padding: 0; list-style: none; }
    .choice, .candidate-choice { display: flex; align-items: center; gap: var(--space-8); font-weight: 500; }
    .choice input, .candidate-choice input { width: auto; }
    .candidate { width: 100%; min-height: 0; text-align: left; }
    .candidate.selected { border-color: var(--accent); background: color-mix(in oklch, var(--accent), white 94%); }
    .candidate small { display: block; margin-top: var(--space-4); color: var(--muted); }
    .selection { margin: 0; padding: var(--space-16); border: 1px solid var(--border); border-radius: var(--radius-panel); }
    .selection legend { padding: 0 var(--space-4); font-family: var(--font-display); font-weight: 600; }
    .pending { color: var(--muted); background: var(--bg); }
    .selection-preview { margin: 0; padding: var(--space-8) var(--space-12); border-left: 3px solid var(--accent); color: var(--muted); }
    .capture-picker { margin-top: var(--space-24); }
    .capture-candidate { padding: var(--space-12); border: 1px solid var(--border); border-radius: var(--radius-control); }
    .capture-candidate.chosen { border-color: var(--accent); }
    .lemma { font-family: var(--font-display); font-size: 1.25rem; }
    .sense-choices { display: grid; gap: var(--space-8); margin: var(--space-12) 0 0 var(--space-24); border: 0; padding: 0; }
    .sense-choices legend { margin-bottom: var(--space-4); color: var(--muted); font-size: .8rem; }
    .language-chips { display: flex; flex-wrap: wrap; gap: var(--space-8); align-items: center; }
    .language-chips > p { width: 100%; }
    .chip.selected { color: white; border-color: var(--accent); background: var(--accent); }
    .create-actions { flex-wrap: wrap; }
    .disabled-explanation { margin: 0; color: var(--muted); font-size: .875rem; }
    .primary-nav, .bottom-nav { display: flex; gap: var(--space-8); }
    .primary-nav button[aria-current="page"], .bottom-nav button[aria-current="page"] { color: white; border-color: var(--accent); background: var(--accent); }
    .study { max-width: 760px; margin: 0 auto; }
    .study-heading { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-16); margin-bottom: var(--space-16); }
    .study-heading h2 { margin: 0; }
    .card-stage { min-height: 25rem; display: grid; align-content: center; gap: var(--space-24); padding: clamp(var(--space-24), 7vw, var(--space-72)); border: 1px solid var(--border); border-radius: var(--radius-dialog); background: var(--surface); box-shadow: var(--shadow-sm); }
    .card-stage:focus { outline: none; }
    .card-stage:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent), white 65%); outline-offset: 3px; }
    .card-side { display: grid; gap: var(--space-16); }
    .front-label, .meaning-label { color: var(--muted); font-family: var(--font-mono); font-size: .75rem; letter-spacing: .08em; text-transform: uppercase; }
    .study-lemma { margin: 0; font-family: var(--font-display); font-size: clamp(3rem, 10vw, 6rem); font-weight: 600; line-height: .98; letter-spacing: -.045em; overflow-wrap: anywhere; }
    .study-meta { margin: 0; color: var(--muted); font-family: var(--font-mono); font-size: .82rem; }
    .reveal-action { justify-self: start; }
    .answer-rule { border: 0; border-top: 1px solid var(--border); width: 100%; margin: var(--space-8) 0; }
    .meaning { margin: 0; font-size: 1.25rem; }
    .example { margin: 0; padding-left: var(--space-16); border-left: 3px solid var(--accent); font-size: 1.05rem; }
    .example-translation { display: block; margin-top: var(--space-4); color: var(--muted); font-size: .9rem; }
    .pronunciation-simple { display: grid; gap: var(--space-8); }
    .extra-info-row { display: flex; flex-wrap: wrap; gap: var(--space-12); align-items: center; }
    .always-extra-toggle { display: flex; flex-direction: row; align-items: center; gap: var(--space-8); font-size: .875rem; font-weight: 500; }
    .always-extra-toggle input { width: auto; }
    .extra-info { display: grid; gap: var(--space-16); border-top: 1px solid var(--border); padding-top: var(--space-16); }
    .detail-block { margin-top: 0; }
    .detail-block p, .detail-block ul { margin-bottom: 0; }
    .detail-block ul { padding-left: var(--space-24); }
    .confidence-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-8); }
    .confidence { min-height: 5rem; display: grid; align-content: center; justify-items: start; gap: var(--space-4); border-top: 4px solid var(--border); text-align: left; }
    .confidence:nth-child(1) { border-top-color: var(--danger); }
    .confidence:nth-child(2) { border-top-color: var(--warning); }
    .confidence:nth-child(3) { border-top-color: oklch(65% .1 95); }
    .confidence:nth-child(4) { border-top-color: oklch(62% .12 155); }
    .confidence:nth-child(5) { border-top-color: var(--accent); }
    .confidence-number { font-family: var(--font-mono); font-size: 1.1rem; }
    .confidence-text { font-size: .75rem; line-height: 1.15; }
    .study-state { min-height: 25rem; display: grid; place-content: center; text-align: center; }
    .study-state h2 { margin-bottom: var(--space-8); }
    .inline-status { margin: 0; color: var(--muted); }
    .inline-status.error { color: var(--danger); }
    .edit-meanings, .pronunciation { padding: var(--space-16); border: 1px solid var(--border); border-radius: var(--radius-panel); background: color-mix(in oklch, var(--bg), white 45%); }
    .edit-meanings h3, .pronunciation h3 { margin-bottom: var(--space-8); font-size: 1.25rem; }
    .gloss-row { display: grid; grid-template-columns: 1fr auto auto; gap: var(--space-8); align-items: end; margin-top: var(--space-12); }
    .audio-actions, .recording-actions { display: flex; flex-wrap: wrap; gap: var(--space-8); }
    .audio-preview { width: 100%; margin-top: var(--space-12); }
    .local-take { margin-top: var(--space-12); padding: var(--space-12); border: 1px dashed var(--accent); border-radius: var(--radius-control); }
    .bottom-nav { display: none; }
    @media (max-width: 800px) {
      .shell { padding: var(--space-24) var(--space-16) calc(var(--space-72) + var(--space-24)); }
      header, .form-row, .deck-heading { align-items: stretch; flex-direction: column; }
      header { align-items: flex-start; }
      header > .primary-nav { display: none; }
      .deck { grid-template-columns: 1fr; }
      .workflow-grid { grid-template-columns: 1fr; }
      .card-stage { min-height: 20rem; padding: var(--space-24); }
      .confidence-grid { grid-template-columns: 1fr; }
      .confidence { min-height: 3.6rem; grid-template-columns: 2rem 1fr; align-items: center; justify-items: start; }
      .confidence-text { font-size: .9rem; }
      .gloss-row { grid-template-columns: 1fr auto; }
      .gloss-row label { grid-column: 1 / -1; }
      .bottom-nav { position: fixed; z-index: 10; right: 0; bottom: 0; left: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 0; padding: var(--space-8) var(--space-16) calc(var(--space-8) + env(safe-area-inset-bottom)); border-top: 1px solid var(--border); background: color-mix(in oklch, var(--surface), white 12%); box-shadow: 0 -8px 24px oklch(20% .02 240 / 6%); }
      .bottom-nav button { min-height: 3rem; border: 0; background: transparent; }
    }
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
  @state() private exportingFormat: 'apkg' | 'tsv' | null = null;
  @state() private captureSentence = '';
  @state() private captureLessonLabel = '';
  @state() private captureSpanStart = 0;
  @state() private captureSpanEnd = 0;
  @state() private captureStatus: CaptureStatus = 'idle';
  @state() private captureCandidates: Candidate[] = [];
  @state() private captureAssetToken = '';
  @state() private captureContext: CaptureContext | null = null;
  @state() private captureSelections: Record<string, CaptureCandidateSelection> = {};
  @state() private captureMeaningLanguages: MeaningLanguage[] = ['de', 'en'];
  @state() private captureUserMeaningDe = '';
  @state() private captureUserMeaningEn = '';
  @state() private captureDeckId: number | null = null;
  @state() private captureError = '';
  @state() private captureDictionaryChanged = false;
  @state() private isCapturing = false;
  @state() private view: AppView = 'decks';
  @state() private studyDeckId: number | null = null;
  @state() private studyStatus: StudyStatus = 'idle';
  @state() private studyCard: NextCardData | null = null;
  @state() private isRevealed = false;
  @state() private isReviewing = false;
  @state() private studyError = '';
  @state() private extraInfoOpen = false;
  @state() private alwaysShowExtraInfo: boolean = readAlwaysShowExtraInfo(localStorageOrNull());
  @state() private glossDrafts: Record<MeaningLanguage, string> = { de: '', en: '' };
  @state() private glossState = '';
  @state() private glossError = '';
  @state() private glossSavingLanguage: MeaningLanguage | null = null;
  @state() private audioStatus: AudioStatus = 'idle';
  @state() private audioMessage = '';
  @state() private recordingStatus: RecordingStatus = 'idle';
  @state() private recordingBlob: Blob | null = null;
  @state() private recordingNoteId: number | null = null;
  @state() private recordingPreviewUrl = '';
  @state() private recordingError = '';
  @state() private showRecordingControls = false;
  @state() private revertConfirmation = false;
  @state() private hasCustomAudio = false;
  @state() private dictionaryMode: SessionMode = 'unconfigured';
  @state() private dictionarySettings: DictionarySettingsInfo | null = null;
  @state() private dictionarySettingsStatus: DictionarySettingsStatus = 'loading';
  @state() private dictionaryAction: DictionarySettingsAction = 'idle';
  @state() private dictionaryActionMessage = '';
  @state() private dictionaryActionError = '';
  @state() private confirmRemoveOffline = false;
  private focusTarget: 'answer' | 'empty' | null = null;
  private audioPlayer: HTMLAudioElement | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private recordingChunks: Blob[] = [];

  connectedCallback(): void {
    super.connectedCallback();
    void this.loadDecks();
    void this.loadDictionarySettings();
    window.addEventListener('keydown', this.handleStudyKeydown);
  }

  disconnectedCallback(): void {
    window.removeEventListener('keydown', this.handleStudyKeydown);
    this.stopAudio();
    this.releaseRecordingPreview();
    super.disconnectedCallback();
  }

  updated(): void {
    if (!this.focusTarget) return;
    const selector = this.focusTarget === 'answer' ? '[data-study-answer]' : '[data-study-empty]';
    const target = this.renderRoot.querySelector<HTMLElement>(selector);
    if (target) {
      target.focus();
      this.focusTarget = null;
    }
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
      if (this.captureDeckId !== null && !decks.some((deck) => deck.id === this.captureDeckId)) {
        this.captureDeckId = null;
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
      this.captureDeckId = refreshedDeck.id;
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

  private openDeck(deck: DeckSummary): void {
    this.selectedDeckId = deck.id;
    this.manualDeckId = deck.id;
    this.captureDeckId = deck.id;
    this.importDeckName = deck.name;
    this.view = 'deck';
    this.successMessage = '';
  }

  private async openStudy(deckId?: number): Promise<void> {
    if (this.recordingBlob || this.recordingStatus === 'recording') {
      this.view = 'study';
      this.errorMessage = 'Save or discard the local recording before changing study sessions.';
      return;
    }
    this.view = 'study';
    this.studyDeckId = deckId ?? null;
    this.studyCard = null;
    this.isRevealed = false;
    this.extraInfoOpen = extraInfoOpenOnCardLoad();
    this.studyError = '';
    this.clearPronunciationState();
    await this.loadStudyCard();
  }

  private clearPronunciationState(): void {
    this.stopAudio();
    this.audioMessage = '';
    this.audioStatus = 'idle';
    this.showRecordingControls = false;
    this.revertConfirmation = false;
  }

  private async loadStudyCard(): Promise<void> {
    this.studyStatus = 'loading';
    this.studyError = '';
    try {
      const response = await vocabClient.getNextCard(this.studyDeckId ?? undefined);
      this.studyCard = response.card;
      this.isRevealed = false;
      this.extraInfoOpen = extraInfoOpenOnCardLoad();
      this.hasCustomAudio = Boolean(response.card?.front.audio_trigger.token?.startsWith('custom:'));
      this.glossDrafts = { de: this.userGlossValue(response.card, 'de'), en: this.userGlossValue(response.card, 'en') };
      this.glossState = '';
      this.glossError = '';
      this.studyStatus = response.card ? 'ready' : 'empty';
      if (!response.card) this.focusTarget = 'empty';
    } catch (error) {
      this.studyCard = null;
      this.studyStatus = 'error';
      this.studyError = this.messageFor(error, 'The next card could not be loaded.');
    }
  }

  private revealCard(): void {
    if (!this.studyCard || this.isRevealed || this.isReviewing) return;
    this.isRevealed = true;
    this.extraInfoOpen = extraInfoOpenOnReveal(this.alwaysShowExtraInfo);
    this.focusTarget = 'answer';
  }

  private toggleExtraInfo(): void {
    this.extraInfoOpen = !this.extraInfoOpen;
  }

  private setAlwaysShowExtraInfo(checked: boolean): void {
    this.alwaysShowExtraInfo = checked;
    writeAlwaysShowExtraInfo(localStorageOrNull(), checked);
    this.extraInfoOpen = extraInfoOpenOnPreferenceChange({
      isRevealed: this.isRevealed,
      newPreference: checked,
    });
  }

  private async submitConfidence(confidence: number): Promise<void> {
    const card = this.studyCard;
    if (!card || !this.isRevealed || this.isReviewing) return;
    if (this.recordingBlob) {
      this.studyError = 'Save or discard the local recording before continuing to the next card.';
      return;
    }
    this.isReviewing = true;
    this.studyError = '';
    try {
      await vocabClient.reviewCard(card.card_id, confidence);
      await this.loadStudyCard();
    } catch (error) {
      this.studyError = this.messageFor(error, 'Your confidence could not be saved. Try the same rating again.');
    } finally {
      this.isReviewing = false;
    }
  }

  private readonly handleStudyKeydown = (event: KeyboardEvent): void => {
    if (this.view !== 'study') return;
    const target = event.target as HTMLElement | null;
    if (target?.closest('input, textarea, select, [contenteditable="true"]')) return;
    if (event.code === 'Space' && !this.isRevealed) {
      event.preventDefault();
      this.revealCard();
      return;
    }
    if (event.key >= '1' && event.key <= '5' && this.isRevealed) {
      event.preventDefault();
      void this.submitConfidence(Number(event.key));
      return;
    }
    if (event.key.toLowerCase() === 'r') {
      event.preventDefault();
      void this.playPronunciation();
    }
  };

  private meaningFor(card: NextCardData | null, language: MeaningLanguage): RenderedMeaning | undefined {
    return card?.back.meanings.find((meaning) => meaning.language === language);
  }

  private userGlossValue(card: NextCardData | null, language: MeaningLanguage): string {
    const meaning = this.meaningFor(card, language);
    return meaning?.is_user_authored ? meaning.lines.join(' ') : '';
  }

  private async saveGloss(language: MeaningLanguage): Promise<void> {
    const card = this.studyCard;
    const meaningText = this.glossDrafts[language].trim();
    if (!card || !meaningText) return;
    this.glossSavingLanguage = language;
    this.glossError = '';
    this.glossState = '';
    try {
      const result = await vocabClient.setGloss(card.note_id, language, meaningText);
      this.glossDrafts = { ...this.glossDrafts, [language]: result.meaning_text };
      this.glossState = `${language === 'de' ? 'German' : 'English'} meaning saved.`;
      await this.refreshStudyFace(card.card_id);
    } catch (error) {
      this.glossError = this.messageFor(error, 'That meaning could not be saved.');
    } finally {
      this.glossSavingLanguage = null;
    }
  }

  private async deleteGloss(language: MeaningLanguage): Promise<void> {
    const card = this.studyCard;
    if (!card) return;
    this.glossSavingLanguage = language;
    this.glossError = '';
    this.glossState = '';
    try {
      const result = await vocabClient.deleteGloss(card.note_id, language);
      if (!result.deleted) throw new Error('The server did not confirm removal.');
      this.glossDrafts = { ...this.glossDrafts, [language]: '' };
      this.glossState = `${language === 'de' ? 'German' : 'English'} meaning removed.`;
      await this.refreshStudyFace(card.card_id);
    } catch (error) {
      this.glossError = this.messageFor(error, 'That meaning could not be removed.');
    } finally {
      this.glossSavingLanguage = null;
    }
  }

  private async refreshStudyFace(cardId: number): Promise<void> {
    try {
      const response = await vocabClient.getNextCard(this.studyDeckId ?? undefined);
      if (response.card?.card_id === cardId) {
        this.studyCard = response.card;
        this.hasCustomAudio = Boolean(response.card.front.audio_trigger.token?.startsWith('custom:'));
      }
    } catch {
      // The mutation result is already server-confirmed; leave the visible face usable.
    }
  }

  private audioRequestId(card: NextCardData): string | number {
    return this.hasCustomAudio ? card.note_id : card.front.audio_trigger.lemma;
  }

  private stopAudio(): void {
    if (this.audioPlayer) {
      this.audioPlayer.pause();
      this.audioPlayer.src = '';
      this.audioPlayer = null;
    }
    if (this.audioStatus === 'playing') this.audioStatus = 'idle';
  }

  private async playPronunciation(): Promise<void> {
    const card = this.studyCard;
    if (!card || !card.front.audio_trigger.available || this.audioStatus === 'loading') return;
    this.stopAudio();
    this.audioStatus = 'loading';
    this.audioMessage = 'Loading pronunciation…';
    try {
      const blob = await vocabClient.fetchAudio(this.audioRequestId(card));
      const url = URL.createObjectURL(blob);
      const player = new Audio(url);
      this.audioPlayer = player;
      player.onended = () => { URL.revokeObjectURL(url); this.audioPlayer = null; this.audioStatus = 'idle'; this.audioMessage = ''; };
      await player.play();
      this.audioStatus = 'playing';
      this.audioMessage = 'Playing pronunciation…';
    } catch (error) {
      this.audioStatus = 'unavailable';
      this.audioMessage = this.messageFor(error, 'Pronunciation is unavailable right now.');
    }
  }

  private releaseRecordingPreview(): void {
    if (this.recordingPreviewUrl) URL.revokeObjectURL(this.recordingPreviewUrl);
    this.recordingPreviewUrl = '';
  }

  private setLocalRecording(blob: Blob): void {
    this.releaseRecordingPreview();
    this.recordingBlob = blob;
    this.recordingNoteId = this.studyCard?.note_id ?? null;
    this.recordingPreviewUrl = URL.createObjectURL(blob);
    this.recordingStatus = 'ready';
    this.recordingError = '';
  }

  private async startRecording(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      this.recordingError = 'Recording is not available in this browser. You can choose an audio file instead.';
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      this.recordingChunks = [];
      recorder.ondataavailable = (event) => { if (event.data.size) this.recordingChunks.push(event.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        this.setLocalRecording(new Blob(this.recordingChunks, { type: recorder.mimeType || 'audio/webm' }));
      };
      recorder.start();
      this.mediaRecorder = recorder;
      this.recordingStatus = 'recording';
      this.recordingError = '';
    } catch (error) {
      this.recordingError = this.messageFor(error, 'Microphone access was not granted. You can choose an audio file instead.');
    }
  }

  private stopRecording(): void {
    if (this.mediaRecorder?.state === 'recording') this.mediaRecorder.stop();
    this.mediaRecorder = null;
  }

  private selectAudioFile(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) this.setLocalRecording(file);
  }

  private discardRecording(): void {
    this.releaseRecordingPreview();
    this.recordingBlob = null;
    this.recordingNoteId = null;
    this.recordingStatus = 'idle';
    this.recordingError = '';
  }

  private async saveRecording(): Promise<void> {
    const card = this.studyCard;
    const recording = this.recordingBlob;
    if (!card || !recording || this.recordingNoteId !== card.note_id) return;
    this.recordingStatus = 'saving';
    this.recordingError = '';
    try {
      await vocabClient.uploadAudio(card.note_id, recording, recording.type || 'audio/webm');
      this.discardRecording();
      this.showRecordingControls = false;
      this.hasCustomAudio = true;
      this.audioMessage = 'Custom pronunciation saved.';
      await this.refreshStudyFace(card.card_id);
    } catch (error) {
      this.recordingStatus = 'save-error';
      this.recordingError = this.messageFor(error, 'The recording was not saved. Your local take is still available.');
    }
  }

  private async revertCustomAudio(): Promise<void> {
    const card = this.studyCard;
    if (!card) return;
    this.audioMessage = '';
    try {
      const result = await vocabClient.revertAudio(card.note_id);
      if (!result.reverted) throw new Error('The server did not confirm the change.');
      this.hasCustomAudio = false;
      this.revertConfirmation = false;
      this.audioMessage = 'Automatic pronunciation restored.';
      await this.refreshStudyFace(card.card_id);
    } catch (error) {
      this.audioMessage = this.messageFor(error, 'Automatic pronunciation could not be restored.');
    }
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
      const candidates = result.candidates.map((candidate) => ({
        ...candidate,
        status: candidate.status ?? (candidate.senses?.length ? 'resolved' : 'needs_gloss'),
        senses: candidate.senses?.map((sense) => ({
          ...sense,
          gloss: sense.gloss ?? sense.meanings?.[0]?.text ?? '',
        })),
      }));
      this.lookupCandidates = candidates;
      this.lookupAssetToken = result.asset_token;
      this.lookupStatus = 'ready';
      const soleCandidate = candidates.length === 1 ? candidates[0] : undefined;
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

  private captureKey(candidate: Candidate): string {
    return `${candidate.lemma_semantic_ref}:${candidate.status}`;
  }

  private updateCaptureSpan(event: Event): void {
    const input = event.target as HTMLTextAreaElement;
    this.captureSpanStart = input.selectionStart ?? 0;
    this.captureSpanEnd = input.selectionEnd ?? 0;
  }

  private resetCapturePicker(): void {
    this.captureCandidates = [];
    this.captureAssetToken = '';
    this.captureContext = null;
    this.captureSelections = {};
    this.captureDictionaryChanged = false;
  }

  private async highlightCapture(event?: Event): Promise<void> {
    event?.preventDefault();
    const sentenceText = this.captureSentence;
    const lessonLabel = this.captureLessonLabel.trim();
    const selectedSpan = { start: this.captureSpanStart, end: this.captureSpanEnd };
    if (!sentenceText.trim()) {
      this.captureStatus = 'error';
      this.captureError = 'Enter the sentence you want this card to remember.';
      return;
    }
    if (selectedSpan.start === selectedSpan.end) {
      this.captureStatus = 'error';
      this.captureError = 'Select the German word or phrase in the sentence before finding candidates.';
      return;
    }
    if (!lessonLabel) {
      this.captureStatus = 'error';
      this.captureError = 'Add a lesson label so this capture keeps its provenance.';
      return;
    }

    this.captureStatus = 'loading';
    this.captureError = '';
    this.resetCapturePicker();
    try {
      const result = await vocabClient.highlight({
        sentence_text: sentenceText,
        selected_span: selectedSpan,
        lesson_label: lessonLabel,
      });
      this.captureCandidates = result.candidates;
      this.captureAssetToken = result.asset_token;
      this.captureContext = result.capture_context;
      this.captureStatus = 'ready';
      const soleCandidate = result.candidates.length === 1 ? result.candidates[0] : undefined;
      if (soleCandidate) this.toggleCaptureCandidate(soleCandidate, true);
    } catch (error) {
      this.captureStatus = 'error';
      this.captureError = this.messageFor(error, 'Candidates could not be found.');
    }
  }

  private toggleCaptureCandidate(candidate: Candidate, checked: boolean): void {
    const key = this.captureKey(candidate);
    const selections = { ...this.captureSelections };
    if (checked) {
      selections[key] = {
        candidate,
        senseRef: candidate.status === 'resolved' ? candidate.senses?.[0]?.sense_semantic_ref ?? null : null,
      };
    } else {
      delete selections[key];
    }
    this.captureSelections = selections;
  }

  private setCaptureSense(candidate: Candidate, senseRef: string): void {
    const key = this.captureKey(candidate);
    const current = this.captureSelections[key];
    if (!current) return;
    this.captureSelections = { ...this.captureSelections, [key]: { ...current, senseRef } };
  }

  private toggleCaptureMeaningLanguage(language: MeaningLanguage): void {
    const selected = this.captureMeaningLanguages;
    if (selected.includes(language)) {
      if (selected.length === 1) return;
      this.captureMeaningLanguages = selected.filter((item) => item !== language);
      return;
    }
    this.captureMeaningLanguages = [...selected, language];
  }

  private captureUserMeanings(): Record<string, string> | undefined {
    const meanings: Record<string, string> = {};
    if (this.captureUserMeaningDe.trim()) meanings.de = this.captureUserMeaningDe.trim();
    if (this.captureUserMeaningEn.trim()) meanings.en = this.captureUserMeaningEn.trim();
    return Object.keys(meanings).length ? meanings : undefined;
  }

  private async saveCapture(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const deck = this.decks.find((item) => item.id === this.captureDeckId);
    const selections = Object.values(this.captureSelections);
    if (!selections.length) return;
    if (!deck) {
      this.captureError = 'Choose a destination deck before creating cards.';
      return;
    }
    if (!this.captureContext || !this.captureAssetToken) {
      this.captureError = 'Find candidates again before creating cards.';
      return;
    }
    const incomplete = selections.some(({ candidate, senseRef }) => candidate.status === 'resolved' && !senseRef);
    if (incomplete) {
      this.captureError = 'Choose a dictionary meaning for every selected candidate.';
      return;
    }

    this.isCapturing = true;
    this.captureError = '';
    this.captureDictionaryChanged = false;
    this.successMessage = '';
    try {
      const result = await vocabClient.captureCards({
        asset_token: this.captureAssetToken,
        deck: { name: deck.name, lesson_label: this.captureContext.lesson_label },
        capture_context: this.captureContext,
        selections: selections.map(({ candidate, senseRef }) => ({
          lemma_semantic_ref: candidate.lemma_semantic_ref,
          sense_semantic_ref: senseRef,
          status: candidate.status,
          component_refs: candidate.component_refs,
          overrides: {
            meaning_langs: this.captureMeaningLanguages,
            user_meanings: this.captureUserMeanings(),
          },
        })),
      });
      const refreshedDecks = await this.loadDecks();
      const selectedDeck = refreshedDecks?.find((item) => item.id === result.deck_id);
      if (!selectedDeck || selectedDeck.id !== deck.id) {
        this.captureError = 'The server did not confirm the selected destination deck. Cards were not reported as created.';
        return;
      }
      const created = result.notes.filter((note) => note.created).length;
      const reused = result.notes.length - created;
      this.selectedDeckId = selectedDeck.id;
      this.manualDeckId = selectedDeck.id;
      this.captureDeckId = selectedDeck.id;
      this.successMessage = `Server confirmed ${created} ${created === 1 ? 'card' : 'cards'} created and ${reused} ${reused === 1 ? 'card' : 'cards'} reused in “${selectedDeck.name}”.`;
      this.captureStatus = 'idle';
      this.captureSentence = '';
      this.captureLessonLabel = '';
      this.captureSpanStart = 0;
      this.captureSpanEnd = 0;
      this.captureUserMeaningDe = '';
      this.captureUserMeaningEn = '';
      this.resetCapturePicker();
    } catch (error) {
      if (error instanceof ApiError && error.isConflict) {
        this.captureDictionaryChanged = true;
        this.captureError = '';
      } else {
        this.captureError = this.messageFor(error, 'Cards could not be created.');
      }
    } finally {
      this.isCapturing = false;
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
    this.exportingFormat = 'tsv';
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
      this.exportingFormat = null;
    }
  }

  private async exportApkg(deck: DeckSummary): Promise<void> {
    this.exportingFormat = 'apkg';
    this.errorMessage = '';
    this.successMessage = '';
    try {
      const apkg = await vocabClient.exportApkg(deck.id);
      const url = URL.createObjectURL(apkg);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${deck.name.replace(/[^a-z0-9._-]+/gi, '-') || 'flashcards'}.apkg`;
      link.click();
      URL.revokeObjectURL(url);
      this.successMessage = `Prepared an APKG export for “${deck.name}”.`;
    } catch (error) {
      this.errorMessage = this.messageFor(error, 'APKG export could not be prepared.');
    } finally {
      this.exportingFormat = null;
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
            <button class="deck-open" @click=${() => this.openDeck(deck)} aria-label=${`Open ${deck.name}`}>
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

  private renderCaptureCreation(deck: DeckSummary) {
    const selectedCount = Object.keys(this.captureSelections).length;
    const captureDeck = this.decks.find((item) => item.id === this.captureDeckId);
    const selectedText = this.captureSentence.slice(this.captureSpanStart, this.captureSpanEnd);
    return html`
      <section class="workflow capture-workflow" aria-labelledby="capture-title">
        <h3 id="capture-title">Capture from a sentence</h3>
        <p class="muted">Paste or type a sentence, select its German word or phrase, then choose the cards to create.</p>
        <form @submit=${this.highlightCapture}>
          <label>Sentence text
            <textarea
              .value=${this.captureSentence}
              @input=${(event: InputEvent) => { this.captureSentence = (event.target as HTMLTextAreaElement).value; this.updateCaptureSpan(event); this.resetCapturePicker(); this.captureStatus = 'idle'; this.captureError = ''; }}
              @select=${this.updateCaptureSpan}
              @keyup=${this.updateCaptureSpan}
              @click=${this.updateCaptureSpan}
              ?disabled=${this.captureStatus === 'loading' || this.isCapturing}
              placeholder="Ich rufe dich morgen an."
            ></textarea>
          </label>
          <p class="selection-preview" aria-live="polite">${selectedText ? html`Selected: <strong>“${selectedText}”</strong>` : 'Select a German word or phrase in the sentence.'}</p>
          <label>Lesson label
            <input
              .value=${this.captureLessonLabel}
              @input=${(event: InputEvent) => { this.captureLessonLabel = (event.target as HTMLInputElement).value; this.resetCapturePicker(); this.captureStatus = 'idle'; this.captureError = ''; }}
              ?disabled=${this.captureStatus === 'loading' || this.isCapturing}
              autocomplete="off"
              placeholder="Lesson 4 · Telephone calls"
            />
          </label>
          <div class="actions">
            <button class="primary" type="submit" ?disabled=${this.captureStatus === 'loading' || this.isCapturing}>${this.captureStatus === 'loading' ? 'Finding candidates…' : 'Find candidates'}</button>
          </div>
        </form>
        ${this.captureStatus === 'loading' ? html`<p class="result" role="status">Checking the active dictionary…</p>` : nothing}
        ${this.captureStatus === 'error' ? html`<div class="capture-state error" role="alert"><p>${this.captureError}</p><button @click=${() => void this.highlightCapture()}>Try again</button></div>` : nothing}
        ${this.captureStatus === 'ready' && this.captureCandidates.length === 0 ? html`<div class="capture-state"><p>No dictionary candidates were found for “${selectedText}”. Adjust the selected text and try again.</p></div>` : nothing}
        ${this.captureCandidates.length ? html`
          <form class="capture-picker" @submit=${this.saveCapture}>
            <fieldset class="selection">
              <legend>Choose vocabulary <span class="muted">(select one or more)</span></legend>
              <p class="result">Each checked German candidate becomes its own card. You can select multiple candidates.</p>
              <ul class="candidate-list">
                ${this.captureCandidates.map((candidate) => {
                  const key = this.captureKey(candidate);
                  const selection = this.captureSelections[key];
                  return html`
                    <li class="capture-candidate ${selection ? 'chosen' : ''}">
                      <label class="candidate-choice">
                        <input
                          type="checkbox"
                          .checked=${Boolean(selection)}
                          @change=${(event: Event) => this.toggleCaptureCandidate(candidate, (event.target as HTMLInputElement).checked)}
                          ?disabled=${this.isCapturing}
                        />
                        <span><strong class="lemma">${candidate.lemma}</strong> <span class="caption">${candidate.pos}</span></span>
                      </label>
                      ${selection && candidate.status === 'resolved' ? (candidate.senses?.length ? html`
                        <fieldset class="sense-choices">
                          <legend>Dictionary meaning for ${candidate.lemma}</legend>
                          ${candidate.senses.map((sense) => html`
                            <label class="choice">
                              <input type="radio" name=${`capture-sense-${key}`} .value=${sense.sense_semantic_ref} .checked=${selection.senseRef === sense.sense_semantic_ref} @change=${() => this.setCaptureSense(candidate, sense.sense_semantic_ref)} ?disabled=${this.isCapturing} />
                              ${sense.gloss || `Meaning ${sense.ord}`}
                            </label>
                          `)}
                        </fieldset>
                      ` : html`<p class="result">This entry has no selectable dictionary meaning.</p>`) : nothing}
                      ${selection && candidate.status === 'derived_compound' ? html`<p class="result">The server will preserve the compound’s dictionary component bindings.</p>` : nothing}
                    </li>
                  `;
                })}
              </ul>
            </fieldset>
            ${this.captureDictionaryChanged ? html`
              <div class="capture-state warning" role="alert">
                <p>The dictionary changed while you were choosing cards. Your selections have not been saved.</p>
                <button type="button" @click=${() => void this.highlightCapture()}>Find fresh candidates</button>
              </div>
            ` : nothing}
            ${this.captureError ? html`<div class="capture-state error" role="alert"><p>${this.captureError}</p></div>` : nothing}
            <fieldset class="selection language-chips">
              <legend>Meaning languages</legend>
              <p class="result">Choose German, English, or both. At least one language stays selected.</p>
              ${(['de', 'en'] as MeaningLanguage[]).map((language) => html`
                <button
                  class="chip ${this.captureMeaningLanguages.includes(language) ? 'selected' : ''}"
                  type="button"
                  aria-pressed=${this.captureMeaningLanguages.includes(language) ? 'true' : 'false'}
                  @click=${() => this.toggleCaptureMeaningLanguage(language)}
                  ?disabled=${this.isCapturing || (this.captureMeaningLanguages.length === 1 && this.captureMeaningLanguages.includes(language))}
                >${language === 'de' ? 'German · DE' : 'English · EN'}</button>
              `)}
            </fieldset>
            ${this.captureMeaningLanguages.includes('de') ? html`<label>Your German meaning <span class="muted">(optional)</span><input .value=${this.captureUserMeaningDe} @input=${(event: InputEvent) => { this.captureUserMeaningDe = (event.target as HTMLInputElement).value; }} ?disabled=${this.isCapturing} autocomplete="off" /></label>` : nothing}
            ${this.captureMeaningLanguages.includes('en') ? html`<label>Your English meaning <span class="muted">(optional)</span><input .value=${this.captureUserMeaningEn} @input=${(event: InputEvent) => { this.captureUserMeaningEn = (event.target as HTMLInputElement).value; }} ?disabled=${this.isCapturing} autocomplete="off" /></label>` : nothing}
            <label>Destination deck
              <select .value=${captureDeck ? String(captureDeck.id) : String(deck.id)} @change=${(event: Event) => { const value = (event.target as HTMLSelectElement).value; this.captureDeckId = value ? Number(value) : null; }} ?disabled=${this.isCapturing}>
                <option value="">Select a deck</option>
                ${this.decks.map((item) => html`<option value=${item.id}>${item.name}</option>`)}
              </select>
            </label>
            <div class="actions create-actions">
              <button class="primary" type="submit" ?disabled=${selectedCount === 0 || this.isCapturing || this.captureDictionaryChanged}>${this.isCapturing ? 'Creating cards…' : `Create ${selectedCount || ''} card${selectedCount === 1 ? '' : 's'}`}</button>
              ${selectedCount === 0 ? html`<p class="disabled-explanation">Select at least one candidate to create cards.</p>` : nothing}
            </div>
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
            <h3>APKG export</h3>
            <p class="muted">Download the selected deck as a ready-to-import Anki package.</p>
            <button class="primary" @click=${() => void this.exportApkg(deck)} ?disabled=${this.exportingFormat !== null}>${this.exportingFormat === 'apkg' ? 'Preparing APKG…' : `Export “${deck.name}” APKG`}</button>
          </div>
          <div>
            <h3>TSV export</h3>
            <p class="muted">Secondary export for the available Anki TSV format.</p>
            <button @click=${() => void this.exportTsv(deck)} ?disabled=${this.exportingFormat !== null}>${this.exportingFormat === 'tsv' ? 'Preparing TSV…' : `Export “${deck.name}” TSV`}</button>
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
        </div>
      </section>
    `;
  }

  /**
   * The simple "Play pronunciation" control. Always visible on the revealed
   * answer, outside Extra info — recording and custom-pronunciation
   * management live in {@link renderPronunciationManagement} instead.
   */
  private renderSimplePronunciation() {
    return html`
      <div class="pronunciation-simple">
        <div class="audio-actions">
          <button type="button" @click=${() => void this.playPronunciation()} ?disabled=${this.audioStatus === 'loading'}>
            ${this.audioStatus === 'loading' ? 'Loading pronunciation…' : this.audioStatus === 'playing' ? 'Playing pronunciation…' : 'Play pronunciation'}
          </button>
          <span class="caption">Press R to replay</span>
        </div>
        ${this.audioMessage ? html`<p class="inline-status ${this.audioStatus === 'unavailable' ? 'error' : ''}" role=${this.audioStatus === 'unavailable' ? 'alert' : 'status'}>${this.audioMessage}</p>` : nothing}
      </div>
    `;
  }

  /**
   * Recording and custom-pronunciation management. Secondary to ordinary
   * review, so it lives inside Extra info rather than on the default
   * revealed answer.
   */
  private renderPronunciationManagement() {
    const recordingFailed = this.recordingStatus === 'save-error';
    return html`
      <section class="pronunciation" aria-labelledby="pronunciation-title">
        <h3 id="pronunciation-title">Custom pronunciation</h3>
        ${this.hasCustomAudio ? html`
          <div class="audio-actions">
            <button type="button" @click=${() => { this.showRecordingControls = !this.showRecordingControls; this.revertConfirmation = false; }}>
              ${this.showRecordingControls ? 'Keep current pronunciation' : 'Replace pronunciation'}
            </button>
            ${this.revertConfirmation ? html`
              <span class="caption">Replace your custom pronunciation with automatic pronunciation?</span>
              <button class="danger" type="button" @click=${() => void this.revertCustomAudio()}>Confirm revert to automatic</button>
              <button type="button" @click=${() => { this.revertConfirmation = false; }}>Cancel</button>
            ` : html`<button class="danger" type="button" @click=${() => { this.revertConfirmation = true; this.showRecordingControls = false; }}>Revert to automatic</button>`}
          </div>
        ` : html`<button type="button" @click=${() => { this.showRecordingControls = !this.showRecordingControls; }}>Add your pronunciation</button>`}
        ${this.showRecordingControls ? html`
          <div class="local-take">
            <p class="muted">Record a take or choose an audio file. It stays only in this browser until you save it.</p>
            ${this.recordingBlob ? html`
              <p class="inline-status">Local recording ready to preview and save.</p>
              <audio class="audio-preview" controls src=${this.recordingPreviewUrl}></audio>
            ` : nothing}
            ${recordingFailed ? html`
              <p class="inline-status error" role="alert">${this.recordingError}</p>
              <div class="recording-actions">
                <button class="primary" type="button" @click=${() => void this.saveRecording()}>Try again</button>
                <button class="danger" type="button" @click=${this.discardRecording}>Discard recording</button>
              </div>
            ` : html`
              <div class="recording-actions">
                ${this.recordingStatus === 'recording'
                  ? html`<button class="danger" type="button" @click=${this.stopRecording}>Stop recording</button>`
                  : html`<button type="button" @click=${() => void this.startRecording()} ?disabled=${this.recordingStatus === 'saving'}>Record pronunciation</button>`}
                <label>Choose audio file
                  <input type="file" accept="audio/*" @change=${this.selectAudioFile} ?disabled=${this.recordingStatus === 'recording' || this.recordingStatus === 'saving'} />
                </label>
                ${this.recordingBlob ? html`
                  <button class="primary" type="button" @click=${() => void this.saveRecording()} ?disabled=${this.recordingStatus === 'saving'}>${this.recordingStatus === 'saving' ? 'Saving pronunciation…' : 'Save recording'}</button>
                  <button class="danger" type="button" @click=${this.discardRecording} ?disabled=${this.recordingStatus === 'saving'}>Discard recording</button>
                ` : nothing}
              </div>
              ${this.recordingError ? html`<p class="inline-status error" role="alert">${this.recordingError}</p>` : nothing}
            `}
          </div>
        ` : nothing}
      </section>
    `;
  }

  private renderMeaningEditor(card: NextCardData) {
    return html`
      <section class="edit-meanings" aria-labelledby="meaning-edit-title">
        <h3 id="meaning-edit-title">Your meanings</h3>
        <p class="muted">Save your wording for either language, or remove an existing personal meaning to return to the card’s available meaning.</p>
        ${(['de', 'en'] as MeaningLanguage[]).map((language) => {
          const meaning = this.meaningFor(card, language);
          const userAuthored = Boolean(meaning?.is_user_authored);
          const languageName = language === 'de' ? 'German' : 'English';
          return html`
            <div class="gloss-row">
              <label>Your ${languageName} meaning
                <input
                  .value=${this.glossDrafts[language]}
                  @input=${(event: InputEvent) => { this.glossDrafts = { ...this.glossDrafts, [language]: (event.target as HTMLInputElement).value }; }}
                  ?disabled=${this.glossSavingLanguage === language}
                  autocomplete="off"
                />
              </label>
              <button type="button" @click=${() => void this.saveGloss(language)} ?disabled=${this.glossSavingLanguage === language || !this.glossDrafts[language].trim()}>
                ${this.glossSavingLanguage === language ? 'Saving…' : 'Save'}
              </button>
              ${userAuthored ? html`<button class="danger" type="button" @click=${() => void this.deleteGloss(language)} ?disabled=${this.glossSavingLanguage === language}>Remove</button>` : nothing}
            </div>
          `;
        })}
        ${this.glossState ? html`<p class="inline-status" role="status">${this.glossState}</p>` : nothing}
        ${this.glossError ? html`<p class="inline-status error" role="alert">${this.glossError}</p>` : nothing}
      </section>
    `;
  }

  private renderStudyCard(card: NextCardData) {
    const deMeaning = this.meaningFor(card, 'de');
    const enMeaning = this.meaningFor(card, 'en');
    const primaryExample = card.back.examples[0];
    const otherExamples = card.back.examples.slice(1);
    const extraMeaningLines = card.back.meanings.flatMap((meaning) => meaning.lines.slice(1).map((line) => `${meaning.heading}: ${line}`));
    return html`
      <div class="card-stage">
        <div class="card-side">
          <span class="front-label">German vocabulary</span>
          <h2 class="study-lemma">${card.front.display_headword}</h2>
          <p class="study-meta">${card.front.pos}${card.front.ipa ? ` · ${card.front.ipa}` : ''}</p>
          ${!this.isRevealed ? html`
            <button class="primary reveal-action" type="button" @click=${this.revealCard}>Reveal answer <span class="caption">Space</span></button>
          ` : html`
            <div class="card-side" data-study-answer tabindex="-1">
              <hr class="answer-rule" />
              <span class="front-label">Answer</span>
              <p class="meaning"><span class="meaning-label">German</span><br />${deMeaning?.lines[0] ?? 'No German learner meaning is available.'}</p>
              ${enMeaning ? html`<p class="meaning"><span class="meaning-label">English</span><br />${enMeaning.lines[0] ?? ''}</p>` : nothing}
              ${primaryExample ? html`<p class="example">${primaryExample.de}${primaryExample.en ? html`<span class="example-translation">${primaryExample.en}</span>` : nothing}</p>` : nothing}
              ${this.renderSimplePronunciation()}
              <div class="extra-info-row">
                <button
                  type="button"
                  aria-expanded=${this.extraInfoOpen ? 'true' : 'false'}
                  aria-controls="extra-info-panel"
                  @click=${this.toggleExtraInfo}
                >${this.extraInfoOpen ? 'Hide extra info' : 'Show extra info'}</button>
                <label class="always-extra-toggle">
                  <input
                    type="checkbox"
                    .checked=${this.alwaysShowExtraInfo}
                    @change=${(event: Event) => this.setAlwaysShowExtraInfo((event.target as HTMLInputElement).checked)}
                  />
                  Always show extra info
                </label>
              </div>
              ${this.extraInfoOpen ? html`
                <div class="extra-info" id="extra-info-panel">
                  <div class="detail-block"><span class="meaning-label">Grammar</span><p>${card.back.grammar.lines.join(' · ') || card.back.pos}</p></div>
                  ${extraMeaningLines.length ? html`<div class="detail-block"><span class="meaning-label">Extended notes</span><ul>${extraMeaningLines.map((line) => html`<li>${line}</li>`)}</ul></div>` : nothing}
                  ${otherExamples.length ? html`<div class="detail-block"><span class="meaning-label">Additional examples</span>${otherExamples.map((example) => html`<p class="example">${example.de}${example.en ? html`<span class="example-translation">${example.en}</span>` : nothing}</p>`)}</div>` : nothing}
                  ${this.renderPronunciationManagement()}
                  ${this.renderMeaningEditor(card)}
                </div>
              ` : nothing}
              <div>
                <p class="front-label">How well did you know it?</p>
                <div class="confidence-grid">
                  ${confidenceLabels.map(([number, label]) => html`
                    <button class="confidence" type="button" ?disabled=${this.isReviewing || Boolean(this.recordingBlob)} @click=${() => void this.submitConfidence(Number(number))}>
                      <span class="confidence-number">${number}</span><span class="confidence-text">${label}</span>
                    </button>
                  `)}
                </div>
              </div>
              ${this.isReviewing ? html`<p class="inline-status" role="status">Saving your confidence…</p>` : nothing}
              ${this.recordingBlob ? html`<p class="inline-status">Save or discard the local recording before choosing a confidence.</p>` : nothing}
            </div>
          `}
        </div>
      </div>
    `;
  }

  private renderStudy() {
    const deck = this.decks.find((item) => item.id === this.studyDeckId);
    return html`
      <main class="study" aria-labelledby="study-title">
        <div class="study-heading">
          <div><p class="caption">Study</p><h2 id="study-title">${deck ? deck.name : 'All due cards'}</h2></div>
          <button type="button" @click=${() => void this.loadStudyCard()} ?disabled=${this.studyStatus === 'loading'}>${this.studyStatus === 'loading' ? 'Loading…' : 'Refresh'}</button>
        </div>
        ${this.studyStatus === 'ready' && this.studyError ? html`<p class="inline-status error" role="alert">${this.studyError}</p>` : nothing}
        ${this.studyStatus === 'loading' ? html`<div class="card-stage study-state" role="status">Loading the next due card…</div>` : nothing}
        ${this.studyStatus === 'error' ? html`<div class="card-stage study-state"><div><h2>Could not load a card</h2><p class="inline-status error" role="alert">${this.studyError}</p><button class="primary" type="button" @click=${() => void this.loadStudyCard()}>Try again</button></div></div>` : nothing}
        ${this.studyStatus === 'empty' ? html`<div class="card-stage study-state" data-study-empty tabindex="-1"><div><h2>Nothing due right now</h2><p class="muted">Your next due card will appear here when the server has one ready.</p><button type="button" @click=${() => void this.loadStudyCard()}>Check again</button></div></div>` : nothing}
        ${this.studyStatus === 'ready' && this.studyCard ? this.renderStudyCard(this.studyCard) : nothing}
      </main>
    `;
  }

  private async loadDictionarySettings(): Promise<void> {
    this.dictionarySettingsStatus = 'loading';
    this.dictionaryActionError = '';
    try {
      const info = await vocabClient.getDictionarySettings();
      this.dictionarySettings = info;
      this.dictionaryMode = info.mode;
      this.dictionarySettingsStatus = 'ready';
      // The chooser is the runtime's unconfigured view; UI surfaces it
      // when the server says so, and only then.
      if (info.mode === 'unconfigured' && this.view !== 'study' && this.view !== 'chooser') {
        // Stay on decks unless the user was already in settings; the
        // chooser banner is rendered inside renderSettings so it's
        // reachable from anywhere.
      }
    } catch (error) {
      this.dictionarySettingsStatus = 'error';
      this.dictionaryActionError = this.messageFor(
        error,
        'Could not read the dictionary settings.',
      );
    }
  }

  private async useOnline(): Promise<void> {
    this.dictionaryAction = 'switching-online';
    this.dictionaryActionMessage = '';
    this.dictionaryActionError = '';
    try {
      await vocabClient.useOnline();
      this.dictionaryActionMessage = 'Now using Online for this session.';
      await this.loadDictionarySettings();
    } catch (error) {
      this.dictionaryActionError = this.messageFor(
        error,
        'Could not switch to Online for this session.',
      );
    } finally {
      this.dictionaryAction = 'idle';
    }
  }

  private async useOffline(): Promise<void> {
    this.dictionaryAction = 'switching-offline';
    this.dictionaryActionMessage = '';
    this.dictionaryActionError = '';
    try {
      await vocabClient.useOffline();
      this.dictionaryActionMessage = 'Now using Offline for this session.';
      await this.loadDictionarySettings();
    } catch (error) {
      this.dictionaryActionError = this.messageFor(
        error,
        'Could not switch to Offline for this session.',
      );
    } finally {
      this.dictionaryAction = 'idle';
    }
  }

  private async installOffline(): Promise<void> {
    this.dictionaryAction = 'installing';
    this.dictionaryActionMessage = '';
    this.dictionaryActionError = '';
    try {
      const result = await vocabClient.installOffline();
      this.dictionaryActionMessage = `Installed full Offline dictionary (status: ${result.status}).`;
      await this.loadDictionarySettings();
    } catch (error) {
      this.dictionaryActionError = this.messageFor(
        error,
        'Could not install the full Offline dictionary.',
      );
    } finally {
      this.dictionaryAction = 'idle';
    }
  }

  private async removeOffline(): Promise<void> {
    this.dictionaryAction = 'removing';
    this.dictionaryActionMessage = '';
    this.dictionaryActionError = '';
    try {
      const result = await vocabClient.removeOffline();
      this.dictionaryActionMessage = `Removed Offline dictionary: ${result.detail}`;
      this.confirmRemoveOffline = false;
      await this.loadDictionarySettings();
    } catch (error) {
      this.dictionaryActionError = this.messageFor(
        error,
        'Could not remove the Offline dictionary.',
      );
    } finally {
      this.dictionaryAction = 'idle';
    }
  }

  private async clearOnlineCache(): Promise<void> {
    this.dictionaryAction = 'clearing';
    this.dictionaryActionMessage = '';
    this.dictionaryActionError = '';
    try {
      const result = await vocabClient.clearOnlineCache();
      this.dictionaryActionMessage = `Online cache cleared (${result.removed_count} entries).`;
      await this.loadDictionarySettings();
    } catch (error) {
      this.dictionaryActionError = this.messageFor(
        error,
        'Could not clear the Online cache.',
      );
    } finally {
      this.dictionaryAction = 'idle';
    }
  }

  private renderChooser() {
    return html`
      <main class="panel" aria-labelledby="chooser-title">
        <h2 id="chooser-title">Choose how to use the dictionary</h2>
        <p class="muted">
          No canonical full Offline dictionary is available yet. Pick how this
          process should serve the vocabulary:
        </p>
        <div class="workflow-grid">
          <section class="workflow" aria-labelledby="chooser-online-title">
            <h3 id="chooser-online-title">Use Online</h3>
            <p>Start now without downloading the full dictionary. Online applies
              to the current session only.</p>
            <button class="primary" type="button" @click=${() => void this.useOnline()} ?disabled=${this.dictionaryAction !== 'idle'}>
              ${this.dictionaryAction === 'switching-online' ? 'Switching…' : 'Use Online'}
            </button>
          </section>
          <section class="workflow" aria-labelledby="chooser-offline-title">
            <h3 id="chooser-offline-title">Download for Offline use</h3>
            <p>Download ~945 MB and work without internet afterward. The
              free-space preflight happens before any download begins.</p>
            <button type="button" @click=${() => void this.installOffline()} ?disabled=${this.dictionaryAction !== 'idle'}>
              ${this.dictionaryAction === 'installing' ? 'Starting install…' : 'Download for Offline use'}
            </button>
          </section>
        </div>
        ${this.dictionaryActionError ? html`<p class="inline-status error" role="alert">${this.dictionaryActionError}</p>` : nothing}
      </main>
    `;
  }

  private renderSettings() {
    const info = this.dictionarySettings;
    const showChooserBanner = this.dictionaryMode === 'unconfigured' && info?.canonical_offline_valid !== true;
    return html`
      <main class="panel" aria-labelledby="settings-title">
        <div class="toolbar"><h2 id="settings-title">Dictionary</h2><button @click=${() => void this.loadDictionarySettings()} ?disabled=${this.dictionarySettingsStatus === 'loading'}>${this.dictionarySettingsStatus === 'loading' ? 'Refreshing…' : 'Refresh'}</button></div>
        ${this.dictionarySettingsStatus === 'error' ? html`<p class="inline-status error" role="alert">${this.dictionaryActionError}</p>` : nothing}
        ${showChooserBanner ? this.renderChooserInline() : nothing}
        ${info ? html`
          <dl class="settings-meta">
            <dt>Mode</dt><dd data-testid="dictionary-mode">${info.mode}</dd>
            <dt>Canonical Offline</dt><dd><code>${info.canonical_offline_path}</code></dd>
            <dt>Present</dt><dd>${info.canonical_offline_present ? 'yes' : 'no'}</dd>
            <dt>Valid</dt><dd>${info.canonical_offline_valid ? 'yes' : 'no'}</dd>
            ${info.online_info ? html`
              <dt>Online dataset token</dt><dd><code>${info.online_info.dataset_token.slice(0, 16)}…</code></dd>
            ` : nothing}
          </dl>
        ` : nothing}
        <div class="workflow-grid">
          <section class="workflow" aria-labelledby="online-action-title">
            <h3 id="online-action-title">Online</h3>
            <p>${info?.mode === 'online' ? 'Online is active for this session.' : 'Use the trusted Online dictionary for this session only.'}</p>
            <button class="primary" type="button" @click=${() => void this.useOnline()} ?disabled=${this.dictionaryAction !== 'idle' || info?.mode === 'online'}>
              ${this.dictionaryAction === 'switching-online' ? 'Switching…' : 'Use Online for this session'}
            </button>
            <button type="button" @click=${() => void this.clearOnlineCache()} ?disabled=${this.dictionaryAction !== 'idle' || !info?.online_active}>
              ${this.dictionaryAction === 'clearing' ? 'Clearing…' : 'Clear Online cache'}
            </button>
          </section>
          <section class="workflow" aria-labelledby="offline-action-title">
            <h3 id="offline-action-title">Offline</h3>
            <p>${info?.mode === 'offline' ? 'Offline is active for this session.' : 'Activate the trusted full Offline dictionary for this session.'}</p>
            <button class="primary" type="button" @click=${() => void this.useOffline()} ?disabled=${this.dictionaryAction !== 'idle' || info?.mode === 'offline' || !info?.canonical_offline_valid}>
              ${this.dictionaryAction === 'switching-offline' ? 'Switching…' : 'Use Offline'}
            </button>
            <button type="button" @click=${() => void this.installOffline()} ?disabled=${this.dictionaryAction !== 'idle' || info?.canonical_offline_valid === true}>
              ${this.dictionaryAction === 'installing' ? 'Starting install…' : 'Download for Offline use'}
            </button>
            ${info?.mode === 'offline' && !this.confirmRemoveOffline ? html`
              <button class="danger" type="button" @click=${() => { this.confirmRemoveOffline = true; }} ?disabled=${this.dictionaryAction !== 'idle'}>
                Remove Offline dictionary
              </button>
            ` : nothing}
            ${this.confirmRemoveOffline ? html`
              <div class="confirm" role="alertdialog">
                <p>Remove the canonical Offline dictionary while Online is active? Choose another mode (Online for this session) first if Offline is in use.</p>
                <button class="danger" type="button" @click=${() => void this.removeOffline()} ?disabled=${this.dictionaryAction !== 'idle'}>Confirm remove Offline</button>
                <button type="button" @click=${() => { this.confirmRemoveOffline = false; }}>Cancel</button>
              </div>
            ` : nothing}
          </section>
        </div>
        ${this.dictionaryActionMessage ? html`<p class="inline-status" role="status">${this.dictionaryActionMessage}</p>` : nothing}
        ${this.dictionaryActionError ? html`<p class="inline-status error" role="alert">${this.dictionaryActionError}</p>` : nothing}
      </main>
    `;
  }

  private renderChooserInline() {
    return html`
      <section class="panel" aria-labelledby="inline-chooser-title">
        <h3 id="inline-chooser-title">Choose how to use the dictionary</h3>
        <p class="muted">No canonical full Offline dictionary is available. Online applies to this session only.</p>
        <div class="actions">
          <button class="primary" type="button" @click=${() => void this.useOnline()} ?disabled=${this.dictionaryAction !== 'idle'}>
            ${this.dictionaryAction === 'switching-online' ? 'Switching…' : 'Use Online'}
          </button>
          <button type="button" @click=${() => void this.installOffline()} ?disabled=${this.dictionaryAction !== 'idle'}>
            ${this.dictionaryAction === 'installing' ? 'Starting install…' : 'Download for Offline use'}
          </button>
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
          <div class="actions"><button class="primary" @click=${() => void this.openStudy(deck.id)}>Study this deck</button><button @click=${() => { this.selectedDeckId = null; this.view = 'decks'; }}>All decks</button></div>
        </div>
        <p>Card data and review scheduling remain on the server.</p>
        <div class="workflow-grid">
          ${this.renderCaptureCreation(deck)}
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
            <h1>Wortlaut</h1>
            <div class="subtitle">German vocabulary</div>
          </div>
          <nav class="primary-nav" aria-label="Main navigation">
            <button type="button" aria-current=${this.view === 'study' ? 'false' : 'page'} @click=${() => { this.view = 'decks'; this.selectedDeckId = null; }}>Decks</button>
            <button type="button" aria-current=${this.view === 'study' ? 'page' : 'false'} @click=${() => void this.openStudy()}>Study due</button>
            <button type="button" aria-current=${this.view === 'settings' || this.view === 'chooser' ? 'page' : 'false'} @click=${() => { this.view = 'settings'; void this.loadDictionarySettings(); }}>Settings</button>
            <button type="button" @click=${this.loadDecks} ?disabled=${this.deckStatus === 'loading'}>${this.deckStatus === 'loading' ? 'Refreshing…' : 'Refresh decks'}</button>
          </nav>
        </header>
        ${this.renderNotices()}
        ${this.view === 'chooser' ? this.renderChooser() :
          this.view === 'settings' ? this.renderSettings() :
          this.view === 'study' ? this.renderStudy() :
          showDeckList ? html`
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
      <nav class="bottom-nav" aria-label="Main navigation">
        <button type="button" aria-current=${this.view === 'study' ? 'false' : 'page'} @click=${() => { this.view = 'decks'; this.selectedDeckId = null; }}>Decks</button>
        <button type="button" aria-current=${this.view === 'study' ? 'page' : 'false'} @click=${() => void this.openStudy()}>Study due</button>
      </nav>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'flashcard-app': FlashcardApp;
  }
}
