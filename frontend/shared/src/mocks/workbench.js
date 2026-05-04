const baseImage = {
  id: 101,
  url: "https://picsum.photos/seed/101/800/600",
  thumbnail_url: "https://picsum.photos/seed/101/400/300",
  room_type: "living_room",
  canonical_tags: ["biophilic", "window", "daylight"],
  validation_count: 4,
  width: 1600,
  height: 1200,
  science: null,
  regions: [],
};

export const nextNumber = {
  image: baseImage,
  assignment: {
    attribute_key: "light.daylight_ratio",
    attribute_name: "Daylight Ratio",
    prompt: "Estimate the fraction of the room lit by daylight.",
    value_type: "number",
    allowed_values: null,
    min: 0,
    max: 1,
    step: 0.05,
    required: true,
  },
};

export const nextEnum = {
  image: { ...baseImage, id: 102, url: "https://picsum.photos/seed/102/800/600" },
  assignment: {
    attribute_key: "room.type",
    attribute_name: "Room Type",
    prompt: "What type of room is shown in this image?",
    value_type: "enum",
    allowed_values: ["living_room", "bedroom", "kitchen", "bathroom", "office", "other"],
    min: null,
    max: null,
    step: null,
    required: true,
  },
};

export const nextBoolean = {
  image: { ...baseImage, id: 103, url: "https://picsum.photos/seed/103/800/600" },
  assignment: {
    attribute_key: "room.has_natural_light",
    attribute_name: "Has Natural Light",
    prompt: "Does this room receive visible natural light from a window or skylight?",
    value_type: "boolean",
    allowed_values: null,
    min: null,
    max: null,
    step: null,
    required: true,
  },
};

export const nextEmpty = { empty: true };

export const validateResponse = {
  validation_id: 4402,
  accepted: true,
};
