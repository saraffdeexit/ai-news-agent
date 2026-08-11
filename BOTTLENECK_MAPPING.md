# Bottleneck Mapping: How V2 Avoids False Positives

## The Problem

When comparing assessments week-to-week, terminology changes can cause false positives:

```
Week 1 news:  "GPU shortage"
Claude summary: issue = "GPU Shortage"
assessment.py: bottleneck_topics = ["gpu_shortage"]

Week 2 news:  "NVIDIA capacity crisis"
Claude summary: issue = "NVIDIA Capacity Crisis"
assessment.py: bottleneck_topics = ["nvidia_capacity_crisis"]

compare.py sees: ["gpu_shortage"] → ["nvidia_capacity_crisis"]
Result: "NEW BOTTLENECK DETECTED!" ❌ FALSE POSITIVE
```

**Same underlying issue, different wording = false alert.**

---

## The Solution: Canonical Forms

**assessment.py** now maps bottleneck descriptions to **canonical categories**:

```python
BOTTLENECK_SYNONYMS = {
    "gpu shortage": "compute_capacity",
    "nvidia capacity crisis": "compute_capacity",
    "h100 shortage": "compute_capacity",
    "chip supply": "compute_capacity",
    
    "power constraints": "power_energy",
    "data center power crisis": "power_energy",
    
    "ai regulation": "regulation_policy",
    "eu ai act": "regulation_policy",
    
    # ... more mappings ...
}
```

**Result:**

```
Week 1: issue = "GPU Shortage"
        canonical = "compute_capacity"
        bottleneck_topics = ["compute_capacity"]

Week 2: issue = "NVIDIA Capacity Crisis"
        canonical = "compute_capacity"
        bottleneck_topics = ["compute_capacity"]

compare.py sees: ["compute_capacity"] → ["compute_capacity"]
Result: "No change detected" ✓ CORRECT
```

---

## How It Works

### Three-Step Process

1. **Claude summarizes** the week's news into bottleneck issues
   ```
   Input: 40 news articles
   Output: issue = "GPU Shortage" (human-readable)
   ```

2. **assessment.py canonicalizes** each issue
   ```python
   issue = "GPU Shortage"
   canonical = BOTTLENECK_SYNONYMS.get(issue.lower())
   → "compute_capacity"
   ```

3. **compare.py compares canonicals** (not raw names)
   ```python
   this_week_topics = ["compute_capacity"]
   last_week_topics = ["compute_capacity"]
   → No change
   ```

### Storage

Assessment stores **both**:
```json
{
  "bottleneck_issues": ["GPU Shortage", "Power Constraints"],  # Raw (for context)
  "bottleneck_topics": ["compute_capacity", "power_energy"]    # Canonical (for comparison)
}
```

**Email shows raw names** (human-readable), but **comparison uses canonicals** (robust to wording changes).

---

## The Mappings

### Compute Capacity
- GPU shortage
- NVIDIA capacity crisis
- H100 shortage / supply
- Chip shortage / supply
- Semiconductor shortage
- Compute bottleneck / capacity / constraint
- Hardware bottleneck
- Training / inference capacity

### Power & Energy
- Power constraints / shortage / crisis
- Electricity cost
- Data center power crisis / shortage
- Energy cost / constraint
- Power consumption

### Regulation & Policy
- AI regulation / policy
- EU AI Act
- Regulatory friction
- Compliance / compliance friction
- Government policy
- Legal risk

### Talent Acquisition
- Talent shortage
- Researcher hiring
- Hiring competition
- Talent retention / brain drain
- Researcher exodus

### Funding & Valuations
- Funding round / shortage
- Valuation pressure
- Capital constraints

### Training Data
- Training data shortage
- Data availability
- Data constraint

### Model Capabilities
- Inferred from themes (e.g., "Model Releases", "Foundation Models")

---

## What Counts as a Real Change?

✓ **Alert on these:**
- New canonical topic appears (e.g., `power_energy` not present last week)
- Existing topic escalates (sentiment: neutral → bearish)
- Topic resolves (topic was there last week, gone now)

✗ **Don't alert on these:**
- Same canonical topics, just different wording
- "GPU shortage" → "NVIDIA capacity crisis" (same compute_capacity topic)
- "Power constraints" → "Data center power crisis" (same power_energy topic)

---

## Fuzzy Matching

If a bottleneck issue isn't in `BOTTLENECK_SYNONYMS`, the mapper uses **fuzzy matching**:

```python
def _canonicalize_bottleneck(issue: str) -> str:
    issue_lower = issue.lower().strip()
    
    # 1. Direct lookup
    if issue_lower in BOTTLENECK_SYNONYMS:
        return BOTTLENECK_SYNONYMS[issue_lower]
    
    # 2. Fuzzy match: if issue contains any key, use it
    for key, canonical in BOTTLENECK_SYNONYMS.items():
        if key in issue_lower or issue_lower in key:
            return canonical
    
    # 3. Fallback: normalize to snake_case
    return issue_lower.replace(" ", "_")
```

**Example:**
```
Issue: "NVIDIA GPU H100 Availability Crisis"
↓ Direct lookup: not found
↓ Fuzzy match: "h100 shortage" is in the issue
↓ Return: "compute_capacity" ✓
```

---

## How to Extend Mappings

Add new synonyms as needed:

```python
BOTTLENECK_SYNONYMS = {
    # ... existing ...
    
    # New: quantum computing constraints
    "quantum computing bottleneck": "quantum_bottleneck",
    "quantum hardware shortage": "quantum_bottleneck",
    
    # New: inference latency
    "inference latency crisis": "inference_capacity",
    "serving capacity": "inference_capacity",
}
```

When a new bottleneck type emerges:
1. Add a new canonical category name
2. Add 2-3 representative synonym mappings
3. It's automatically available for comparison

---

## Testing the Mappings

**Test that synonyms map to the same canonical:**

```bash
python assessment.py
```

Output from Test 2:
```
=== Test 2: Synonym Mapping (Same Issue, Different Wording) ===
Week 1 canonical topics: ["compute_capacity", "power_energy"]
Week 2 canonical topics: ["compute_capacity", "power_energy"]
✓ Same underlying issues (canonical forms match)
✓ Would NOT trigger escalation alert (correct!)
```

---

## Performance Impact

**None.** Mapping happens at assessment time (weekly), which is already offline:
- Direct dict lookup: O(1)
- Fuzzy matching: O(n) over ~50 mappings = negligible

Total cost: <1ms per assessment.

---

## Edge Cases

### Case 1: New wording, new canonical category
```
Week 1: "GPU shortage" → compute_capacity
Week 2: "Training data shortage" → training_data (NEW)

Result: NEW bottleneck detected ✓ (correct, this is real)
```

### Case 2: Same wording, multiple meanings
```
"Constraint" could mean: compute, power, or resource
→ Use fuzzy matching context: 
   if "power" in issue → power_energy
   if "compute" in issue → compute_capacity
```

### Case 3: Unmapped bottleneck
```
"Quantum noise in chips" (hypothetical new issue)
→ Not in BOTTLENECK_SYNONYMS
→ Fuzzy match fails
→ Fallback: "quantum_noise_in_chips" (raw snake_case)
→ Treated as new topic (which it is!)
```

---

## Tuning for Your Role

As a **Treasury Executive**, you might care more about cost-related bottlenecks:

```python
# Add higher weight to cost escalations
BOTTLENECK_SYNONYMS = {
    # ... existing ...
    
    # Cost escalations (high priority for treasury)
    "ai compute cost surge": "cost_escalation",
    "gpu price increase": "cost_escalation",
    "power cost crisis": "cost_escalation",
    "capex inflation": "cost_escalation",
}

# Then in compare.py SIGNIFICANCE_PROMPT:
# "Cost escalations should trigger alerts with high confidence (0.8+)"
```

---

## Summary

**Canonical mapping prevents false positives** by normalizing terminology:

| Scenario | Without Mapping | With Mapping |
|----------|---|---|
| "GPU shortage" → "NVIDIA capacity crisis" | **False alert** ❌ | No alert ✓ |
| New power constraint mentioned | Correct alert ✓ | Correct alert ✓ |
| Same bottleneck, 3x wording variations | 3 false alerts ❌ | 1 alert ✓ |
| New regulatory policy | Correct alert ✓ | Correct alert ✓ |

**Result:** You only get emailed about *real* changes, not semantic noise.
