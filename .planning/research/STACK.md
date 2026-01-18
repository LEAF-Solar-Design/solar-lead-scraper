# Stack Research: Text Classification for Job Listing Filtering

**Project:** Solar Lead Scraper - Improved Filtering
**Researched:** 2026-01-18
**Research Mode:** Stack (technology recommendations)

## Context

- **Current state:** Rule-based keyword filtering with ~3% precision
- **Training data:** ~500 rejected leads, ~16 qualified leads (highly imbalanced, ~97:3 ratio)
- **Constraint:** No ML infrastructure overhead, runs on GitHub Actions
- **Goal:** Improve precision without complexity explosion

## Recommended Stack

### Tier 1: Enhanced Rule-Based (RECOMMENDED START)

**Confidence: HIGH** (established patterns, no external verification needed)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pandas | >=2.0 | Data manipulation | Already in stack, excellent for filtering |
| re (stdlib) | N/A | Pattern matching | Regex for complex term detection |
| json (stdlib) | N/A | Load labeled data | Parse training JSON files |

**Rationale:** With only 16 positive examples, ML will overfit. The immediate win is to analyze your labeled data and improve keyword rules. This is not "giving up on ML" - it is recognizing that data-driven rule refinement is more valuable than premature ML.

**Approach:**
1. Load rejected/qualified JSON files
2. Analyze term frequency differences between classes
3. Identify high-signal exclusion terms from rejected data
4. Identify high-signal inclusion terms from qualified data
5. Refine the tiered filter based on evidence

### Tier 2: Lightweight Statistical Classification

**Confidence: MEDIUM** (established approach, versions need verification)

When you have 50+ positive examples, consider:

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| scikit-learn | >=1.4 | Classification | Industry standard, lightweight, no GPU needed |

**Specific Components:**

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
```

**Why These Models for Small Data:**

1. **Naive Bayes (MultinomialNB)** - Best for tiny datasets
   - Works well with <100 examples
   - Handles imbalanced classes naturally
   - Fast, interpretable
   - Use with `class_prior` parameter to handle imbalance

2. **Logistic Regression** - Good baseline
   - Interpretable (can see which terms drive decisions)
   - Works with `class_weight='balanced'` for imbalanced data
   - Regularization prevents overfitting

3. **Random Forest** - When you have 100+ positives
   - More robust feature interactions
   - Built-in feature importance
   - Use `class_weight='balanced_subsample'`

**TF-IDF Configuration for Job Listings:**

```python
vectorizer = TfidfVectorizer(
    max_features=1000,      # Limit vocabulary for small data
    ngram_range=(1, 2),     # Unigrams + bigrams capture "solar designer"
    min_df=2,               # Term must appear 2+ times
    stop_words='english',
    sublinear_tf=True       # Dampen term frequency
)
```

### Tier 3: Embedding-Based (Future)

**Confidence: MEDIUM** (approach is sound, specific versions need verification)

When you have 200+ positive examples OR want to leverage pre-trained knowledge:

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| sentence-transformers | >=2.2 | Text embeddings | Pre-trained semantic understanding |

**Model Recommendation:**
- `all-MiniLM-L6-v2` - Fast, good quality, 384 dimensions
- Use with scikit-learn classifiers on embeddings

**Why NOT yet:**
- Pre-trained embeddings help when you have semantic similarity needs
- With 16 examples, you cannot fine-tune
- Adding 400MB+ model dependency for marginal gain

## Handling Class Imbalance

**Confidence: HIGH** (fundamental ML principles)

Your 97:3 imbalance is severe. Approaches ranked by simplicity:

### 1. Class Weights (RECOMMENDED)

```python
# Scikit-learn handles this automatically
model = LogisticRegression(class_weight='balanced')
```

### 2. Threshold Adjustment

```python
# Default threshold is 0.5, adjust for precision/recall tradeoff
probabilities = model.predict_proba(X)[:, 1]
predictions = (probabilities > 0.3).astype(int)  # Lower threshold = more recall
```

### 3. Manual Oversampling (if needed)

```python
from sklearn.utils import resample
# Oversample minority class
qualified_oversampled = resample(qualified_data, n_samples=len(rejected_data)//5)
```

**What NOT to use:**
- SMOTE - Generates synthetic text embeddings that are nonsensical
- Complex ensemble methods - Overkill for this dataset size

## What NOT to Use

### Transformers/Deep Learning

**Do not use:** transformers, pytorch, tensorflow, bert, gpt-based classification

**Why:**
1. Your dataset has 16 positive examples - deep learning needs thousands
2. Fine-tuning requires GPU infrastructure
3. Model size (100MB-1GB+) versus benefit is poor
4. Inference latency matters less than model complexity here

### LLM-Based Classification

**Do not use:** OpenAI API, Claude API, Ollama for classification

**Why:**
1. API costs scale with job listing volume
2. Latency for batch processing
3. Dependency on external service
4. Your rule-based approach with 500+ labeled examples will match or beat zero-shot LLM

### Heavy NLP Libraries

**Avoid for now:** spaCy, nltk (full install), stanza

**Why:**
1. You do not need NER, POS tagging, dependency parsing
2. Large model downloads (300MB+)
3. TF-IDF captures enough signal for this task

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| Vectorization | TF-IDF | Word2Vec/GloVe | Pre-trained word vectors average out, lose specificity |
| Classification | Naive Bayes/LogReg | SVM | SVM slower, similar performance on text |
| Classification | Scikit-learn | PyTorch | Overkill, needs GPU for benefit |
| Embeddings | MiniLM (future) | OpenAI embeddings | API cost, external dependency |
| Imbalance handling | class_weight | SMOTE | SMOTE generates nonsense text |

## Recommended Progression

Given your constraints, recommended approach:

### Phase 1: Data-Driven Rule Refinement (NOW)
```
requirements.txt additions: None (use existing pandas)
```
- Analyze labeled data programmatically
- Find discriminative terms between classes
- Improve keyword tiers based on evidence

### Phase 2: Statistical Baseline (when 50+ positives)
```
requirements.txt additions:
scikit-learn>=1.4
```
- TF-IDF + Logistic Regression
- Compare to rule-based baseline
- Keep rules as fallback

### Phase 3: Hybrid (when 200+ positives)
```
requirements.txt additions:
sentence-transformers>=2.2
```
- Semantic similarity for edge cases
- Rules for clear cases
- ML for ambiguous cases

## Installation Commands

### Phase 1 (Current)
```bash
# No new dependencies
pip install -r requirements.txt
```

### Phase 2 (Future)
```bash
pip install scikit-learn>=1.4
```

### Phase 3 (Future)
```bash
pip install sentence-transformers>=2.2
```

## Confidence Assessment

| Recommendation | Confidence | Notes |
|----------------|------------|-------|
| Enhance rules first | HIGH | Correct approach for 16 examples |
| TF-IDF + NaiveBayes | HIGH | Textbook solution for small text data |
| scikit-learn versions | MEDIUM | Versions based on training data, verify PyPI |
| Avoid deep learning | HIGH | Fundamental: DL needs large datasets |
| sentence-transformers later | MEDIUM | Version needs verification |

## Gaps and Verification Needed

**Unable to verify due to tool limitations:**
- [ ] Current scikit-learn version on PyPI
- [ ] Current sentence-transformers version on PyPI
- [ ] Any new lightweight classification libraries in 2025

**Recommend verifying:**
```bash
pip index versions scikit-learn
pip index versions sentence-transformers
```

## Key Insight

**Your labeled data is more valuable than any library.**

With 500+ rejected examples, you have a goldmine of negative patterns. The immediate highest-ROI action is:

1. Load rejected-leads JSON files
2. Find terms that appear frequently in rejected but rarely in qualified
3. Add those as exclusion terms
4. Repeat for positive signals

This is ML (learning from data) without the ML infrastructure overhead.

---

*Stack research completed: 2026-01-18*
*Confidence: MEDIUM overall (tool limitations prevented version verification)*
