# Statistical Significance Analysis Guide

## Overview

This document explains how to prove statistical significance for the IR search experiments, specifically testing whether increasing k (number of IR variants) improves proof success rates.

## Experimental Design

**Hypothesis**: Increasing k_variants improves proof success rate under fixed compute.

**Experimental Setup**:
- Same theorems tested with different k values
- Same seeds used across k values (for paired comparison)
- Fixed: model, temperature, max_tokens, timeout
- Varied: k_variants (1, 2, 4, 8, 16, ...)

**Data Structure**:
- Each trial: (theorem_id, seed, k) → proved (boolean)
- Multiple seeds per theorem (typically 3-5)
- Multiple theorems (target: 100+)

## Statistical Tests

### 1. McNemar's Test (Primary Test)

**Why McNemar's Test?**
- Appropriate for **paired binary data**
- Same (theorem, seed) pairs tested with different k values
- Tests if the difference in success rates is statistically significant

**How it works**:
1. Build 2×2 contingency table:
   ```
                    k>1 succeeds  k>1 fails
   k=1 succeeds     [both]        [k=1 only]
   k=1 fails        [k>1 only]    [neither]
   ```

2. Only uses **discordant pairs** (where outcomes differ):
   - k=1 fails, k>1 succeeds → improvement
   - k=1 succeeds, k>1 fails → regression

3. Tests null hypothesis: P(improvement) = P(regression)

**Interpretation**:
- p < 0.05 → Significant improvement
- Effect size: `(k>1_only - k=1_only) / total_pairs`

**Example**:
```
Contingency table:
  [both fail] = 150
  [k=1 fails, k=8 succeeds] = 45  ← improvements
  [k=1 succeeds, k=8 fails] = 5    ← regressions
  [both succeed] = 50

McNemar's test:
  χ² = 32.0
  p-value = 0.0001  ✓ SIGNIFICANT
  Absolute improvement: 45/250 = 18%
```

### 2. Spearman Correlation (Trend Analysis)

**Purpose**: Test if success rate increases **monotonically** with k.

**Why Spearman?**
- Tests for monotonic relationship (not just linear)
- Robust to outliers
- Appropriate for ordinal k values

**Interpretation**:
- Positive correlation + p < 0.05 → Confirms monotonic increase
- Suggests that more variants consistently help

### 3. Per-Theorem Analysis

**Purpose**: Understand which problems benefit from k-variants.

**Metrics**:
- Theorems helped: k=1 fails, but k>1 succeeds (any seed)
- Theorems hurt: k=1 succeeds, but k>1 fails (all seeds)
- Theorems unchanged: Same outcome across k values

**Use case**: Identify problem types that benefit most.

## Running the Analysis

### Step 1: Run Experiments with Different k Values

```bash
# Run with k=1
python run.py --config configs/ir_search_k1.yaml

# Run with k=8
python run.py --config configs/ir_search_k8.yaml
```

**Important**: Use the same benchmark, seeds, and model settings across all k values.

### Step 2: Find Log Directories

Each experiment creates a log directory with a config hash:
```
outputs/logs/ir_search_v0/<cfg_hash>/events.jsonl
```

To find experiments:
```bash
# List all experiment runs
find outputs/logs/ir_search_v0 -name "events.jsonl" -exec dirname {} \;

# Check which k value (inspect config or events)
cat outputs/logs/ir_search_v0/*/events.jsonl | grep run_start | head -1 | jq .
```

### Step 3: Run Statistical Analysis

```bash
python scripts/analyze_significance.py \
  --log-dirs \
    outputs/logs/ir_search_v0/<hash_k1>/ \
    outputs/logs/ir_search_v0/<hash_k8>/ \
  --k-values 1 8 \
  --output results.json
```

### Step 4: Interpret Results

**Success Criteria for Publication**:

✅ **Minimum threshold**:
- p-value < 0.05 (McNemar's test)
- Absolute improvement ≥ 10%
- At least 100 (theorem, seed) pairs

✅ **Strong results**:
- p-value < 0.01
- Absolute improvement ≥ 15-20%
- Monotonic increase confirmed
- Majority of theorems benefit

## Example Analysis Workflow

### 1. Quick Validation (Pilot)

```bash
# Test on 20 theorems, k=1 vs k=4
# If no improvement, adjust strategy before full run
python run.py --config configs/ir_search_k1.yaml --limit 20
python run.py --config configs/ir_search_k4.yaml --limit 20

# Analyze
python scripts/analyze_significance.py \
  --log-dirs <hash_k1> <hash_k4> \
  --k-values 1 4
```

### 2. Full Experiment

```bash
# Run all k values on full benchmark
for k in 1 2 4 8; do
  # Edit config to set k_variants=$k
  python run.py --config configs/ir_search_k${k}.yaml
done

# Analyze all comparisons
python scripts/analyze_significance.py \
  --log-dirs <hash_k1> <hash_k2> <hash_k4> <hash_k8> \
  --k-values 1 2 4 8 \
  --output full_analysis.json
```

### 3. Reporting Results

**In paper, report**:
1. Success rates for each k
2. McNemar's test results (p-values, effect sizes)
3. Trend analysis (Spearman correlation)
4. Per-theorem breakdown
5. Statistical power (sample sizes)

**Example table**:
```
k   Success Rate  vs k=1 (p-value)  Absolute Improvement
1   45.2%         -                  -
2   52.1%         0.023              +6.9%
4   58.7%         0.001              +13.5%
8   63.4%         <0.001             +18.2%
```

## Statistical Power

**Sample Size Requirements**:

- **Minimum**: 50-100 (theorem, seed) pairs
- **Recommended**: 200+ pairs
- **For publication**: 300+ pairs

**Why multiple seeds?**
- Reduces variance
- More robust to model randomness
- Better statistical power

**Formula for power calculation**:
```
Power = 1 - β (type II error rate)
Target: Power ≥ 0.8 (80% chance of detecting true effect)
```

With 200 pairs and 15% improvement, you'll have adequate power (assuming α=0.05).

## Common Pitfalls

### 1. Multiple Comparisons

**Problem**: Testing many k values inflates false positive rate.

**Solution**: 
- Use Bonferroni correction: divide α by number of comparisons
- Or focus on primary comparison: k=1 vs k=8

### 2. Non-Independent Data

**Problem**: Multiple seeds per theorem are not independent.

**Solution**:
- Aggregate by theorem (best result across seeds)
- Or use mixed-effects models (advanced)

### 3. Selection Bias

**Problem**: Only reporting successful comparisons.

**Solution**:
- Report all k values tested
- Include negative results
- Be transparent about experimental choices

### 4. Effect Size vs. Statistical Significance

**Problem**: Significant but tiny improvement.

**Solution**:
- Report both p-value AND effect size
- Consider practical significance (≥10% improvement)
- Discuss cost-benefit (compute vs. success)

## Advanced Analysis

### Bootstrap Confidence Intervals

For more robust effect size estimates:

```python
import numpy as np
from scipy.stats import bootstrap

# Bootstrap the improvement rate
def improvement_statistic(data):
    # Calculate improvement from bootstrap sample
    return improvement_rate

ci = bootstrap((data,), improvement_statistic, confidence_level=0.95)
print(f"95% CI: [{ci.confidence_interval.low}, {ci.confidence_interval.high}]")
```

### Stratified Analysis

Analyze by problem type:

```python
# Group theorems by category
algebra_theorems = [...]
number_theory_theorems = [...]

# Run analysis separately for each category
# Identify which problem types benefit most
```

### Cost-Benefit Analysis

```python
# Compute cost (attempts × time) vs. benefit (success rate)
for k in [1, 2, 4, 8]:
    avg_attempts = mean(attempts for k=k)
    success_rate = ...
    cost_per_success = avg_attempts / success_rate
    print(f"k={k}: {cost_per_success} attempts per success")
```

## Reporting in Paper

### Methods Section

```
We compared proof success rates across k ∈ {1, 2, 4, 8} using the same 
theorem set and random seeds. For each (theorem, seed) pair, we recorded 
whether the proof succeeded (proved=True). We used McNemar's test to assess 
statistical significance of improvements, as it is appropriate for paired 
binary outcomes. We also computed Spearman correlation to test for 
monotonic increase in success rate with k.
```

### Results Section

```
Increasing k from 1 to 8 improved success rate from 45.2% to 63.4% 
(absolute improvement: 18.2%, McNemar's test: p < 0.001). The improvement 
was monotonic (Spearman ρ = 0.89, p < 0.001), with k=2, k=4, and k=8 all 
showing significant improvements over k=1 (all p < 0.05). Of 200 theorems, 
45 (22.5%) were solved by k=8 but not by k=1, while only 5 (2.5%) were 
solved by k=1 but not by k=8.
```

## References

- McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika, 12(2), 153-157.
- Agresti, A. (2018). An introduction to categorical data analysis. John Wiley & Sons.

