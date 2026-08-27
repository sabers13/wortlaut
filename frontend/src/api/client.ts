/**
 * Stateless, typed fetch client for /vocab endpoints.
 * Conforms to ADR-0001, ADR-0002 §4.1 / §5, ADR-0004 D47, and AGENTS rules R1, R6, R12.
 *
 * Requirements:
 * - Every non-GET request must send X-Flashcards-Request: 1
 * - JSON requests must send Content-Type: application/json
 * - Uses only the /vocab prefix
 * - Completely stateless and ephemeral: no scheduler, FSRS/rating mapping, due state,
 *   authoritative card cache, IndexedDB, or persistence.
 */

import { parseApiError } from './errors.ts';
import type {
  ActivateDictionaryRequest,
  ActivateDictionaryResponse,
  CaptureCardsRequest,
  CaptureCardsResponse,
  CreateDeckRequest,
  CreateDeckResponse,
  CreateNoteRequest,
  CreateNoteResponse,
  DeckSummary,
  DeleteDeckResponse,
  DeleteGlossResponse,
  HighlightRequest,
  HighlightResponse,
  ImportCsvRequest,
  ImportCsvResponse,
  LookupResponse,
  MeaningLanguage,
  NextCardResponse,
  RevertAudioResponse,
  ReviewCardResponse,
  SetGlossResponse,
  UploadAudioResponse,
} from './types.ts';

export interface VocabClientOptions {
  baseUrl?: string;
  fetch?: typeof globalThis.fetch;
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'DELETE' | 'PUT' | 'PATCH';
  params?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  headers?: Record<string, string>;
  responseType?: 'json' | 'text' | 'blob';
}

export class VocabClient {
  readonly baseUrl: string;
  private readonly _fetch: typeof globalThis.fetch;

  constructor(options: VocabClientOptions = {}) {
    this.baseUrl = options.baseUrl ? options.baseUrl.replace(/\/+$/, '') : '';
    this._fetch = options.fetch ?? globalThis.fetch.bind(globalThis);
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const method = options.method ?? 'GET';
    const isGet = method === 'GET';

    // Build URL with query parameters
    let url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
    if (options.params) {
      const searchParams = new URLSearchParams();
      for (const [key, value] of Object.entries(options.params)) {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      }
      const qs = searchParams.toString();
      if (qs) {
        url += (url.includes('?') ? '&' : '?') + qs;
      }
    }

    const headers: Record<string, string> = { ...options.headers };

    // AGENTS R12 / ADR-0002: Custom header required on all non-GET requests
    if (!isGet) {
      headers['X-Flashcards-Request'] = '1';
    }

    let requestBody: BodyInit | undefined;

    if (options.body !== undefined && options.body !== null) {
      if (
        options.body instanceof FormData ||
        options.body instanceof Blob ||
        options.body instanceof ArrayBuffer ||
        ArrayBuffer.isView(options.body)
      ) {
        requestBody = options.body as BodyInit;
        // Do not set Content-Type for FormData; browser/fetch adds multipart boundary
      } else {
        headers['Content-Type'] = 'application/json';
        requestBody = JSON.stringify(options.body);
      }
    }

    const response = await this._fetch(url, {
      method,
      headers,
      body: requestBody,
    });

    if (!response.ok) {
      throw await parseApiError(response);
    }

    if (options.responseType === 'text') {
      return (await response.text()) as unknown as T;
    }
    if (options.responseType === 'blob') {
      return (await response.blob()) as unknown as T;
    }

    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return undefined as unknown as T;
    }

    return (await response.json()) as T;
  }

  // -------------------------------------------------------------------------
  // Dictionary & Lookup Endpoints
  // -------------------------------------------------------------------------

  /**
   * Search lemmas and surface forms in the active dictionary (GET /vocab/lookup).
   */
  async lookup(query: string): Promise<LookupResponse> {
    return this.request<LookupResponse>('/vocab/lookup', {
      method: 'GET',
      params: { q: query },
    });
  }

  /**
   * Search lemmas and surface forms in the active dictionary (POST /vocab/lookup).
   */
  async lookupPost(query: string): Promise<LookupResponse> {
    return this.request<LookupResponse>('/vocab/lookup', {
      method: 'POST',
      body: { query },
    });
  }

  /**
   * Activate a replacement dictionary file (POST /vocab/dictionary/activate).
   */
  async activateDictionary(request: ActivateDictionaryRequest): Promise<ActivateDictionaryResponse> {
    return this.request<ActivateDictionaryResponse>('/vocab/dictionary/activate', {
      method: 'POST',
      body: request,
    });
  }

  // -------------------------------------------------------------------------
  // Capture Endpoints
  // -------------------------------------------------------------------------

  /**
   * Stage 1: Resolve span candidates and rank examples (POST /vocab/highlight).
   * Zero writes to user database.
   */
  async highlight(request: HighlightRequest): Promise<HighlightResponse> {
    return this.request<HighlightResponse>('/vocab/highlight', {
      method: 'POST',
      body: request,
    });
  }

  /**
   * Stage 2: Atomically persist selected candidate cards to deck (POST /vocab/cards).
   */
  async captureCards(request: CaptureCardsRequest): Promise<CaptureCardsResponse> {
    return this.request<CaptureCardsResponse>('/vocab/cards', {
      method: 'POST',
      body: request,
    });
  }

  /**
   * Batch word list import into deck (POST /vocab/import/csv).
   */
  async importCsv(request: ImportCsvRequest): Promise<ImportCsvResponse> {
    return this.request<ImportCsvResponse>('/vocab/import/csv', {
      method: 'POST',
      body: request,
    });
  }

  /**
   * Single note creation endpoint (POST /vocab/notes).
   */
  async createNote(request: CreateNoteRequest): Promise<CreateNoteResponse> {
    return this.request<CreateNoteResponse>('/vocab/notes', {
      method: 'POST',
      body: request,
    });
  }

  // -------------------------------------------------------------------------
  // Review & Study Endpoints
  // -------------------------------------------------------------------------

  /**
   * Fetch next due card for study, optionally filtered by deck (GET /vocab/cards/next).
   */
  async getNextCard(deckId?: number): Promise<NextCardResponse> {
    return this.request<NextCardResponse>('/vocab/cards/next', {
      method: 'GET',
      params: { deck_id: deckId },
    });
  }

  /**
   * Log a review rating for a card with raw confidence 1..5 (POST /vocab/cards/{card_id}/review).
   * Note: Client-supplied rating is forbidden by API; pass raw confidence only.
   */
  async reviewCard(cardId: number, confidence: number): Promise<ReviewCardResponse> {
    return this.request<ReviewCardResponse>(`/vocab/cards/${cardId}/review`, {
      method: 'POST',
      body: { confidence },
    });
  }

  // -------------------------------------------------------------------------
  // Gloss / Meaning Endpoints
  // -------------------------------------------------------------------------

  /**
   * Set user-authored meaning/gloss on a note (POST /vocab/notes/{note_id}/gloss).
   */
  async setGloss(
    noteId: number,
    language: MeaningLanguage,
    meaningText: string,
  ): Promise<SetGlossResponse> {
    return this.request<SetGlossResponse>(`/vocab/notes/${noteId}/gloss`, {
      method: 'POST',
      body: {
        language,
        meaning_text: meaningText,
      },
    });
  }

  /**
   * Delete user-authored meaning/gloss on a note (DELETE /vocab/notes/{note_id}/gloss).
   */
  async deleteGloss(noteId: number, language: MeaningLanguage): Promise<DeleteGlossResponse> {
    return this.request<DeleteGlossResponse>(`/vocab/notes/${noteId}/gloss`, {
      method: 'DELETE',
      params: { language },
    });
  }

  // -------------------------------------------------------------------------
  // Audio Endpoints
  // -------------------------------------------------------------------------

  /**
   * Upload custom pronunciation audio for a note (POST /vocab/notes/{note_id}/audio).
   */
  async uploadAudio(
    noteId: number,
    audioData: Blob | ArrayBuffer | Uint8Array | FormData,
    contentType?: string,
  ): Promise<UploadAudioResponse> {
    const headers: Record<string, string> = {};
    if (contentType && !(audioData instanceof FormData)) {
      headers['Content-Type'] = contentType;
    }
    return this.request<UploadAudioResponse>(`/vocab/notes/${noteId}/audio`, {
      method: 'POST',
      body: audioData,
      headers,
    });
  }

  /**
   * Revert custom pronunciation audio for a note (DELETE /vocab/notes/{note_id}/audio).
   */
  async revertAudio(noteId: number): Promise<RevertAudioResponse> {
    return this.request<RevertAudioResponse>(`/vocab/notes/${noteId}/audio`, {
      method: 'DELETE',
    });
  }

  /**
   * Build URL for audio endpoint (GET /vocab/audio/{audio_id}).
   */
  getAudioUrl(audioId: string | number): string {
    const cleanId = encodeURIComponent(String(audioId));
    return `${this.baseUrl}/vocab/audio/${cleanId}`;
  }

  /**
   * Fetch audio binary data (GET /vocab/audio/{audio_id}).
   */
  async fetchAudio(audioId: string | number): Promise<Blob> {
    const cleanId = encodeURIComponent(String(audioId));
    return this.request<Blob>(`/vocab/audio/${cleanId}`, {
      method: 'GET',
      responseType: 'blob',
    });
  }

  // -------------------------------------------------------------------------
  // Deck Management Endpoints
  // -------------------------------------------------------------------------

  /**
   * List all decks with card count, due count, and mastery % (GET /vocab/decks).
   */
  async getDecks(): Promise<DeckSummary[]> {
    return this.request<DeckSummary[]>('/vocab/decks', {
      method: 'GET',
    });
  }

  /**
   * Create a new deck (POST /vocab/decks).
   */
  async createDeck(name: string): Promise<CreateDeckResponse> {
    const req: CreateDeckRequest = { name };
    return this.request<CreateDeckResponse>('/vocab/decks', {
      method: 'POST',
      body: req,
    });
  }

  /**
   * Delete a deck (DELETE /vocab/decks/{deck_id}).
   * Orphaned notes move to Orphaned deck without cascading review history.
   */
  async deleteDeck(deckId: number): Promise<DeleteDeckResponse> {
    return this.request<DeleteDeckResponse>(`/vocab/decks/${deckId}`, {
      method: 'DELETE',
    });
  }

  // -------------------------------------------------------------------------
  // Export Endpoints
  // -------------------------------------------------------------------------

  /**
   * Export deck or entire collection to Anki TSV format (GET /vocab/export/anki).
   */
  async exportAnki(deckId?: number): Promise<string> {
    return this.request<string>('/vocab/export/anki', {
      method: 'GET',
      params: { deck_id: deckId },
      responseType: 'text',
    });
  }
}

/**
 * Factory function to create a new VocabClient instance.
 */
export function createVocabClient(options?: VocabClientOptions): VocabClient {
  return new VocabClient(options);
}
