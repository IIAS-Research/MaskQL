# Contributing to MaskQL

Thanks for your interest in MaskQL.
Small and focused contributions are the easiest to review.
This file explains how to report a bug, ask for help, and send a change.

## Before you open a change

- Read [README.md](README.md) for the project overview and development requirements.
- Read [docs/QUICKSTART.md](docs/QUICKSTART.md) if you need a reproducible local walkthrough.
- If you want to work on a larger change, such as a new feature, an API change, or a refactor, please open an issue first so we can discuss the scope before you spend time on it.
- For small bug fixes, test updates, and documentation improvements, you can open a pull request or merge request directly.

## Reporting a bug

Please use the repository issue tracker and include:

- the MaskQL version or commit SHA,
- your environment: OS, Docker version, Python/`uv` version,
- the exact commands you ran,
- the expected behavior,
- the actual behavior,
- a minimal reproducer if possible,
- relevant logs or error messages.

Please do not post credentials, patient data, private datasets, or other sensitive information.
Redact examples before posting them publicly.

## Asking for help

Use the repository issue tracker for:

- installation problems,
- local development setup questions,
- unclear documentation,
- usage questions about catalogs, rules, and the SQL gateway.

A small reproducer is much easier to answer than a screenshot alone.

## Local development

A typical local workflow is:

```bash
cp .env.example .env
bash ./scripts/build-trino-plugin.sh
make local
uv run tox
make down
```

Notes:

- `make local` uses `compose.dev.yml`.
- On a fresh clone, build the Trino plugin once before starting the stack. `compose.dev.yml` mounts the plugin jar from the local workspace.
- `uv run tox` is the closest match to CI.

## Contribution expectations

- Keep changes focused and avoid unrelated refactors.
- Add or update tests when behavior changes.
- Update documentation when user-facing behavior, APIs, or workflows change.
- Follow the existing code style and project structure.
- Clear commit messages help. Conventional Commit prefixes are welcome because releases are automated.

## Review and maintenance

MaskQL is maintained on a best-effort basis.
Some changes may need a few review rounds before merge.
Large, unscoped, or lightly tested changes may be postponed or declined.

## Conduct

Please keep discussions respectful and practical.
