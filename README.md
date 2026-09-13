# Apex Runtime

State persistence, CI/CD, connectors, search, monitoring, recovery, docs, and skill registry for the APEX system.

## Engines

### 1. State Persistence
Remember across sessions.

```bash
python3 runtime.py state set current_task "build MCP server"
python3 runtime.py state get current_task
python3 runtime.py state list
python3 runtime.py state history
```

### 2. CI/CD Workflows
Auto-test on push.

```bash
python3 runtime.py ci generate --repo /path/to/repo
python3 runtime.py ci list
```

### 3. Connector Runtime
MCP server that runs connectors.

```bash
python3 runtime.py connector list
python3 runtime.py connector tools
python3 runtime.py connector health
```

### 4. Search/Discovery
Index and search across estate.

```bash
python3 runtime.py search index --repo /path/to/repo
python3 runtime.py search query "MCP server"
python3 runtime.py search stats
```

### 5. Monitoring
Health checks and alerts.

```bash
python3 runtime.py monitor check --repos /path/to/repo1,/path/to/repo2
python3 runtime.py monitor history
python3 runtime.py monitor latest
```

### 6. Error Recovery
Rollback and recovery mechanisms.

```bash
python3 runtime.py recovery checkpoint "before_deploy"
python3 runtime.py recovery checkpoints
python3 runtime.py recovery rollback <checkpoint_id>
python3 runtime.py recovery history
```

### 7. Documentation Site
Central docs hub.

```bash
python3 runtime.py docs add --repo /path/to/repo
python3 runtime.py docs generate
python3 runtime.py docs search "MCP"
```

### 8. Skill Registry
Index of all available skills.

```bash
python3 runtime.py skills register /path/to/skill.md
python3 runtime.py skills list
python3 runtime.py skills search "MCP"
python3 runtime.py skills stats
```

## Testing

```bash
pytest tests/ -v
```

## License

MIT

### Machine–Mesh Protocol Manifest

<!-- glacier-eq-protocol:start -->
```yaml
{
  "schema": "glacier-eq.readme.machine-mesh/v1",
  "repository": {
    "id": "GlacierEQ/apex-runtime",
    "url": "https://github.com/GlacierEQ/apex-runtime",
    "readme_contract": "estate-machine-v1",
    "default_branch": "main"
  },
  "machine": {
    "repository_kind": "migration-residue",
    "public_api": "inspect-declared-entrypoints",
    "protocol_files": [],
    "entrypoints": [
      {
        "kind": "source-area",
        "path": "src",
        "policy": "inspect-before-use"
      },
      {
        "kind": "test-area",
        "path": "tests",
        "policy": "run-before-reliance"
      }
    ]
  },
  "presentation": {
    "architecture": [
      "recruiter",
      "master",
      "machine",
      "mesh"
    ],
    "authority": {
      "capability": "stone-psysoc-x",
      "repository": "GlacierEQ/AKOS",
      "manifest": "stones/psysoc-x/stone.json",
      "engine": "infinity_stones/psysoc_x.py"
    },
    "truth_invariant": "presentation-may-change-sequence-density-tone-and-style; facts-evidence-uncertainty-provenance-dignity-and-reader-agency-may-not"
  },
  "license": {
    "class": "NO_ROOT_LICENSE_DETECTED",
    "status": "ORIGINALITY_AND_PROVENANCE_REVIEW_REQUIRED",
    "controlling_path": null,
    "policy": "GlacierEQ/job-app-helix/LICENSE_POLICY.json",
    "may_relicense_automatically": false,
    "upstream_rights_must_be_preserved": false
  },
  "mesh": {
    "primary_home": null,
    "branch": "migration-residue",
    "subcategory": "unresolved-primary-home",
    "routing": [
      {
        "relation": "estate-map",
        "target": "GlacierEQ/monolith",
        "url": "https://github.com/GlacierEQ/monolith"
      }
    ],
    "boundaries": [
      "routing-does-not-transfer-source-code-evidence-deployment-or-lifecycle-authority",
      "generated-contract-is-a-source-index-not-a-runtime-or-provider-receipt",
      "implementation-and-provider-state-require-independent-evidence",
      "presentation-calibration-cannot-promote-claim-or-evidence-state",
      "license-automation-cannot-relicense-unresolved-upstream-or-third-party-rights"
    ]
  },
  "provenance": {
    "generated_by": "GlacierEQ/job-app-helix",
    "generator_contract": "estate-machine-v1",
    "classification_source": null,
    "classification_evidence_path": null,
    "classification_evidence_blob_sha": null,
    "classification_status": null,
    "contract_digest": "85cc4f5512a6c44571ad9946d2aba51a1610e6035ab3f0d6e02c2c535dedf150"
  }
}
```
<!-- glacier-eq-protocol:end -->
