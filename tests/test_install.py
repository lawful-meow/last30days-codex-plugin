import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.py"
HOOK_SCRIPT = REPO_ROOT / "plugins" / "last30days" / "hooks" / "codex-hook.py"
SKILL_PATH = REPO_ROOT / "plugins" / "last30days" / "skills" / "last30days" / "SKILL.md"


def load_module():
    spec = importlib.util.spec_from_file_location("last30days_install", INSTALL_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class InstallScriptTests(unittest.TestCase):
    def test_merge_config_text_adds_codex_hooks_without_multi_agent(self):
        module = load_module()
        existing = "\n".join(
            [
                'model = "gpt-5.4"',
                "",
                "[features]",
                "codex_hooks = false",
                "",
                '[plugins."github@openai-curated"]',
                "enabled = true",
                "",
            ]
        )

        merged = module.merge_config_text(existing, marketplace_name="last30days-local")

        self.assertIn('model = "gpt-5.4"', merged)
        self.assertIn("[features]", merged)
        self.assertIn("codex_hooks = true", merged)
        self.assertEqual(merged.count("codex_hooks = true"), 1)
        self.assertNotIn("multi_agent = true", merged)
        self.assertIn('[plugins."last30days@last30days-local"]', merged)
        self.assertIn("enabled = true", merged)

    def test_merge_marketplace_doc_preserves_existing_plugins_and_upserts_last30days(self):
        module = load_module()
        existing = {
            "name": "personal-plugins",
            "interface": {"displayName": "Personal Plugins"},
            "plugins": [
                {
                    "name": "github",
                    "source": {"source": "local", "path": "./plugins/github"},
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Coding",
                },
                {
                    "name": "last30days",
                    "source": {"source": "local", "path": "./plugins/old-last30days"},
                    "policy": {
                        "installation": "NOT_AVAILABLE",
                        "authentication": "ON_USE",
                    },
                    "category": "Legacy",
                },
            ],
        }

        merged = module.merge_marketplace_doc(existing, installation_policy="INSTALLED_BY_DEFAULT")

        self.assertEqual(merged["name"], "personal-plugins")
        self.assertEqual(merged["interface"]["displayName"], "Personal Plugins")
        entries = {entry["name"]: entry for entry in merged["plugins"]}
        self.assertIn("github", entries)
        self.assertIn("last30days", entries)
        self.assertEqual(entries["last30days"]["source"]["path"], "./plugins/last30days")
        self.assertEqual(entries["last30days"]["policy"]["installation"], "INSTALLED_BY_DEFAULT")
        self.assertEqual(entries["last30days"]["policy"]["authentication"], "ON_INSTALL")
        self.assertEqual(entries["last30days"]["category"], "Productivity")
        self.assertEqual(sum(1 for entry in merged["plugins"] if entry["name"] == "last30days"), 1)

    def test_build_last30days_hooks_doc_only_registers_session_start(self):
        module = load_module()
        plugin_root = Path("/tmp/fake-home/plugins/last30days")

        hooks_doc = module.build_last30days_hooks_doc(plugin_root)
        hooks = hooks_doc["hooks"]

        self.assertEqual(set(hooks), {"SessionStart"})
        self.assertEqual(hooks["SessionStart"][0]["matcher"], "startup|resume")

        command = hooks["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn(str(plugin_root / "hooks" / "codex-hook.py"), command)
        self.assertIn("SessionStart", command)

    def test_run_install_is_idempotent(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            home_dir = temp_root / "home"
            home_dir.mkdir()

            module.run_install(REPO_ROOT, home_dir)
            module.run_install(REPO_ROOT, home_dir)

            installed_plugin = home_dir / "plugins" / "last30days"
            self.assertTrue((installed_plugin / ".codex-plugin" / "plugin.json").exists())
            self.assertTrue((installed_plugin / "hooks" / "codex-hook.py").exists())

            marketplace = json.loads((home_dir / ".agents" / "plugins" / "marketplace.json").read_text())
            self.assertEqual(sum(1 for entry in marketplace["plugins"] if entry["name"] == "last30days"), 1)
            self.assertEqual(
                next(entry for entry in marketplace["plugins"] if entry["name"] == "last30days")["policy"]["installation"],
                "INSTALLED_BY_DEFAULT",
            )

            hooks = json.loads((home_dir / ".codex" / "hooks.json").read_text())
            self.assertEqual(set(hooks["hooks"]), {"SessionStart"})

            config = (home_dir / ".codex" / "config.toml").read_text()
            self.assertIn("codex_hooks = true", config)
            self.assertNotIn("multi_agent = true", config)
            self.assertIn(f'[plugins."last30days@{marketplace["name"]}"]', config)
            self.assertIn("enabled = true", config)

    def test_packaged_skill_mentions_plugins_install_path(self):
        skill = SKILL_PATH.read_text()
        self.assertIn('$HOME/plugins/last30days', skill)

    def test_packaged_skill_script_root_probe_finds_installed_plugin(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            home_dir = temp_root / "home"
            project_dir = temp_root / "project"
            project_dir.mkdir()

            module.run_install(REPO_ROOT, home_dir)

            command = """
for dir in \
  "." \
  "${CLAUDE_PLUGIN_ROOT:-}" \
  "${GEMINI_EXTENSION_DIR:-}" \
  "$HOME/plugins/last30days" \
  "$HOME/.claude/plugins/marketplaces/last30days-skill" \
  "$HOME/.gemini/extensions/last30days-skill" \
  "$HOME/.gemini/extensions/last30days" \
  "$HOME/.claude/skills/last30days" \
  "$HOME/.agents/skills/last30days" \
  "$HOME/.codex/skills/last30days"; do
  [ -n "$dir" ] && [ -f "$dir/scripts/last30days.py" ] && SKILL_ROOT="$dir" && break
done

test -n "${SKILL_ROOT:-}"
printf '%s' "$SKILL_ROOT"
"""
            result = subprocess.run(
                ["/bin/zsh", "-lc", command],
                cwd=project_dir,
                env={**os.environ, "HOME": str(home_dir)},
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertEqual(result.stdout, str(home_dir / "plugins" / "last30days"))


class CodexHookTests(unittest.TestCase):
    def run_hook(self, home_dir: Path, cwd: Path, env=None):
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "test",
            "cwd": str(cwd),
            "source": "startup",
            "model": "gpt-5.4",
        }
        result = subprocess.run(
            ["python3", str(HOOK_SCRIPT), "SessionStart"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env={**os.environ, "HOME": str(home_dir), **(env or {})},
            check=True,
        )
        return json.loads(result.stdout)

    def test_hook_warns_when_no_config_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            data = self.run_hook(root / "home", root / "project")
            self.assertIn("No API keys configured", data["systemMessage"])
            self.assertIn(".codex/last30days.env", data["systemMessage"])

    def test_hook_allows_environment_only_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            data = self.run_hook(root / "home", root / "project", env={"OPENAI_API_KEY": "sk-test"})
            self.assertEqual(data, {})

    def test_hook_accepts_codex_project_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_dir = root / "project"
            config_dir = project_dir / ".codex"
            config_dir.mkdir(parents=True)
            env_file = config_dir / "last30days.env"
            env_file.write_text("SCRAPECREATORS_API_KEY=sc-test\n")
            env_file.chmod(0o600)

            data = self.run_hook(root / "home", project_dir)
            self.assertEqual(data, {})

    def test_hook_falls_back_to_claude_project_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_dir = root / "project"
            config_dir = project_dir / ".claude"
            config_dir.mkdir(parents=True)
            env_file = config_dir / "last30days.env"
            env_file.write_text("SCRAPECREATORS_API_KEY=sc-test\n")
            env_file.chmod(0o600)

            data = self.run_hook(root / "home", project_dir)
            self.assertEqual(data, {})

    def test_hook_warns_on_open_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_dir = root / "project"
            config_dir = project_dir / ".codex"
            config_dir.mkdir(parents=True)
            env_file = config_dir / "last30days.env"
            env_file.write_text("SCRAPECREATORS_API_KEY=sc-test\n")
            env_file.chmod(0o644)

            data = self.run_hook(root / "home", project_dir)
            self.assertIn("chmod 600", data["systemMessage"])
            self.assertIn(str(env_file), data["systemMessage"])


if __name__ == "__main__":
    unittest.main()
