# ActivitiesViewer - Configuration System Upgrade

## Summary of Changes

This document summarizes the improvements made to ActivitiesViewer's CLI and configuration system, bringing it in line with the patterns used in StravaAnalyzer.

### Key Improvements

#### 1. **Pydantic-based Configuration Management**
- **Before:** Simple class-based configuration with hardcoded paths
- **After:** Robust Pydantic `Settings` class with validation, environment variable support, and YAML loading
- **Benefits:**
  - Type-safe configuration with validation
  - Automatic path resolution (relative → absolute)
  - Support for ~ and $VAR expansion in paths
  - Comprehensive error messages

#### 2. **Professional CLI Interface**
- **Before:** Minimal print-based CLI with no actual commands
- **After:** Full-featured Click-based CLI with multiple commands
- **Commands:**
  - `run` - Start the Streamlit dashboard with validation
  - `validate` - Check configuration and data files
  - `version` - Show version information
- **Features:**
  - Custom help formatting
  - Logging configuration
  - Error handling and user-friendly messages
  - Progress indicators (✅, ❌, ⚠️)

#### 3. **YAML Configuration Files**
- **Before:** Environment variables and .env file only
- **After:** YAML configuration files with environment variable overrides
- **Example:**
  ```yaml
  data_dir: "../dev/data_enriched"
  activities_enriched_file: "activities_enriched.csv"
  activity_summary_file: "activity_summary.json"
  streams_dir: "Streams"

  ftp: 285.0
  weight_kg: 77.0
  max_hr: 185
  ```

#### 4. **Enhanced Streamlit Integration**
- **Before:** Streamlit app loaded configuration from hardcoded paths
- **After:** Streamlit app receives configuration via session state from CLI
- **Workflow:**
  ```bash
  activities-viewer run --config config.yaml
  # CLI validates config → passes to Streamlit → runs dashboard
  ```

### File Changes

| File | Changes |
|------|---------|
| `src/activities_viewer/config.py` | Complete rewrite with Pydantic Settings, YAML loading, validation |
| `src/activities_viewer/cli.py` | Full implementation with Click commands, logging, validation |
| `src/activities_viewer/app.py` | Updated to use session state config from CLI |
| `examples/config.yaml` | New comprehensive configuration template |
| `.env.example` | Updated with Pydantic environment variable naming |
| `pyproject.toml` | Added Click, Pydantic, pydantic-settings dependencies |
| `docs/CLI_CONFIGURATION.md` | Complete CLI and configuration reference |
| `docs/QUICK_START.md` | Quick reference guide |

### Dependencies Added

```toml
click>=8.1.0              # CLI framework
pydantic>=2.0.0           # Data validation
pydantic-settings>=2.0.0  # Settings management
```

### Usage Examples

#### Running the Dashboard

```bash
# Basic usage
activities-viewer run --config config.yaml

# Custom port
activities-viewer run --config config.yaml --port 8502

# With verbose logging
activities-viewer run --config config.yaml --verbose
```

#### Validating Configuration

```bash
# Check all data files and settings
activities-viewer validate --config config.yaml

# Output:
# Configuration Validation Summary
# ============================================================
#   data_dir: /path/to/data
#   ftp: 285.0
#   Activities loaded: 1812 records
#   Stream files: 1812 found
# ============================================================
# ✅ All validations passed!
```

### Configuration Loading Order

Settings are now loaded with proper precedence:

1. **Environment Variables** (highest priority)
   - `ACTIVITIES_VIEWER_FTP=290`
   - `ACTIVITIES_VIEWER_DATA_DIR=/path`

2. **YAML Configuration File**
   - Specified via `--config config.yaml`
   - Supports relative paths (resolved from config file location)

3. **Default Values** (lowest priority)
   - Built-in defaults for all settings

### Path Resolution

The configuration system now handles paths intelligently:

```yaml
# Relative path - resolved from config file directory
data_dir: "../dev/data_enriched"
# → Becomes: /absolute/path/to/dev/data_enriched

# Absolute path - used as-is
data_dir: "/home/user/data_enriched"
# → Used directly

# Home directory expansion
data_dir: "~/Activities/data_enriched"
# → Becomes: /home/user/Activities/data_enriched
```

### Data File Validation

The new CLI validates all required files before starting the dashboard:

```bash
$ activities-viewer validate --config config.yaml

❌ Configuration validation failed:
  - Activities file not found: /path/activities_enriched.csv
  - Streams directory not found: /path/Streams
```

### Comparison with StravaAnalyzer Pattern

ActivitiesViewer now follows the same architecture as StravaAnalyzer:

| Aspect | Pattern |
|--------|---------|
| Settings | Pydantic BaseSettings with validation |
| Configuration | YAML files with CLI loading |
| CLI | Click-based with multiple commands |
| Logging | Standard logging with verbosity control |
| Error Handling | Descriptive error messages with context |
| Path Resolution | Intelligent relative/absolute path handling |

### Migration Guide

If you were using the old configuration method:

**Old way (.env file):**
```bash
export DATA_DIR=/path/to/data
export USER_FTP=295
streamlit run src/activities_viewer/app.py
```

**New way (YAML config):**
```bash
# Create config.yaml
cat > config.yaml << EOF
data_dir: /path/to/data
ftp: 295
EOF

# Run with CLI
activities-viewer run --config config.yaml
```

### Benefits of New System

1. ✅ **Validation:** Configuration errors caught before starting dashboard
2. ✅ **Documentation:** YAML config is self-documenting
3. ✅ **Flexibility:** YAML + env vars + defaults for different deployment scenarios
4. ✅ **Consistency:** Same patterns as StravaAnalyzer and StravaFetcher
5. ✅ **Type Safety:** Pydantic ensures all values are correct types
6. ✅ **Path Handling:** Automatic resolution of relative/absolute paths
7. ✅ **User Experience:** Clear error messages and validation feedback

### Next Steps

1. Install updated dependencies: `uv sync`
2. Create configuration file: `cp examples/config.yaml config.yaml`
3. Update paths in `config.yaml` for your environment
4. Validate setup: `activities-viewer validate --config config.yaml`
5. Run dashboard: `activities-viewer run --config config.yaml`

### Documentation

- **[CLI & Configuration Guide](docs/CLI_CONFIGURATION.md)** - Detailed reference
- **[Quick Start Guide](docs/QUICK_START.md)** - Quick reference
- **[README](README.md)** - General information
- **[Setup Guide](docs/SETUP.md)** - Installation instructions
