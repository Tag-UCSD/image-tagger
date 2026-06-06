export type Role = "tagger" | "scientist" | "supervisor" | "admin";

export type JwtClaims = {
  sub: string;
  role: Role;
};

export type TrustEvaluationStatus = "validated" | "proxy_validated" | "untested";

export type TrustEnvelope<T> = {
  value: T;
  model_id: string;
  evaluation_status: TrustEvaluationStatus;
  confidence_interval_95: [number, number] | null;
  n_training: number;
  notes: string;
};

export type ImageSummary = {
  id: number;
  url: string;
  thumbnail_url: string;
  room_type: string | null;
  canonical_tags: string[];
  validation_count: number;
};

export type AttributeDef = {
  id: number;
  key: string;
  name: string;
  category: string | null;
  level: string | null;
  range: string | null;
  sources: string | null;
  notes: string | null;
};

export type RegionGeometry =
  | {
      type: "bbox";
      x: number;
      y: number;
      width: number;
      height: number;
    }
  | {
      type: "polygon";
      points: Array<{ x: number; y: number }>;
    };

export type RegionCreate = {
  image_id: number;
  geometry: RegionGeometry;
  manual_label: string;
};

export type Region = {
  id: number;
  image_id: number;
  geometry: RegionGeometry;
  auto_label: string | null;
  auto_confidence: number | null;
  manual_label: string | null;
};

export type AffordancePrediction = {
  key: string;
  label: string;
  score: number;
  confidence: TrustEnvelope<number>;
};

export type SciencePayload = {
  run_id: number;
  run_status: "pending" | "running" | "completed" | "failed";
  features: Record<string, TrustEnvelope<number>>;
  affordances: AffordancePrediction[];
};

export type ImageDetail = ImageSummary & {
  width: number;
  height: number;
  science: SciencePayload | null;
  regions: Region[];
  image_sets?: ImageSetMembership[];
  latent_observations?: LatentObservation[];
  linked_effects?: LinkedEffect[];
};

// ─── Workplan 2: image sets ─────────────────────────────────────────────────

export type ImageSetSummary = {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  source: string | null;
  item_count: number;
  created_at: string;
};

export type ImageSetMembership = {
  image_set_id: number;
  slug: string;
  name: string;
  room_type: string | null;
  source_url: string | null;
  photographer: string | null;
  license: string | null;
  license_url: string | null;
};

export type ImageSetImportImage = {
  filename: string;
  url?: string;
  path?: string;
  storage_path?: string;
  room_type?: string;
  source_url?: string;
  photographer?: string;
  license?: string;
  license_url?: string;
  tags?: string[];
  meta_data?: Record<string, unknown>;
};

export type ImageSetImportRequest = {
  name: string;
  slug: string;
  description?: string;
  source?: string;
  provenance?: Record<string, unknown>;
  images: ImageSetImportImage[];
};

export type ImageSetImportResponse = {
  image_set_id: number;
  slug: string;
  created_images: number;
  reused_images: number;
  created_items: number;
  skipped_items: number;
  errors: Array<{ filename: string; message: string }>;
  total_in_file: number;
};

// ─── Workplan 2: latent observations and effects ─────────────────────────────

export type LatentTagId =
  | "social.sociopetal_seating"
  | "social.shared_attention_anchor"
  | "social.interactional_visibility"
  | "spatial.prospect"
  | "social.chance_encounter_potential"
  | "social.disengagement_ease";

export type EffectDomain =
  | "cognitive"
  | "affective"
  | "behavioral"
  | "social"
  | "physiological"
  | "neural"
  | "health";

export type LatentObservation = {
  image_id: number;
  image_set_id: number | null;
  science_run_id: number | null;
  tag_id: LatentTagId | string;
  label: string;
  value: number; // 0..4 ordinal
  value_type: "ordinal";
  confidence: number; // 0..1
  evidence: Record<string, unknown>;
  detector_version: string;
};

export type LinkedEffect = {
  tag_id: LatentTagId | string;
  domain: EffectDomain;
  mechanism: string;
};

export type LatentRunSummary = {
  image_set_id: number;
  queued: number;
  running: number;
  completed: number;
  failed: number;
  already_complete: number;
};

export type LatentDetectorStat = {
  tag_id: LatentTagId | string;
  mean_value: number;
  pct_above_threshold: number;
  mean_confidence: number;
  n_observations: number;
};

export type LatentDistributionWarning = {
  tag_id: LatentTagId | string;
  code:
    | "all_identical"
    | "skew_high"
    | "skew_low"
    | "low_confidence";
  message: string;
};

export type LatentStatusResponse = {
  image_set_id: number;
  total_images: number;
  images_with_all_six: number;
  failures: number;
  threshold: number;
  by_detector: LatentDetectorStat[];
  warnings: LatentDistributionWarning[];
};

export type WorkbenchLatentAssignment = {
  image: ImageDetail;
  latent: {
    tag_id: LatentTagId | string;
    label: string;
    value: number;
    value_type: "ordinal";
    confidence: number;
    evidence: Record<string, unknown>;
    detector_version: string;
  };
};

export type LatentValidationSubmit = {
  image_id: number;
  tag_id: LatentTagId | string;
  value: number;
  duration_ms: number;
};

export type ExplorerSearchResponse = {
  items: ImageSummary[];
  total: number;
  page: number;
  page_size: number;
};

export type ExplorerSearchParams = {
  q?: string;
  page?: number;
  page_size?: number;
  room_type?: string;
  tag?: string;
  // Workplan 2 filters
  image_set?: string;
  latent_tag?: LatentTagId | string;
  effect_domain?: EffectDomain | string;
  min_value?: number;
};

export type VelocityPoint = {
  timestamp: string;
  count: number;
};

export type IRRRow = {
  attribute_key: string;
  attribute_name: string;
  irr: number;
  bin: "low" | "medium" | "high";
  n_pairs: number;
};

export type WorkbenchAssignment = {
  image: ImageDetail;
  assignment: {
    attribute_key: string;
    attribute_name: string;
    prompt: string;
    value_type: "boolean" | "number" | "enum";
    allowed_values: Array<string | number | boolean> | null;
    min: number | null;
    max: number | null;
    step: number | null;
    required: true;
  };
};

export type ValidationSubmit = {
  image_id: number;
  attribute_key: string;
  value: string | number | boolean;
  duration_ms: number;
};

export type ErrorDetail = {
  field: string;
  message: string;
  type: string;
};

export type ErrorResponse = {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: ErrorDetail[];
  };
};
