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
