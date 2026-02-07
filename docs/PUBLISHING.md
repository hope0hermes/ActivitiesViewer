# Publishing Guide

## Overview

ActivitiesViewer can be published to the private Devpi PyPI index. This guide covers the publishing process.

## Prerequisites

### Required GitHub Secrets

Configure these in your repository settings:

1. **DEVPI_PASSWORD** - Password for Devpi authentication
2. **DEVPI_URL** - Devpi index URL (e.g., `http://144.24.233.179/hope0hermes/dev/`)
3. **DEVPI_USERNAME** - Username for Devpi (e.g., `hope0hermes`)
4. **PAT_TOKEN** - Personal Access Token for PR creation

### Required Tools

- UV package manager (for local builds)
- Access to the Devpi server

## Publishing Methods

### 1. GitHub Actions (Recommended)

Publishing via GitHub Actions is automated and consistent:

```bash
# Push your changes to main
git push origin main

# Wait for tests to pass

# Trigger publish workflow
# Go to: GitHub → Actions → Publish to Devpi → Run workflow
```

The workflow will:
1. Build the package with UV
2. Extract version from `src/activities_viewer/__init__.py`
3. Publish to Devpi private index
4. Report success/failure

### 2. Manual Publishing

For testing or emergency publishing:

```bash
# Build the package
uv build

# Publish to Devpi
uv publish \
  --publish-url http://144.24.233.179/hope0hermes/dev/ \
  --username hope0hermes \
  --password <your-password>
```

## Version Management

### Automated Versioning (Recommended)

The project uses automated semantic versioning:

1. **Commit with conventional format**:
   ```bash
   git commit -m "feat: add new dashboard feature"
   ```

2. **Push to main**:
   ```bash
   git push origin main
   ```

3. **Release workflow**:
   - Analyzes commits since last version
   - Determines version bump (major/minor/patch)
   - Creates PR with version bump and changelog update

4. **Merge version PR**:
   - Triggers GitHub release creation
   - Tags the release

5. **Publish** (manual):
   - Run publish workflow from GitHub Actions

### Manual Versioning

If you need to manually bump the version:

```bash
# Edit src/activities_viewer/__init__.py
__version__ = "0.2.0"

# Update CHANGELOG.md
# Add entry for new version

# Commit
git add src/activities_viewer/__init__.py CHANGELOG.md
git commit -m "chore: bump version to 0.2.0"

# Tag
git tag v0.2.0
git push origin main --tags
```

## Semantic Versioning

We follow [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (X.0.0) - Breaking changes
- **MINOR** (0.X.0) - New features (backward compatible)
- **PATCH** (0.0.X) - Bug fixes

### Commit Type → Version Bump

| Commit Type | Version Bump | Example |
|-------------|--------------|---------|
| `feat!:` or `BREAKING CHANGE:` | Major | 1.0.0 → 2.0.0 |
| `feat:` | Minor | 1.0.0 → 1.1.0 |
| `fix:` | Patch | 1.0.0 → 1.0.1 |
| `docs:`, `style:`, `refactor:`, etc. | None | - |

## Installing Published Packages

### From Devpi Private Index

```bash
# Using pip
pip install --index-url http://144.24.233.179/hope0hermes/dev/ activities-viewer

# Using UV
uv pip install --index-url http://144.24.233.179/hope0hermes/dev/ activities-viewer

# Specific version
pip install --index-url http://144.24.233.179/hope0hermes/dev/ activities-viewer==0.1.0
```

### Configure pip to use Devpi by default

Create/edit `~/.pip/pip.conf`:

```ini
[global]
index-url = http://144.24.233.179/hope0hermes/dev/
```

Or create a requirements file:

```txt
# requirements.txt
--index-url http://144.24.233.179/hope0hermes/dev/
activities-viewer>=0.1.0
strava-analyzer>=1.2.0
```

## Verifying Published Packages

### Check Package on Devpi

```bash
# List available versions
pip index versions activities-viewer --index-url http://144.24.233.179/hope0hermes/dev/

# Install and test
pip install --index-url http://144.24.233.179/hope0hermes/dev/ activities-viewer
python -c "import activities_viewer; print(activities_viewer.__version__)"
```

### View Package Details

Visit in browser:
```
http://144.24.233.179/hope0hermes/dev/activities-viewer/
```

## Troubleshooting

### Build Failures

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Rebuild
uv build

# Check build artifacts
ls -lh dist/
```

### Authentication Errors

```bash
# Verify credentials
curl -u hope0hermes:<password> http://144.24.233.179/hope0hermes/dev/

# Update GitHub secrets if needed
# Settings → Secrets and variables → Actions
```

### Version Conflicts

```bash
# Check current version
grep __version__ src/activities_viewer/__init__.py

# Check published versions
pip index versions activities-viewer --index-url http://144.24.233.179/hope0hermes/dev/

# Bump version if conflict
# Edit src/activities_viewer/__init__.py
```

### Workflow Failures

Check GitHub Actions logs:
```
GitHub → Actions → Publish to Devpi → <failed run>
```

Common issues:
- Missing secrets
- Network connectivity to Devpi
- Version already published (use different version)
- Build errors (check pyproject.toml syntax)

## Publishing Checklist

Before publishing:

- [ ] All tests pass (`uv run pytest`)
- [ ] Linting passes (`uv run ruff check .`)
- [ ] Type checking passes (`uv run mypy src/`)
- [ ] Version bumped in `__init__.py`
- [ ] CHANGELOG.md updated
- [ ] Documentation updated
- [ ] Committed and pushed to main
- [ ] GitHub tests workflow passed

To publish:

- [ ] Run "Publish to Devpi" workflow from GitHub Actions
- [ ] Verify workflow succeeded
- [ ] Test installation from Devpi
- [ ] Verify package works correctly

## Best Practices

1. **Always use automated versioning** via conventional commits
2. **Test locally** before publishing (`uv build`)
3. **Use GitHub Actions** for publishing (consistent environment)
4. **Tag releases** in Git for traceability
5. **Update documentation** with each release
6. **Keep CHANGELOG.md** current
7. **Test installations** from Devpi after publishing

## Related Documentation

- [SharedWorkflows Publishing](https://github.com/hope0hermes/SharedWorkflows/blob/main/docs/PUBLISHING.md)
- [Devpi Complete Guide](../../private_index/DEVPI_COMPLETE_GUIDE.md)
- [Development Guide](DEVELOPMENT.md)
- [Conventional Commits](https://www.conventionalcommits.org/)
