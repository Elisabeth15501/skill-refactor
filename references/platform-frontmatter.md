# Platform frontmatter field matrix

The same skill is consumed by different hosts, and the frontmatter schema differs.
Do **not** invent fields a host does not recognize. Use this matrix to pick the
fields for the target platform, then keep the published skill in the host-neutral
core (`name`, `description`, `when_to_use`) plus that platform's additions.

## Core fields (every platform)

| Field | Required | Notes |
|---|---|---|
| `name` | yes | lowercase hyphen slug; the stable trigger key |
| `description` | yes | what it does + when to use + NOT-for; the primary trigger surface; keep under ~1024 chars |
| `when_to_use` | recommended | explicit triggers + explicit non-triggers |
| `tags` | recommended | discovery keywords |
| `summary` | recommended | one-line plain-English abstract for UI |

## Host A - Claude / WorkBuddy (host-side)

These fields are honored by the Claude/WorkBuddy runtime, **not** by the ClawHub
OpenClaw scanner. They are optional and host-specific; document them per host, do
not force them into a ClawHub-published package.

| Field | Meaning |
|---|---|
| `allowed-tools` | whitelist of tools the skill may use |
| `context: fork` | run the skill in a forked context, keeping the main conversation clean |
| `disable-model-invocation` | forbid auto-triggering; user may still invoke by name |
| `user-invocable` | allow the user to invoke by name |
| `environment` / `network` | self-declared scope, for human trust |

## Host B - ClawHub / OpenClaw (published, scanner-visible)

The scanner reads `metadata.openclaw`. Declaration must match behavior; a code
reference that is not declared is flagged as a mismatch.

| Field | Meaning |
|---|---|
| `metadata.openclaw.requires.bins` | binaries that must all exist |
| `metadata.openclaw.requires.env` | required environment variables |
| `metadata.openclaw.requires.anyBins` | at least one of these must exist |
| `metadata.openclaw.requires.config` | config files the skill reads |
| `metadata.openclaw.primaryEnv` | the main credential variable |
| `metadata.openclaw.os` | supported OS list |
| `metadata.openclaw.install` | how to install deps (brew / node / go / uv) |
| `metadata.openclaw.always` | always-active skill |
| `metadata.openclaw.homepage` / `emoji` / `skillKey` / `nix` | metadata |
| `license: MIT-0` | default license; use only if there is no proprietary content |

> For a skill that ships an offline Python linter (this skill): declare
> `requires.bins: [python3]`, leave `env: []` and `config: []` empty, and set
> `license: MIT-0`. That is the minimal, accurate, scanner-clean declaration.

## Host C - SkillHub (Chinese domestic registry)

| Field | Meaning |
|---|---|
| `license` | keep `MIT` / `MIT-0` for GitHub-synchronized distribution |
| `displayName` | human-facing name |
| content red lines | domestic content review; avoid VPN / "scientific上网"-style wording (see the publish gate) |

## Decision rule

1. Identify the **publish target** (ClawHub / SkillHub / Claude-WorkBuddy / GitHub).
2. Start from the core fields (Host A section's "Core fields" table).
3. Add only that target's additions (Host B / Host C rows).
4. Never merge host-specific fields into a platform's published schema; if a field
   is needed by one host only, keep it in that host's copy, not the neutral package.
