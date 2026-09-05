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
