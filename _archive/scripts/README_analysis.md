# Statistical Significance Analysis

## Overview

The `analyze_significance.py` script performs statistical tests to determine if increasing k (number of IR variants) significantly improves proof success rates.

## Statistical Tests Used

### 1. McNemar's Test (Primary)
- **Purpose**: Tests for significant difference in paired binary outcomes
- **Use case**: Compare k=1 vs k>1 on the same (theorem, seed) pairs
- **Why appropriate**: Same theorems/seeds tested with different k values (paired data)
- **Interpretation**: 
  - p < 0.05 → Significant improvement
  - Effect size: absolute improvement percentage

### 2. Spearman Correlation (Trend Analysis)
- **Purpose**: Tests if success rate increases monotonically with k
- **Use case**: Check if more variants consistently help
- **Interpretation**: 
  - Positive correlation + p < 0.05 → Monotonic increase confirmed

### 3. Per-Theorem Analysis
- **Purpose**: Count how many theorems benefit from k-variants
- **Use case**: Understand which problems benefit most

## Usage

### Basic Example

```bash
# Compare k=1 vs k=8 experiments
python scripts/analyze_significance.py \
  --log-dirs \
    outputs/logs/ir_search_v0/<hash_k1>/ \
    outputs/logs/ir_search_v0/<hash_k8>/ \
  --k-values 1 8
```

### Multiple k Values

```bash
# Compare k=1, k=2, k=4, k=8
python scripts/analyze_significance.py \
  --log-dirs \
    outputs/logs/ir_search_v0/<hash_k1>/ \
    outputs/logs/ir_search_v0/<hash_k2>/ \
    outputs/logs/ir_search_v0/<hash_k4>/ \
    outputs/logs/ir_search_v0/<hash_k8>/ \
  --k-values 1 2 4 8 \
  --output results.json
```

## Finding Config Hashes

Each experiment run creates a log directory with a config hash. To find which hash corresponds to which k value:

```bash
# List all experiment runs
find outputs/logs/ir_search_v0 -name "events.jsonl" -exec dirname {} \;

# Check config hash (first 12 chars of SHA256 of config)
# You can also check the run_start event in events.jsonl:
cat outputs/logs/ir_search_v0/*/events.jsonl | grep run_start | jq .cfg_hash
```

## Interpreting Results

### Success Criteria for Publication

**Minimum for significance:**
- p-value < 0.05 (McNemar's test)
- Absolute improvement ≥ 10%
- At least 100 (theorem, seed) pairs

**Strong results:**
- p-value < 0.01
- Absolute improvement ≥ 15-20%
- Monotonic increase confirmed (Spearman p < 0.05)
- Majority of theorems benefit

### Example Output Interpretation

```
k=1 vs k=8:
  p-value = 0.0032  ✓ SIGNIFICANT
  Absolute improvement: 18.5%
  
  → This means: k=8 solves 18.5% more (theorem, seed) pairs than k=1
  → With p < 0.05, this is statistically significant
  → Ready for publication if effect size is meaningful
```

## Statistical Power

To ensure adequate statistical power:
- **Minimum**: 50-100 (theorem, seed) pairs
- **Recommended**: 200+ pairs
- **Multiple seeds**: Use 3-5 seeds per theorem for robustness

## Common Issues

**Problem**: "No valid log directories found"
- **Solution**: Check that log directories exist and contain events.jsonl

**Problem**: "p-value = 1.0" (not significant)
- **Possible causes**:
  - Too few samples
  - No actual improvement
  - Need more experiments

**Problem**: "discordant_pairs = 0"
- **Meaning**: All pairs have same outcome (both succeed or both fail)
- **Solution**: Need more diverse problems or better model

## Advanced Analysis

For deeper analysis, you can:
1. Filter by problem type (algebra, number theory, etc.)
2. Analyze by error type (timeout, type_error, etc.)
3. Compare compute cost vs. success rate
4. Bootstrap confidence intervals for effect size

See the script source for details on extending the analysis.

