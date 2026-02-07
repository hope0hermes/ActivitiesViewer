# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/hope0hermes/ActivitiesViewer/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/hope0hermes/ActivitiesViewer/releases/tag/v1.0.0
