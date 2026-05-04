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
};

export type ExplorerSearchResponse = {
  items: ImageSummary[];
  total: number;
  page: number;
  page_size: number;
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
