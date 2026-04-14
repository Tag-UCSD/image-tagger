# TRS Release Workflow

This document describes how to create a new release of the Tag Registry Service.

## Prerequisites

- Python 3.11+
- `pyyaml` installed (`pip install pyyaml`)
- All changes committed to the registry YAML
- Tests passing (`pytest tests/ -v`)

## Quick Release

```bash
# Run with validation gates (recommended)
python scripts/release.py v0.2.9

# Skip gates if you understand the risks
python scripts/release.py v0.2.9 --skip-gates
```

## Step-by-Step Release Process

### 1. Make Your Changes

Edit the registry YAML file:
```
core/trs-core/v{current}/registry/cnfa_tag_registry_canonical_v{current}.yaml
```

Changes you can make:
- Add new tags
- Modify definitions, aliases, extraction hints
- Update extractability ratings
- Deprecate tags (set `status: deprecated` and `replaced_by: <new_tag>`)

### 2. Validate Your Changes

```bash
python scripts/validate_registry.py core/trs-core/v{current}/registry/
```

This checks:
- Required fields present
- Valid enum values (value_type, status, etc.)
- No duplicate aliases
- No orphan parent/child references
- No circular deprecations

Fix any errors before proceeding.

### 3. Check for Breaking Changes

```bash
python scripts/diff_registry.py v{previous} v{current}
```

Breaking changes that will block release:
- **TAG_REMOVED**: A tag was deleted
- **VALUE_TYPE_CHANGED**: A tag's value_type changed

Warnings that allow release:
- **TAG_DEPRECATED**: A tag was deprecated
- **EXTRACTABILITY_DOWNGRADE**: Extractability reduced

Info (always safe):
- **TAG_ADDED**: New tag added
- **ALIASES_ADDED**: New aliases added
- **DEFINITION_CHANGED**: Definition updated

### 4. Regenerate Contracts

```bash
python scripts/generate_contracts.py v{current}
```

This creates:
- `image_tagger_contract_v{current}.json`
- `article_eater_contract_v{current}.json`
- `bn_contract_v{current}.json`
- `preference_testing_contract_v{current}.json`
- `registry_sha256_v{current}.json`

### 5. Create the Release

```bash
python scripts/release.py v{new}
```

The release script will:
1. Run all validation gates
2. Block if any gates fail
3. Generate contracts
4. Create release ZIP
5. Write manifest and SHA256
6. Log the release to `logs/audit.jsonl`

### 6. Verify the Release

```bash
# Check the artifacts
ls -la release_artifacts/

# Verify the ZIP
unzip -l release_artifacts/Tagging_Contractor_v{new}.zip | head -20

# Check the audit log
cat logs/audit.jsonl | tail -1 | python -m json.tool
```

## Rollback

If a release causes problems:

1. Update `.env` to use previous version:
   ```
   TRS_CORE_VER=v0.2.8
   ```

2. Restart the service:
   ```bash
   ./bin/tc down && ./bin/tc up
   ```

3. Verify rollback:
   ```bash
   curl http://localhost:8401/status
   ```

## Release Gates

| Gate | What It Checks | Blocks Release? |
|------|----------------|-----------------|
| Schema Validation | Required fields, valid enums | Yes |
| Invariant Validation | Duplicate aliases, orphan refs | Yes |
| Breaking Changes | Removed tags, type changes | Yes |
| Contract Generation | Contracts regenerate successfully | Yes |

## Audit Log

Every release is logged to `logs/audit.jsonl`:

```json
{
  "timestamp": "2024-12-21T18:53:34Z",
  "action": "release",
  "user": "student@ucsd.edu",
  "hostname": "lab-machine",
  "result": "success",
  "details": {
    "version": "v0.2.9",
    "previous_version": "v0.2.8",
    "tags_added": 3,
    "tags_removed": 0
  }
}
```

## Troubleshooting

### "Validation has N errors"

Run validation separately to see details:
```bash
python scripts/validate_registry.py core/trs-core/v{version}/registry/ --verbose
```

### "Breaking changes detected"

Run diff to see what changed:
```bash
python scripts/diff_registry.py v{old} v{new}
```

If the breaking change is intentional:
1. This is a MAJOR version bump scenario
2. Coordinate with downstream clients
3. Consider deprecation instead of removal

### "Contract generation failed"

Check the registry YAML for syntax errors:
```bash
python -c "import yaml; yaml.safe_load(open('core/trs-core/v{version}/registry/*.yaml').read())"
```

## Best Practices

1. **Small, frequent releases** are better than large batch changes
2. **Deprecate before removing** - give clients time to migrate
3. **Add aliases liberally** - helps discoverability
4. **Document definitions** - future you will thank you
5. **Run tests before release** - `pytest tests/ -v`
