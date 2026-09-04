/**
 * Type definitions for the /vocab API endpoints.
 * Conforms to ADR-0001, ADR-0002 §4.1 / §5, ADR-0004 D47, and ADR-0007.
 */

export type MeaningLanguage = 'de' | 'en';
export type NoteStatus = 'resolved' | 'derived_compound' | 'needs_gloss' | 'orphaned';

export interface LemmaGrammar {
  pos?: string | null;
  gender?: string | null;
  plural?: string | null;
  genitive_sg?: string | null;
  aux?: string | null;
  separable?: boolean | null;
  particle?: string | null;
  reflexive?: boolean | null;
  praesens_3sg?: string | null;
  praeteritum_3sg?: string | null;
  partizip_ii?: string | null;
  governs?: string | null;
  comparative?: string | null;
  superlative?: string | null;
  ipa?: string | null;
}

export interface SenseMeaning {
  language: string;
  kind: string;
  ord: number;
  text: string;
  source: string;
  license: string;
}

export interface CandidateSense {
  sense_id: number;
  sense_semantic_ref: string;
  ref: string;
  ord: number;
  gloss: string;
  meanings: SenseMeaning[];
}

export interface RankedExample {
  id: number;
  de: string;
  en: string | null;
  source: string;
  license: string;
  token_count: number | null;
  has_proper: boolean;
}

export interface DerivedComponentInfo {
  lemma: string;
  lemma_ref: string;
  sense_ref: string;
}

export interface Candidate {
  ref: string;
  lemma_semantic_ref: string;
  lemma: string;
  pos: string;
  gender: string | null;
  status: NoteStatus;
  senses?: CandidateSense[];
  grammar?: LemmaGrammar;
  examples?: RankedExample[];
  component_refs?: Array<[string, string]>;
  components?: DerivedComponentInfo[];
}

export interface LookupResponse {
  query: string;
  asset_token: string;
  candidates: Candidate[];
}

export interface HighlightSpan {
  start: number;
  end: number;
}

export interface HighlightRequest {
  sentence_text: string;
  selected_span: HighlightSpan;
  lesson_label: string;
  lesson_id?: string;
  known_lemmas?: string[];
}

export interface HighlightProvenance {
  char_start: number;
  char_end: number;
  lesson_id?: string;
}

export interface CaptureContext {
  sentence_text: string;
  selected_span: HighlightSpan;
  lesson_label: string;
  provenance: HighlightProvenance;
}

export interface HighlightResponse {
  asset_token: string;
  candidates: Candidate[];
  capture_context: CaptureContext;
}

export interface SelectionOverrides {
  front_override?: string | null;
  back_override?: string | null;
  meaning_langs?: MeaningLanguage[];
  user_meanings?: Record<string, string | null>;
}

export type ComponentBindingTuple = [string, string];
export interface ComponentBindingObject {
  lemma_semantic_ref?: string;
  sense_semantic_ref?: string;
  lemma_ref?: string;
  sense_ref?: string;
}

export interface CardSelection {
  ref?: string;
  lemma_semantic_ref?: string;
  sense_semantic_ref?: string | null;
  sense_ref?: string | null;
  status?: NoteStatus;
  component_refs?: Array<ComponentBindingTuple | ComponentBindingObject>;
  component_bindings?: Array<ComponentBindingTuple | ComponentBindingObject>;
  overrides?: SelectionOverrides;
}

export interface CaptureCardsRequest {
  asset_token: string;
  deck: string | { name?: string; lesson_label?: string };
  selections: CardSelection[];
  capture_context?: CaptureContext;
}

export interface CapturedNoteResult {
  note_id: number;
  status: string;
  created: boolean;
  deck_id: number;
}

export interface CaptureCardsResponse {
  notes: CapturedNoteResult[];
  deck_id: number;
}

export interface ImportCsvRequest {
  csv_text: string;
  deck_name: string;
  meaning_languages?: MeaningLanguage[];
  meaning_langs?: MeaningLanguage[];
}

export interface ImportCsvResponse {
  deck_id: number;
  notes_created: number;
  notes_reused: number;
  total_words: number;
}

export interface CreateNoteRequest {
  asset_token?: string;
  lemma_semantic_ref?: string;
  ref?: string;
  sense_semantic_ref?: string | null;
  status?: NoteStatus;
  component_refs?: Array<ComponentBindingTuple | { lemma_semantic_ref: string; sense_semantic_ref: string }>;
  meaning_languages: MeaningLanguage[];
  meaning_langs?: MeaningLanguage[];
  selected_languages?: MeaningLanguage[];
  deck_name?: string;
  lesson_label?: string;
  user_meanings?: Record<string, string>;
}

export interface CreateNoteResponse {
  note_id: number;
  status: string;
  meaning_languages: string[];
  deck_id: number | null;
}

export interface AudioTriggerInfo {
  available: boolean;
  lemma: string;
  token?: string | null;
}

export interface RenderedFront {
  headword: string;
  display_headword: string;
  pos: string;
  gender: string | null;
  article: string | null;
  ipa: string | null;
  text: string;
  audio_trigger: AudioTriggerInfo;
}

export interface RenderedGrammar {
  pos: string;
  lines: string[];
}

export interface RenderedMeaning {
  language: string;
  origin: string;
  is_user_authored: boolean;
  heading: string;
  lines: string[];
}

export interface RenderedExampleLine {
  de: string;
  en: string | null;
  lines: string[];
}

export interface RenderedBack {
  display_headword: string;
  pos: string;
  gender: string | null;
  article: string | null;
  ipa: string | null;
  plural: string | null;
  text: string;
  grammar: RenderedGrammar;
  meanings: RenderedMeaning[];
  examples: RenderedExampleLine[];
}

export interface NextCardData {
  card_id: number;
  note_id: number;
  due_at: string;
  state: number;
  front: RenderedFront;
  back: RenderedBack;
}

export interface NextCardResponse {
  card: NextCardData | null;
}

export interface ReviewCardRequest {
  confidence: number;
}

export interface ReviewCardResponse {
  card_id: number;
  confidence: number;
  rating: number;
  due_at: string;
  interval_days: number;
  state: number;
}

export interface SetGlossRequest {
  language: MeaningLanguage;
  meaning_text: string;
}

export interface SetGlossResponse {
  note_id: number;
  language: string;
  meaning_text: string;
}

export interface DeleteGlossResponse {
  note_id: number;
  language: string;
  deleted: boolean;
}

export interface UploadAudioResponse {
  note_id: number;
  media_filename: string;
  sha256: string;
  byte_size: number;
  format: string;
  source_type: string;
}

export interface RevertAudioResponse {
  note_id: number;
  reverted: boolean;
}

export interface ActivateDictionaryRequest {
  path: string;
  version?: string;
}

export interface ActivateDictionaryResponse {
  status: string;
  version: string;
  asset_token: string;
}

export interface DeckSummary {
  id: number;
  name: string;
  created_at: string;
  card_count: number;
  due_count: number;
  mastery_percent: number;
}

export interface CreateDeckRequest {
  name: string;
}

export interface CreateDeckResponse {
  id: number;
  name: string;
}

export interface DeleteDeckResponse {
  id: number;
  deleted: boolean;
}

export type DictionaryMode = 'offline' | 'online' | 'unconfigured';

export interface DictionarySettingsInfo {
  mode: DictionaryMode;
  canonical_offline_path: string;
  canonical_offline_present: boolean;
  canonical_offline_valid: boolean;
  online_active: boolean;
  online_info?: {
    dataset_token: string;
    asset_token: string;
    cache_dir: string;
  };
  server_owned_offline_install?: boolean;
  install_progress?: {
    status: string;
    downloaded_bytes: number;
    total_bytes: number | null;
    percent: number;
    started_at: string | null;
    finished_at: string | null;
    error: string;
  };
}

export interface InstallOfflineRequest {
  // The browser never supplies a source. The server uses its trusted
  // Offline install triple (version, filename, SHA-256, bytes,
  // download_url) derived from release/dictionary-manifest-v2.json.
  // This interface is intentionally empty.
  [key: string]: never;
}

export interface InstallOfflineResponse {
  status: string;
  canonical_offline_path?: string;
  sha256?: string;
  byte_size?: number;
  measured_bytes?: number;
  safety_threshold_bytes?: number;
}

export interface RemoveOfflineRequest {
  // The browser never supplies a filename. The server removes exactly
  // the managed canonical asset derived from its trusted triple.
  // This interface is intentionally empty.
  [key: string]: never;
}

export interface RemoveOfflineResponse {
  status: string;
  detail: string;
  canonical_offline_path?: string;
}

export interface ClearOnlineCacheResponse {
  status: string;
}

export interface UseOnlineResponse {
  status: 'online';
  online_info: {
    dataset_token: string;
    asset_token: string;
    cache_dir: string;
  };
}

export interface UseOfflineResponse {
  status: 'offline';
  asset_token?: string;
  canonical_offline_path?: string;
}
