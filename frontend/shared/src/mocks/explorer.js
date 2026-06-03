export const searchResponse = {
  items: [
    {
      id: 101,
      url: "https://picsum.photos/seed/101/800/600",
      thumbnail_url: "https://picsum.photos/seed/101/400/300",
      room_type: "living_room",
      canonical_tags: ["biophilic", "window", "daylight"],
      validation_count: 4,
      top_latent: {
        tag_id: "spatial.prospect",
        label: "Prospect",
        value: 4,
        confidence: 0.7,
        effect_mechanism: "Long sightlines reduce cognitive load and aid wayfinding.",
      },
    },
    {
      id: 102,
      url: "https://picsum.photos/seed/102/800/600",
      thumbnail_url: "https://picsum.photos/seed/102/400/300",
      room_type: "bedroom",
      canonical_tags: ["minimal", "natural_light"],
      validation_count: 2,
      // no top_latent — tests that cards without latents don't break
    },
    {
      id: 103,
      url: "https://picsum.photos/seed/103/800/600",
      thumbnail_url: "https://picsum.photos/seed/103/400/300",
      room_type: "kitchen",
      canonical_tags: ["modern", "open_plan"],
      validation_count: 7,
      top_latent: {
        tag_id: "social.chance_encounter_potential",
        label: "Chance Encounter",
        value: 0,
        confidence: 0.15,
        effect_mechanism: "Open layouts increase informal encounter frequency.",
      },
    },
  ],
  total: 37,
  page: 1,
  page_size: 20,
};

export const searchEmptyResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
};

// ─── Workplan 2: image sets ─────────────────────────────────────────────────

export const imageSetsResponse = {
  items: [
    {
      id: 1,
      slug: "atlas-living-rooms-2024",
      name: "Atlas Living Rooms 2024",
      description: "Curated residential interiors with full provenance.",
      source: "internal_curation",
      item_count: 250,
      created_at: "2026-05-01T10:00:00Z",
    },
    {
      id: 2,
      slug: "studio-cafes-2024",
      name: "Studio Cafes 2024",
      description: "Third-place cafe interiors for social affordance work.",
      source: "creative_commons_flickr",
      item_count: 180,
      created_at: "2026-05-10T14:30:00Z",
    },
  ],
};

export const imageSetsEmptyResponse = { items: [] };

const fullLatentObservations = [
  {
    image_id: 101,
    image_set_id: 1,
    science_run_id: 8801,
    tag_id: "social.sociopetal_seating",
    label: "Sociopetal Seating",
    value: 3,
    value_type: "ordinal",
    confidence: 0.62,
    evidence: {
      openness_score: 0.71,
      seating_cluster_proxy: 0.58,
      proxy_version: "latent-social-v1",
    },
    detector_version: "latent-social-v1",
  },
  {
    image_id: 101,
    image_set_id: 1,
    science_run_id: 8801,
    tag_id: "social.shared_attention_anchor",
    label: "Shared Attention Anchor",
    value: 2,
    value_type: "ordinal",
    confidence: 0.48,
    evidence: {
      central_focus_proxy: 0.66,
      edge_density: 0.32,
      proxy_version: "latent-social-v1",
    },
    detector_version: "latent-social-v1",
  },
  {
    image_id: 101,
    image_set_id: 1,
    science_run_id: 8801,
    tag_id: "social.interactional_visibility",
    label: "Interactional Visibility",
    value: 3,
    value_type: "ordinal",
    confidence: 0.55,
    evidence: {
      openness_score: 0.71,
      depth_source: "proxy",
      proxy_version: "latent-social-v1",
    },
    detector_version: "latent-social-v1",
  },
  {
    image_id: 101,
    image_set_id: 1,
    science_run_id: 8801,
    tag_id: "spatial.prospect",
    label: "Prospect",
    value: 4,
    value_type: "ordinal",
    confidence: 0.7,
    evidence: {
      openness_score: 0.82,
      depth_spread: 0.74,
      depth_source: "proxy",
      proxy_version: "latent-social-v1",
    },
    detector_version: "latent-social-v1",
  },
  {
    image_id: 101,
    image_set_id: 1,
    science_run_id: 8801,
    tag_id: "social.chance_encounter_potential",
    label: "Chance Encounter Potential",
    value: 2,
    value_type: "ordinal",
    confidence: 0.41,
    evidence: {
      path_complexity_proxy: 0.45,
      segmentation_source: "proxy",
      proxy_version: "latent-social-v1",
    },
    detector_version: "latent-social-v1",
  },
  {
    image_id: 101,
    image_set_id: 1,
    science_run_id: 8801,
    tag_id: "social.disengagement_ease",
    label: "Disengagement Ease",
    value: 3,
    value_type: "ordinal",
    confidence: 0.53,
    evidence: {
      openness_score: 0.71,
      edge_density: 0.32,
      proxy_version: "latent-social-v1",
    },
    detector_version: "latent-social-v1",
  },
];

const linkedEffects = [
  {
    tag_id: "social.sociopetal_seating",
    domain: "social",
    mechanism: "Face-to-face seating supports conversation initiation.",
  },
  {
    tag_id: "spatial.prospect",
    domain: "cognitive",
    mechanism: "Long sightlines reduce cognitive load and aid wayfinding.",
  },
  {
    tag_id: "social.shared_attention_anchor",
    domain: "affective",
    mechanism: "A shared focal point synchronizes attention and mood.",
  },
];

const sampleMembership = [
  {
    image_set_id: 1,
    slug: "atlas-living-rooms-2024",
    name: "Atlas Living Rooms 2024",
    room_type: "living_room",
    source_url: "https://example.com/atlas/lr-101",
    photographer: "A. Renner",
    license: "CC BY 4.0",
    license_url: "https://creativecommons.org/licenses/by/4.0/",
  },
];

export const imageDetail = {
  id: 101,
  url: "https://picsum.photos/seed/101/800/600",
  thumbnail_url: "https://picsum.photos/seed/101/400/300",
  room_type: "living_room",
  canonical_tags: ["biophilic", "window", "daylight"],
  validation_count: 4,
  width: 1600,
  height: 1200,
  image_sets: sampleMembership,
  latent_observations: fullLatentObservations,
  linked_effects: linkedEffects,
  science: {
    run_id: 8801,
    run_status: "completed",
    features: {
      "light.daylight_ratio": {
        value: 0.84,
        model_id: "feature_daylight_ratio_v1",
        evaluation_status: "proxy_validated",
        confidence_interval_95: [0.79, 0.88],
        n_training: 0,
        notes: "Derived feature; proxy validated against internal reference set.",
      },
      "texture.visual_complexity": {
        value: 0.41,
        model_id: "feature_visual_complexity_v1",
        evaluation_status: "untested",
        confidence_interval_95: null,
        n_training: 0,
        notes: "Evaluation provenance not yet documented in ML_EVALUATION.md; display as untested in v1.",
      },
    },
    affordances: [
      {
        key: "L059",
        label: "sleep_suitability",
        score: 5.8,
        confidence: {
          value: 5.8,
          model_id: "affordance_L059_lgbm_v1",
          evaluation_status: "validated",
          confidence_interval_95: [5.2, 6.1],
          n_training: 1523,
          notes: "held-out test R²=0.71; see ML_EVALUATION.md#L059",
        },
      },
    ],
  },
  regions: [
    {
      id: 901,
      image_id: 101,
      geometry: { type: "bbox", x: 245, y: 180, width: 320, height: 210 },
      auto_label: null,
      auto_confidence: null,
      manual_label: "window",
    },
  ],
};

// ─── Workplan 2: no-latents variant (image 102) ─────────────────────────────

export const imageDetailNoLatents = {
  id: 102,
  url: "https://picsum.photos/seed/102/800/600",
  thumbnail_url: "https://picsum.photos/seed/102/400/300",
  room_type: "bedroom",
  canonical_tags: ["minimal", "natural_light"],
  validation_count: 2,
  width: 1280,
  height: 960,
  image_sets: [],
  latent_observations: [],
  linked_effects: [],
  science: null,
  regions: [],
};

// ─── Workplan 2: low-confidence proxy variant (image 103) ───────────────────

const lowConfidenceLatents = [
  "social.sociopetal_seating",
  "social.shared_attention_anchor",
  "social.interactional_visibility",
  "spatial.prospect",
  "social.chance_encounter_potential",
  "social.disengagement_ease",
].map((tag_id, i) => ({
  image_id: 103,
  image_set_id: null,
  science_run_id: null,
  tag_id,
  label: tag_id.split(".").pop().replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
  value: i % 3,
  value_type: "ordinal",
  confidence: 0.15 + (i % 3) * 0.03,
  evidence: {
    openness_score: 0.2 + i * 0.04,
    depth_source: "proxy",
    proxy_version: "latent-social-v1",
  },
  detector_version: "latent-social-v1",
}));

export const imageDetailLowConfidence = {
  id: 103,
  url: "https://picsum.photos/seed/103/800/600",
  thumbnail_url: "https://picsum.photos/seed/103/400/300",
  room_type: "kitchen",
  canonical_tags: ["modern", "open_plan"],
  validation_count: 7,
  width: 1920,
  height: 1080,
  image_sets: [
    {
      image_set_id: 2,
      slug: "studio-cafes-2024",
      name: "Studio Cafes 2024",
      room_type: "kitchen",
      source_url: null,
      photographer: null,
      license: "CC0",
      license_url: "https://creativecommons.org/publicdomain/zero/1.0/",
    },
  ],
  latent_observations: lowConfidenceLatents,
  linked_effects: [
    {
      tag_id: "social.chance_encounter_potential",
      domain: "behavioral",
      mechanism: "Open layouts increase informal encounter frequency.",
    },
  ],
  science: null,
  regions: [],
};

export const attributesResponse = {
  attributes: [
    {
      id: 12,
      key: "light.daylight_ratio",
      name: "Daylight Ratio",
      category: "light",
      level: "continuous",
      range: "0..1",
      sources: "science_pipeline_v3.4",
      notes: "Used by explorer filters and workbench validation.",
    },
    {
      id: 13,
      key: "texture.visual_complexity",
      name: "Visual Complexity",
      category: "texture",
      level: "continuous",
      range: "0..1",
      sources: "science_pipeline_v3.4",
      notes: null,
    },
    {
      id: 14,
      key: "room.biophilic_index",
      name: "Biophilic Index",
      category: "room",
      level: "continuous",
      range: "0..1",
      sources: "science_pipeline_v3.4",
      notes: "Composite of daylight, greenery, and natural material features.",
    },
  ],
};
