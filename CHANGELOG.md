# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Dockerfile and docker-compose.yml for sharing via GHCR
- `docs/SHARING.md` — guide for distributing to friends via Docker

### Changed
- Rewrite README.md with accurate features, structure, and quick start
- Rewrite all docs/ files (QUICK_START, SETUP, DATA_STRUCTURE, CLI_CONFIGURATION, DEVELOPMENT) to reflect current architecture
- Remove obsolete `CONFIGURATION_UPGRADE.md` (pre-Pydantic migration doc)
- Update pyproject.toml classifiers from Alpha to Beta

### Fixed
- Remove stale `tool.black` config from pyproject.toml (project uses ruff)
- Remove dead `deployment` optional deps (gunicorn, psycopg2, redis)

## [1.7.0] - 2026-02-25

### Changed
- feat(ai-coach): fleet-level stream analytics (#23)


## [1.6.3] - 2026-02-25

### Changed
- fix: None YAML sections crash + AI stream data access (#21)


## [1.6.2] - 2026-02-25

### Changed
- fix: align default data_dir with StravaFetcher to avoid re-auth on sync (#19)


## [1.6.1] - 2026-02-24

### Changed
- fix: remove stale VERSION file and add unified config example (#16)


## [1.6.0] - 2026-02-24

### Changed
- feat: align config field names and eliminate field_map (Phase 7) (#14)


## [1.5.0] - 2026-02-24

### Changed
- feat: add mtime-based caching and broad numeric coercion to CSVActivityRepository (Phase 6) (#12)


## [1.4.0] - 2026-02-24

### Changed
- feat: sync Activity model + add contract tests (Phase 4+5) (#9)


## [1.3.0] - 2026-02-24

### Changed
- feat: delegate OAuth to StravaFetcher library (Phase 3) (#8)


## [1.2.0] - 2026-02-22

### Changed
- feat: replace subprocess pipeline with direct library API calls (#6)
- chore: remove Docker build (will rebuild after refactoring) (#5)


## [1.1.0] - 2026-02-22

### Changed
- ci: add permissions to release workflow
- fix: add requests to mypy ignore_missing_imports
- style: fix all ruff lint errors
- chore: move AI dependencies to optional extras
- feat: add strava-fetcher and strava-analyzer as direct dependencies
- feat: refactor into a full pipeline
- feat: ia-coach has access to training plan
- docs: update changelog with first working version note
- fix: resolve mypy type errors across codebase
- chore: align CI/CD workflows with SharedWorkflows patterns
- feat: add long term memory context
- feat: add ia-assisted training plan generator
- feat: enforce consistent metrics usage from input data table. Add calendar view, as well as CTL and FTP trends. Improve chatbot context. Add training plan generator
- feat: add ftp trend chart
- feat: add historical comparison
- feat: add trend arrows and tss calendar view
- chore: small layout refacotring (manual)
- feat: refactor for more streamlined navigation
- chore: minor fixes
- feat: pages refactor, more metrics and better visialization
- chore: add monthly page and fix yearly one
- chore: fix activity details
- chore: refactor to read from raw and moving input files (checkup activity details only)
- chore: add project structure and initial implementation with help text tooltips
- chore: initial empty commit


## [1.0.0] - 2025-07-22

First working version, extensively tested locally.

### Added
- Streamlit multi-page dashboard with 4 pages: Analysis, Detail, AI Coach, Training Planner
- CSV-based data repository for Strava activities
- YAML configuration with Pydantic validation (`config.py`)
- CLI entry point via Click (`cli.py`)
- AI Coach page with Google Gemini integration (LangChain)
  - Dynamic model selection with semantic version sorting
  - Persistent chat history (`~/.activitiesviewer/chat_history.json`)
  - Long-term memory consolidation (50 exchanges → summary blocks)
  - Info expander documenting capabilities, context, and limitations
  - Sidebar cache management (clear chat, reset memory, clear all)
- Training Planner page with AI-generated plans
  - Info expander with capabilities and limitations
- Analytics module with activity insights
- Persistent cache system (`cache.py`) for chat history, memory summaries, and geocode data
- Activity service layer for data access
- Domain models for cycling activities
- Complete CI/CD setup with SharedWorkflows integration
  - Commitlint for conventional commit enforcement
  - Automated tests and linting via reusable workflows
  - Automated release with semantic versioning
  - Devpi publishing via manual dispatch
- GitHub configuration: CODEOWNERS, PR template
- Comprehensive test scaffolding with pytest + coverage

[Unreleased]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.7.0...HEAD
[1.7.0]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.6.3...v1.7.0
[1.6.3]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.6.2...v1.6.3
[1.6.2]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.6.1...v1.6.2
[1.6.1]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/hope0hermes/ActivitiesViewer/releases/tag/v1.0.0
