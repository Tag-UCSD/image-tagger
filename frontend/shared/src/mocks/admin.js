export const uploadResponse = {
  job_id: "upl_20260504_0001",
  items: 2,
  image_ids: [101, 102],
  status: "queued",
};

export const budgetResponse = {
  spent_usd: 4.25,
  limit_usd: 15.0,
  remaining_usd: 10.75,
  total_spent: 4.25,
  hard_limit: 15.0,
  is_kill_switched: false,
};

export const modelsResponse = [
  {
    id: 1,
    name: "VLM-A",
    is_enabled: true,
    cost_per_1k_tokens: 0.12,
  },
  {
    id: 2,
    name: "VLM-B",
    is_enabled: false,
    cost_per_1k_tokens: 0.08,
  },
  {
    id: 3,
    name: "VLM-C",
    is_enabled: true,
    cost_per_1k_tokens: 0.2,
  },
];

export const costHistoryResponse = [
  { day: "2026-04-28", total_cost: 0.41 },
  { day: "2026-04-29", total_cost: 0.38 },
  { day: "2026-04-30", total_cost: 0.55 },
  { day: "2026-05-01", total_cost: 0.72 },
  { day: "2026-05-02", total_cost: 0.62 },
  { day: "2026-05-03", total_cost: 0.67 },
  { day: "2026-05-04", total_cost: 0.9 },
];

export const uploadJobsResponse = [
  {
    job_id: "upl_20260504_0001",
    status: "queued",
    created_at: "2026-05-04T17:45:00Z",
    image_count: 2,
  },
  {
    job_id: "upl_20260503_0007",
    status: "completed",
    created_at: "2026-05-03T13:20:00Z",
    image_count: 12,
  },
];

export const vlmConfigResponse = {
  provider: "auto",
  engine: "gemini-1.5-flash",
  available_backends: {
    gemini: true,
    openai: true,
    anthropic: false,
  },
  cognitive_prompt_override: "",
  max_batch_size: 8,
  cost_per_1k_images_usd: 0.42,
};

export const vlmTestResponse = {
  engine: "gemini-1.5-flash",
  is_stub: true,
  output: "Mock VLM response",
};

export const trainingExportResponse = [
  { image_id: 101, label: "accept" },
  { image_id: 102, label: "reject" },
];

export const killSwitchEnabled = {
  enabled: true,
  changed_at: "2026-05-04T17:41:12Z",
  total_spent: 4.25,
  hard_limit: 15.0,
  is_kill_switched: true,
};

export const killSwitchDisabled = {
  enabled: false,
  changed_at: "2026-05-04T17:41:12Z",
  total_spent: 4.25,
  hard_limit: 15.0,
  is_kill_switched: false,
};
