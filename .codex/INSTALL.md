# Installing Last30days For Codex

One-command install:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lawful-meow/last30days-codex-plugin/refs/heads/main/scripts/install.sh)
```

From a local checkout:

```bash
bash scripts/install.sh
```

The installer:

- copies `plugins/last30days` to `~/plugins/last30days`
- merges a `last30days` entry into `~/.agents/plugins/marketplace.json`
- enables `codex_hooks = true` in `~/.codex/config.toml`
- enables `last30days@<marketplace-name>` in `~/.codex/config.toml`
- writes the Last 30 Days `SessionStart` hook into `~/.codex/hooks.json`

## Configure API Keys

Preferred per-project config:

```bash
mkdir -p .codex
chmod 700 .codex
cat > .codex/last30days.env <<'EOF'
SCRAPECREATORS_API_KEY=...
OPENAI_API_KEY=...
EOF
chmod 600 .codex/last30days.env
```

Compatible alternatives:

- `codex login`
- `.claude/last30days.env`
- `~/.config/last30days/.env`
- environment variables

At minimum, `SCRAPECREATORS_API_KEY`, `OPENAI_API_KEY`, or a valid `codex login` session is required.

## Verify

```bash
ls -la ~/plugins/last30days
ls -la ~/.agents/plugins/marketplace.json
ls -la ~/.codex/hooks.json
rg -n 'codex_hooks|last30days@' ~/.codex/config.toml
```

Restart Codex after install. On the next session start, the hook should stay silent when config is valid and should show a warning when config is missing or insecure.
