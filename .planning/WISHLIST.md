# Wishlist

Low-priority improvements to address when time permits. None of these block production use.

For actual issues that need fixing, see [ISSUES.md](ISSUES.md).

---

## Documentation

### Add `.env.example` file
- **Description:** Create a template showing required environment variables for local development
- **Current state:** Env vars are documented in CLAUDE.md, but no template file exists
- **Benefit:** Faster onboarding for new developers

### Add root `README.md`
- **Description:** Create a README that links to CLAUDE.md and DATA_ARCHITECTURE_PLAN.md
- **Current state:** Documentation exists but is split across multiple files
- **Benefit:** Standard entry point for GitHub visitors

---

## Repository Hygiene

### Add `output/.gitkeep`
- **Description:** Ensure output directory exists in repo with a `.gitkeep` placeholder
- **Current state:** Directory is created at runtime via `mkdir(exist_ok=True)`
- **Benefit:** Clearer repo structure

---

## Code Quality

### Refactor GitHub Actions merge step
- **Description:** Move inline Python from workflow YAML to a separate script
- **Current state:** 250+ lines of Python embedded in YAML via `-c` flag
- **Benefit:** Easier to test, debug, and maintain

### Add file operation timeouts
- **Description:** Large JSON/CSV reads could hang indefinitely
- **Current state:** No timeouts on file I/O
- **Benefit:** Prevent infinite hangs on slow/locked files

### Mask proxy credentials in logs
- **Description:** Proxy URLs with credentials could appear in CI logs
- **Current state:** No credential masking
- **Benefit:** Security hygiene

---

*Last updated: 2025-01-23*
