# WORKPLAN 2 OVERVIEW

Workplan 2 rewrites the objectives from `/Users/tds/Documents/GitHub/tagger update assignment` as local feature work for `/Users/tds/Documents/GitHub/image-tagger`.

The old assignment asked students to build a 500-image collection, implement six latent-tag detectors, batch annotate the collection, and ship a standalone HTML viewer into an upstream Knowledge Atlas branch. In this local repo, those objectives should become product features inside the existing FastAPI and React app.

The current local app already has the surfaces that the assignment treated as missing:

- Explorer for public browse and detail inspection
- Admin for upload and operational controls
- Workbench for human validation
- Monitor for supervisor visibility
- a science pipeline with canonical science runs

The meaningful update is therefore:

- add named image sets with provenance
- add latent social-spatial observations with detector evidence
- update the existing GUIs to browse, validate, and monitor those outputs

## Main Product Objectives

1. **Image sets:** import and preserve named collections with provenance.
2. **Latent variables:** compute six local social-spatial scores on a `0..4` ordinal scale.
3. **GUIs:** expose image-set browsing, latent/effect filtering, detail evidence, validation, and monitoring through the existing four apps.

## Selected Latent Variables

- `social.sociopetal_seating`
- `social.shared_attention_anchor`
- `social.interactional_visibility`
- `spatial.prospect`
- `social.chance_encounter_potential`
- `social.disengagement_ease`

All outputs must include value, value type, confidence, detector version, and evidence JSON.

