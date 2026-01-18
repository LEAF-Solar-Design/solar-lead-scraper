# Features Research: Job Listing Classification for Solar CAD/Design Roles

**Domain:** Job listing classification / lead qualification
**Researched:** 2026-01-18
**Confidence:** MEDIUM (based on codebase analysis and labeled data patterns)

## Executive Summary

The scraper aims to identify solar CAD/design job listings as sales leads for solar design automation software. The current rule-based system achieves ~3% precision (16 qualified out of ~530 processed), indicating significant room for improvement. This research identifies high-signal features, anti-pattern indicators, and feature engineering approaches to improve classification accuracy.

---

## High-Signal Features

Features that strongly indicate a relevant solar CAD/design role.

### Tier 1: Solar-Specific Design Tools (Auto-Qualify)

**Confidence: HIGH** - These tools are exclusively used for solar PV design.

| Feature | Signal Strength | Notes |
|---------|----------------|-------|
| `helioscope` | Very Strong | Solar-specific layout/stringing tool |
| `aurora solar` | Very Strong | Residential/commercial solar design platform |
| `pvsyst` | Very Strong | Industry-standard PV simulation software |
| `solaredge designer` | Very Strong | Inverter-specific design tool |
| `opensolaris` | Strong | Open-source solar design tool |

**Why high signal:** These tools have no use outside solar PV design. Any job mentioning them is almost certainly a solar design role.

**Implementation:** Current scraper uses these correctly in TIER 1.

### Tier 2: Solar-Specific Technical Deliverables

**Confidence: HIGH** - These work products are unique to solar design.

| Feature | Signal Strength | Context Required |
|---------|----------------|------------------|
| `stringing diagram` / `stringing layout` | Very Strong | Must be solar context (not tennis) |
| `string sizing` | Very Strong | PV string sizing calculations |
| `module layout` / `array layout` / `panel layout` | Strong | PV array configuration |
| `single line diagram` + solar context | Strong | Electrical SLD for PV systems |
| `permit set` / `plan set` / `permit package` | Strong | Construction documents |
| `voltage drop calculation` | Medium | Common in solar electrical design |
| `conduit schedule` / `wiring schedule` | Medium | Electrical design deliverables |

**Why high signal:** These deliverables are the core outputs of solar CAD work. Combined with solar/PV context, they strongly indicate design roles.

**Current gap:** "stringing" without context triggers tennis false positives. Need compound feature: `stringing AND (solar OR pv) AND NOT (tennis OR racquet)`.

### Tier 3: Design Role Indicators

**Confidence: MEDIUM** - Generic role titles that need solar context.

| Feature | Signal Strength | Context Required |
|---------|----------------|------------------|
| `solar designer` / `pv designer` | Very Strong | Direct match |
| `solar design engineer` | Very Strong | Direct match |
| `solar drafter` / `pv drafter` | Very Strong | Direct match |
| `cad designer` + solar context | Strong | Generic CAD with solar qualification |
| `electrical designer` + solar context | Strong | Generic electrical with solar qualification |
| `autocad drafter` + solar context | Medium | Tool-based with context |

**Current gap:** Generic titles like "Electrical Designer" pass filter when company is non-solar (Tesla, SpaceX).

### Tier 4: Company-Level Signals

**Confidence: MEDIUM** - Not currently implemented, high potential value.

| Feature | Signal Strength | Notes |
|---------|----------------|-------|
| Company name contains "solar" | Strong | Sundog Solar, Zero Impact Solar |
| Company name contains "energy" + renewables focus | Medium | Signal Energy, SunEnergy1 |
| Company name contains "PV" | Strong | PV Pros |
| Known solar company (allowlist) | Very Strong | Requires maintenance |
| Known non-solar company (blocklist) | Very Strong | Tesla, SpaceX, Boeing, Northrop Grumman |

**Implementation opportunity:** Company-level filtering is mentioned in PROJECT.md as an active requirement but not yet implemented.

### Tier 5: Project Type Indicators

**Confidence: MEDIUM** - Solar project context in description.

| Feature | Signal Strength | Notes |
|---------|----------------|-------|
| `residential solar` | Strong | Residential PV market |
| `commercial solar` | Strong | C&I solar market |
| `utility-scale solar` / `utility solar` | Strong | Large-scale PV projects |
| `ground mount solar` | Strong | Specific mounting type |
| `rooftop solar` | Strong | Specific mounting type |
| `solar farm` | Strong | Utility-scale context |
| `carport solar` | Strong | Specific application |

---

## Anti-Pattern Indicators

Features that strongly indicate a false positive (not a relevant lead).

### Category 1: Wrong Industry - Tennis/Racquet Sports

**Confidence: HIGH** - Current false positive category.

| Anti-Feature | Why Triggers | Current Status |
|--------------|--------------|----------------|
| `tennis` | "stringing" search term | Excluded |
| `racquet` / `racket` | Sports equipment | Excluded |
| `pickleball` | Related sport | Excluded |
| `badminton` | Related sport | Excluded |
| `stringer` | Racquet stringing role | NOT excluded - gap |

**Gap:** The term "stringer" without other context may slip through.

### Category 2: Wrong Industry - Aerospace/Space

**Confidence: HIGH** - Solar panels on spacecraft, not terrestrial PV.

| Anti-Feature | Why Triggers | Current Status |
|--------------|--------------|----------------|
| `spacecraft` | Solar panels on satellites | Excluded |
| `satellite` | Space solar | Excluded |
| `aerospace` | Industry context | Excluded |
| `starlink` | SpaceX satellite constellation | Excluded |
| `orbit` / `orbital` | Space context | Excluded |
| `avionics` | Aircraft electronics | Excluded |
| `boeing` | Aerospace company | NOT excluded - gap |
| `lockheed` | Aerospace company | NOT excluded - gap |
| `raytheon` | Defense contractor | NOT excluded - gap |
| `northrop grumman` | Aerospace company | Shows in CSV output - gap |

**Gap:** Company-level aerospace exclusion not implemented. Northrop Grumman appears in output CSV.

### Category 3: Wrong Industry - Semiconductor

**Confidence: HIGH** - Chip design uses "CAD" but wrong domain.

| Anti-Feature | Why Triggers | Current Status |
|--------------|--------------|----------------|
| `semiconductor` | Chip industry | Excluded |
| `asic` / `fpga` / `vlsi` | Chip design | Excluded |
| `foundry` / `wafer` / `silicon` | Chip manufacturing | Excluded |
| `cadence` | EDA tool (chip design) | NOT excluded - gap |
| `synopsys` | EDA tool (chip design) | NOT excluded - gap |
| `mentor graphics` | EDA tool (chip design) | NOT excluded - gap |

**Gap:** EDA tool names not excluded. Searching for "CAD designer" could match chip design roles.

### Category 4: Wrong Role - Field/Installation

**Confidence: HIGH** - Installers don't use design software.

| Anti-Feature | Why Triggers | Current Status |
|--------------|--------------|----------------|
| `installer` | Field work | Excluded |
| `installation technician` | Field work | Excluded |
| `journeyman electrician` | Trade role | Excluded |
| `lineman` / `lineworker` | Utility field work | Excluded |
| `field technician` | Field work | Excluded |
| `solar technician` / `pv technician` | Field work | Excluded |
| `roofer` | Installation labor | NOT excluded - gap |
| `foreman` | Construction supervision | NOT excluded - gap |
| `crew lead` | Installation supervision | NOT excluded - gap |

### Category 5: Wrong Role - Sales/Business Development

**Confidence: HIGH** - Sales roles don't use design software.

| Anti-Feature | Why Triggers | Current Status |
|--------------|--------------|----------------|
| `sales director` / `sales manager` | Sales leadership | Excluded |
| `business development` | BD role | Excluded |
| `account executive` | Sales role | Excluded |
| `sales engineer` | Technical sales | Excluded |
| `solar consultant` | Sales role | NOT excluded - gap |
| `energy consultant` | Sales role | NOT excluded - gap |
| `proposal manager` | Pre-sales role | NOT excluded - gap |

### Category 6: Wrong Role - Management (Non-Design)

**Confidence: MEDIUM** - Managers may influence purchases but don't use software.

| Anti-Feature | Why Triggers | Current Status |
|--------------|--------------|----------------|
| `project manager` | Management role | Excluded |
| `construction manager` | Management role | Excluded |
| `design manager` | Management role | Excluded (but may oversee designers) |
| `ceo` / `cto` / `cfo` | Executive | Excluded |
| `director of` | Leadership role | Partial - some excluded |
| `engineering manager` | May have designers | Shows in CSV - review needed |

**Note:** "Design Manager" appears in output CSV (Voltage company). This could be a false positive OR a legitimate lead (manages design team). Needs case-by-case evaluation.

### Category 7: Wrong Role - Non-Design Engineering

**Confidence: MEDIUM** - Adjacent engineering roles that don't do CAD work.

| Anti-Feature | Why Triggers | Current Status |
|--------------|--------------|----------------|
| `project engineer` | Project coordination | Excluded |
| `structural engineer` | Different discipline | Excluded |
| `civil engineer` | Different discipline | Excluded |
| `protection and control` | Utility focus | Excluded |
| `commissioning engineer` | Field work | Excluded |
| `interconnection engineer` | Utility interface | NOT excluded - gap |
| `grid engineer` | Utility focus | NOT excluded - gap |
| `power systems analyst` | Analysis not design | NOT excluded - gap |

### Category 8: Wrong Domain - BESS/Storage

**Confidence: MEDIUM** - Battery storage is adjacent but different market.

| Anti-Feature | Why Triggers | Current Status |
|--------------|--------------|----------------|
| `bess` | Battery Energy Storage | NOT excluded - appears in titles |
| `battery storage` | Energy storage | NOT excluded - gap |
| `microgrid` | Hybrid systems | NOT excluded - appears in output |
| `energy storage` | Storage market | NOT excluded - gap |

**Note:** BESS appears in output titles ("CADD Drafter/Designer - Substation / Photovoltaic (PV)/ BESS / Wind"). This role IS relevant (PV included) but BESS-only roles would not be.

---

## Feature Engineering Ideas

Approaches to improve classification beyond simple keyword matching.

### 1. Compound Features (Boolean Combinations)

**Recommended priority: HIGH**

Create features that combine multiple signals to reduce false positives.

```python
# Example compound features
is_solar_cad_role = (
    has_cad_tool AND
    has_design_role_title AND
    has_solar_context AND
    NOT has_exclusion_industry
)

is_solar_specific_tool = (
    has_helioscope OR
    has_aurora OR
    has_pvsyst
)

is_tennis_false_positive = (
    has_stringing AND
    (has_tennis OR has_racquet) AND
    NOT has_solar_context
)
```

**Current gap:** Filter uses sequential tiers, not compound boolean logic. A single exclusion term can miss a valid lead if the positive signal is strong enough.

### 2. Company Classification Feature

**Recommended priority: HIGH**

Classify companies into categories before evaluating job listings.

| Company Category | Examples | Treatment |
|-----------------|----------|-----------|
| Solar-focused | Sundog Solar, Soltage, SunEnergy1 | Boost positive weight |
| Renewables diversified | Kimley-Horn (solar practice), Burns & McDonnell | Neutral |
| General engineering | AECOM, Jacobs | Neutral |
| Aerospace/Defense | Boeing, Northrop Grumman, SpaceX | Strong negative weight |
| Semiconductor | Intel, NVIDIA, AMD | Strong negative weight |
| Non-relevant | Tennis clubs, retailers | Auto-reject |

**Implementation approaches:**
1. **Allowlist/Blocklist** - Maintain curated lists (high precision, requires maintenance)
2. **Company name patterns** - Regex on company names (medium precision, low maintenance)
3. **Domain classification** - Use web search/APIs to classify company industry (complex, highest potential)

### 3. Title-Based Feature Extraction

**Recommended priority: MEDIUM**

Extract structured features from job titles.

| Title Component | Feature | Signal |
|----------------|---------|--------|
| Explicit role: "Solar Designer" | `title_explicit_solar_design` | Strong positive |
| CAD tool: "AutoCAD Drafter" | `title_cad_tool` | Positive (needs context) |
| Seniority: "Senior", "Lead", "Principal" | `title_seniority` | Neutral |
| Level: "I", "II", "III" | `title_level` | Neutral |
| Industry qualifier: "- Energy" | `title_industry_energy` | Weak positive |

### 4. Description Section Analysis

**Recommended priority: MEDIUM**

Weight features by where they appear in description.

| Section | Weight | Rationale |
|---------|--------|-----------|
| First 200 characters (title area) | 2x | Most relevant for role identification |
| Requirements/qualifications | 1.5x | Technical skill requirements |
| Responsibilities | 1x | Day-to-day work |
| Company description | 0.5x | Background context |
| Benefits/perks | 0.25x | Least relevant |

**Current implementation:** First 200 chars checked for TIER 4 title signals. Could expand to structured section weighting.

### 5. Frequency-Based Features

**Recommended priority: LOW**

Count occurrences of key terms rather than binary presence.

| Feature | Calculation | Rationale |
|---------|-------------|-----------|
| `solar_mention_count` | Count of "solar"/"pv" | Higher count = stronger solar focus |
| `cad_tool_count` | Count of CAD tool mentions | More tools = more design-focused |
| `exclusion_density` | Count of exclusion terms | Higher = more likely false positive |

### 6. Pattern Learning from Labeled Data

**Recommended priority: HIGH**

Use existing labeled data to identify patterns.

**Available data (per PROJECT.md):**
- 253 rejected leads (2026-01-16)
- 261 rejected leads (2026-01-17)
- 16 qualified leads (2026-01-18)

**Suggested approach:**
1. Extract all terms from qualified vs rejected descriptions
2. Calculate TF-IDF or simple frequency ratios
3. Identify terms that appear much more in qualified (positive signal) vs rejected (negative signal)
4. Add high-ratio terms to filter logic

**Example analysis structure:**
```python
qualified_terms = extract_terms(qualified_leads)
rejected_terms = extract_terms(rejected_leads)

# Terms appearing in qualified but rarely in rejected = positive signals
# Terms appearing in rejected but rarely in qualified = negative signals

signal_ratio = term_freq_qualified / (term_freq_rejected + 1)
```

### 7. Scoring Model Instead of Binary Classification

**Recommended priority: MEDIUM**

Replace pass/fail filter with weighted scoring.

```python
score = 0

# Positive signals
if has_solar_specific_tool: score += 100  # Auto-qualify
if has_solar_context: score += 20
if has_design_role_title: score += 15
if has_cad_tool: score += 10
if company_is_solar: score += 25
if has_strong_technical_signal: score += 20

# Negative signals
if company_is_aerospace: score -= 100  # Auto-reject
if has_installer_terms: score -= 50
if has_sales_terms: score -= 40
if has_management_terms: score -= 20

# Threshold
return score >= 30  # Tunable threshold
```

**Advantage:** Allows fine-tuning without binary pass/fail logic. Can output score for manual review of borderline cases.

---

## Table Stakes Features (Must Have)

Features that any job classification system for this domain must include.

| Feature | Why Required | Current Status |
|---------|--------------|----------------|
| Solar/PV context check | Core domain filter | Implemented |
| Design role title detection | Core role filter | Implemented |
| CAD tool detection | Core skill filter | Implemented |
| Installer/field role exclusion | Major false positive category | Implemented |
| Sales role exclusion | Major false positive category | Implemented |
| Tennis/sports exclusion | Known false positive | Implemented |
| Aerospace exclusion | Known false positive | Partial - needs company-level |

---

## Differentiator Features (Should Have)

Features that would significantly improve precision.

| Feature | Value | Implementation Effort | Recommendation |
|---------|-------|----------------------|----------------|
| Company classification | High - eliminates aerospace/semiconductor FPs | Medium | Implement allowlist/blocklist first |
| Compound boolean logic | High - more nuanced filtering | Low | Refactor filter structure |
| Scoring model | High - replaces binary with gradation | Medium | Implement after compound logic |
| Title parsing | Medium - better role detection | Low | Add title-specific checks |
| BESS/storage handling | Medium - adjacent market clarification | Low | Add conditional logic |

---

## Anti-Features (Should NOT Build)

Features that seem useful but would hurt more than help.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| ML/NLP model from scratch | Small dataset (16 qualified), model drift, black box | Stick with interpretable rules + pattern analysis |
| Automated company research API | Cost, latency, reliability | Manual allowlist/blocklist with periodic updates |
| Real-time learning from user feedback | Complexity, drift risk | Batch retraining with human review |
| Aggressive expansion of search terms | Already wide net causing noise | Focus on filter improvement, not wider search |

---

## Recommended Implementation Phases

Based on research, suggested feature implementation order:

### Phase 1: Low-Hanging Fruit (Quick Wins)

1. Add company blocklist (aerospace: Boeing, Northrop Grumman, SpaceX, Lockheed, Raytheon)
2. Add missing exclusion terms (stringer, roofer, foreman, interconnection engineer)
3. Tighten "stringing" to require compound: stringing AND solar context

### Phase 2: Structure Improvement

1. Refactor filter to use compound boolean logic
2. Implement basic scoring model (can start with all weights = 1)
3. Add company allowlist for known solar companies

### Phase 3: Pattern Learning

1. Analyze labeled data for additional positive/negative signals
2. Calculate term ratios between qualified/rejected
3. Add discovered high-signal terms to filter

### Phase 4: Advanced Features

1. Tune scoring weights based on precision/recall metrics
2. Implement title parsing for structured extraction
3. Add description section weighting

---

## Confidence Assessment

| Feature Category | Confidence | Basis |
|-----------------|------------|-------|
| Solar-specific tools | HIGH | Domain knowledge, no alternative uses |
| Anti-pattern industries | HIGH | Observed in output data (Northrop Grumman) |
| Company classification value | HIGH | Most false positives are company-level |
| Scoring model approach | MEDIUM | Standard pattern, untested for this data |
| Pattern learning potential | MEDIUM | Labeled data exists but small |
| Feature weights | LOW | Would need testing/iteration |

---

## Sources

- Analysis of existing codebase: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py`
- Output data review: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/output/solar_leads_*.csv`
- Project documentation: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/.planning/PROJECT.md`
- Codebase concerns: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/.planning/codebase/CONCERNS.md`

---

*Research completed: 2026-01-18*
