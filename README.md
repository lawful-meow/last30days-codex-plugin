# Last30days Codex Plugin

Last30days Codex Plugin packages [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) `v2.9.5` for Codex.

This wrapper keeps the upstream research engine vendored under `plugins/last30days` and adds the Codex-specific pieces the upstream repo does not ship:

- a Codex plugin manifest under `plugins/last30days/.codex-plugin/plugin.json`
- a home marketplace installer for `~/plugins/last30days`
- a Codex `SessionStart` hook entry in `~/.codex/hooks.json` that warns when config is missing or insecure

## Install

From a local checkout:

```bash
bash scripts/install.sh
```

If you want to bootstrap from a published remote instead, set `LAST30DAYS_REPO_URL` first and then run the same script.

After the installer finishes, restart Codex. The installer copies the plugin bundle to `~/plugins/last30days`, merges a `last30days` entry into `~/.agents/plugins/marketplace.json`, enables `last30days@<marketplace-name>` in `~/.codex/config.toml`, enables `codex_hooks`, and registers the `SessionStart` config check in `~/.codex/hooks.json`.

Full setup details are documented in [`.codex/INSTALL.md`](./.codex/INSTALL.md).

## Config

Supported config sources, in precedence order:

1. Environment variables such as `OPENAI_API_KEY` or `SCRAPECREATORS_API_KEY`
2. `.codex/last30days.env`
3. `.claude/last30days.env`
4. `~/.config/last30days/.env`

The Codex hook checks those locations on session start and warns if no config is found or if a config file is too open.

## Repository Layout

- `plugins/last30days/`
  Vendored upstream runtime plus Codex-specific manifest and hook adapter.
- `scripts/install.py`
  Installer that updates `~/plugins`, `~/.agents`, and `~/.codex`.
- `scripts/install.sh`
  Local one-command installer and optional remote bootstrap wrapper.
- `upstream/`
  Provenance snapshot files copied from the upstream repository.

## Provenance

- upstream repository: <https://github.com/mvanhorn/last30days-skill>
- upstream release packaged here: `v2.9.5`
