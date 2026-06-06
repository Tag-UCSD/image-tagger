export const velocityResponse = {
  series: [
    { timestamp: "2026-05-04T08:00:00Z", count: 12 },
    { timestamp: "2026-05-04T09:00:00Z", count: 18 },
    { timestamp: "2026-05-04T10:00:00Z", count: 15 },
    { timestamp: "2026-05-04T11:00:00Z", count: 22 },
    { timestamp: "2026-05-04T12:00:00Z", count: 9 },
    { timestamp: "2026-05-04T13:00:00Z", count: 31 },
    { timestamp: "2026-05-04T14:00:00Z", count: 27 },
    { timestamp: "2026-05-04T15:00:00Z", count: 19 },
  ],
};

export const irrResponse = {
  rows: [
    {
      attribute_key: "light.daylight_ratio",
      attribute_name: "Daylight Ratio",
      irr: 0.67,
      bin: "high",
      n_pairs: 28,
    },
    {
      attribute_key: "texture.visual_complexity",
      attribute_name: "Visual Complexity",
      irr: 0.44,
      bin: "medium",
      n_pairs: 14,
    },
    {
      attribute_key: "room.has_natural_light",
      attribute_name: "Has Natural Light",
      irr: 0.31,
      bin: "low",
      n_pairs: 11,
    },
  ],
};

export const irrEmptyResponse = { rows: [] };

export const validationsResponse = [
  {
    validation_id: 9101,
    image_id: 201,
    rater: "demo.tagger",
    value: 1,
    created_at: "2026-05-04T12:15:00Z",
  },
  {
    validation_id: 9102,
    image_id: 201,
    rater: "demo.supervisor",
    value: 0,
    created_at: "2026-05-04T12:18:00Z",
  },
];

export const inspectorResponse = {
  image: {
    image_id: 201,
    url: "https://picsum.photos/seed/201/1280/960",
  },
  tags: ["daylight", "window", "biophilic"],
  features: ["light.daylight_ratio", "texture.visual_complexity"],
  validations: validationsResponse,
};

export const pipelineHealthResponse = {
  import_ok: true,
  cv2_available: true,
  analyzers_by_tier: {
    tier_1: ["color", "shape"],
    tier_2: ["daylight", "vegetation"],
  },
  warnings: [],
  analyzer_errors: [],
};

// ─── Workplan 2: latent status for an image set ─────────────────────────────

const LATENT_TAGS = [
  "social.sociopetal_seating",
  "social.shared_attention_anchor",
  "social.interactional_visibility",
  "spatial.prospect",
  "social.chance_encounter_potential",
  "social.disengagement_ease",
];

export const latentStatusResponse = {
  image_set_id: 1,
  total_images: 250,
  images_with_all_six: 248,
  failures: 2,
  threshold: 2.5,
  by_detector: LATENT_TAGS.map((tag_id) => ({
    tag_id,
    mean_value: 2.1,
    pct_above_threshold: 0.42,
    mean_confidence: 0.5,
    n_observations: 248,
  })),
  warnings: [],
};

export const latentStatusSuspiciousResponse = {
  image_set_id: 2,
  total_images: 180,
  images_with_all_six: 180,
  failures: 0,
  threshold: 2.5,
  by_detector: [
    {
      tag_id: "social.sociopetal_seating",
      mean_value: 3.6,
      pct_above_threshold: 0.91,
      mean_confidence: 0.55,
      n_observations: 180,
    },
    {
      tag_id: "social.shared_attention_anchor",
      mean_value: 0.2,
      pct_above_threshold: 0.0,
      mean_confidence: 0.18,
      n_observations: 180,
    },
    {
      tag_id: "social.interactional_visibility",
      mean_value: 2.0,
      pct_above_threshold: 0.5,
      mean_confidence: 0.5,
      n_observations: 180,
    },
    {
      tag_id: "spatial.prospect",
      mean_value: 2.0,
      pct_above_threshold: 0.0,
      mean_confidence: 0.5,
      n_observations: 180,
    },
    {
      tag_id: "social.chance_encounter_potential",
      mean_value: 2.0,
      pct_above_threshold: 0.5,
      mean_confidence: 0.5,
      n_observations: 180,
    },
    {
      tag_id: "social.disengagement_ease",
      mean_value: 2.0,
      pct_above_threshold: 0.5,
      mean_confidence: 0.5,
      n_observations: 180,
    },
  ],
  warnings: [
    {
      tag_id: "social.sociopetal_seating",
      code: "skew_high",
      message: "Over 80% of values are above the 2.5 threshold.",
    },
    {
      tag_id: "social.shared_attention_anchor",
      code: "skew_low",
      message: "Over 80% of values are below 0.5.",
    },
    {
      tag_id: "social.shared_attention_anchor",
      code: "low_confidence",
      message: "Mean confidence is below 0.2.",
    },
    {
      tag_id: "spatial.prospect",
      code: "all_identical",
      message: "All recorded values are identical.",
    },
  ],
};

export const latentStatusEmptyResponse = {
  image_set_id: 0,
  total_images: 0,
  images_with_all_six: 0,
  failures: 0,
  threshold: 2.5,
  by_detector: [],
  warnings: [],
};
