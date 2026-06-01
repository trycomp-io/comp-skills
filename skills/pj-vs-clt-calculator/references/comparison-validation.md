# PJ vs CLT Calculator - Validation Methodology

This document describes the complete validation process to ensure the skill's calculations match the official simulator with acceptable precision.

---

## 1. Validation Overview

### 1.1 Purpose

Validate that the Python CLI implementation produces results **identical or nearly identical** to the official HTML simulator for all calculation scenarios.

### 1.2 Acceptance Criteria

**Primary criteria:**
- Difference < R$ 1,00 for all monetary values
- Difference < 0,01% for percentage comparisons
- Rounding matches simulator (2 decimal places)

**Secondary criteria:**
- Consistent behavior across edge cases
- Same treatment of benefits and costs
- Identical FGTS inclusion/exclusion logic

### 1.3 Reference Simulator

**Location:** `C:\Users\bruno\Downloads\simuladorpj.txt`
**Type:** HTML with embedded JavaScript
**Usage:** Open in browser for manual validation

---

## 2. Validation Process

### 2.1 Step-by-Step Manual Validation

**For each test case:**

1. **Open simulator in browser**
   ```bash
   # Open simuladorpj.txt in your default browser
   # Or copy content to a .html file and open
   ```

2. **Input test values**
   - Fill all form fields with test case values
   - Ensure checkboxes match (FGTS inclusion)
   - Select correct number of invoices (12 or 13)

3. **Capture simulator output**
   - Take screenshot of complete results
   - Copy numerical values to text file
   - Note any warnings or special messages

4. **Run CLI with same inputs**
   ```bash
   python3 pj_clt_calculator.py \
       --mode calc \
       --direction clt-to-pj \
       --clt-salary 10000 \
       --pj-aliquota 6 \
       --include-fgts
   ```

5. **Compare outputs line by line**
   - CLT Net Monthly
   - CLT Annualized
   - CLT FGTS Annual
   - CLT Total Target
   - PJ Monthly Gross Required
   - PJ Annual Gross
   - PJ Annual Tax
   - PJ Net Annual

6. **Calculate differences**
   ```
   Diff = |Simulator Value - CLI Value|
   ```

7. **Document results**
   - Record in `examples.md`
   - Include pass/fail status
   - Note any discrepancies

### 2.2 Automated Validation (Optional)

For high-confidence validation, extract JavaScript calculation logic and run headless browser tests:

```python
from selenium import webdriver
import json

def validate_with_simulator(test_case):
    # Load simulator in headless browser
    driver = webdriver.Chrome(options=headless_options)
    driver.get(f"file://{simulator_path}")

    # Input values programmatically
    driver.find_element_by_id("cltGrossSalary").send_keys(test_case["salary"])
    driver.find_element_by_id("pjAliquota").send_keys(test_case["aliquota"])
    # ... submit form

    # Extract results
    simulator_result = driver.find_element_by_id("cltToPjResult").text

    # Compare with CLI
    cli_result = run_cli(test_case)

    return compare_results(simulator_result, cli_result)
```

**Note:** This requires Selenium setup and is optional for the current implementation.

---

## 3. Test Case Coverage

### 3.1 Mandatory Test Categories

**Basic CLT → PJ:**
- Minimum wage scenarios
- Mid-range salaries (R$ 5.000 - R$ 10.000)
- High salaries (above INSS ceiling)

**Basic PJ → CLT:**
- Low billing (R$ 5.000 - R$ 10.000)
- Medium billing (R$ 10.000 - R$ 20.000)
- High billing (R$ 20.000+)

**With Benefits/Costs:**
- VR/VA monthly allowances
- Annual bonuses
- Other monthly benefits
- PJ accounting costs
- PJ other costs

**Edge Cases:**
- Exactly at INSS ceiling (R$ 7.786,02)
- Exactly at IRPF bracket boundaries
- Zero benefits/costs
- 12 vs 13 invoices
- With/without FGTS

**Different Aliquotas:**
- 4% (Anexo I low)
- 6% (Anexo III common)
- 8.21% (Anexo V)
- 15% (higher rates)

### 3.2 Minimum Test Suite

**10 Mandatory Test Cases:**

| # | Category | Inputs | Expected Validation |
|---|----------|--------|---------------------|
| 1 | CLT→PJ Basic | CLT R$ 5.000, Aliq 6% | < R$ 1 diff |
| 2 | CLT→PJ High | CLT R$ 20.000, Aliq 8.21% | < R$ 1 diff |
| 3 | CLT→PJ No FGTS | CLT R$ 1.412, Aliq 4%, no FGTS | < R$ 1 diff |
| 4 | CLT→PJ Benefits | CLT R$ 7.786,02, VR R$ 600, Aliq 6% | < R$ 1 diff |
| 5 | PJ→CLT Basic | PJ R$ 10.000, Aliq 6% | < R$ 1 diff |
| 6 | PJ→CLT Benefits | PJ R$ 15.000, VR R$ 600, Bonus R$ 5.000, Aliq 6% | < R$ 1 diff |
| 7 | CLT→PJ 13 Invoices | CLT R$ 10.000, Aliq 6%, 13 invoices | < R$ 1 diff |
| 8 | CLT→PJ No FGTS | CLT R$ 10.000, Aliq 6%, no FGTS | < R$ 1 diff |
| 9 | PJ→CLT High Aliq | PJ R$ 20.000, Aliq 15% | < R$ 1 diff |
| 10 | Full Complexity | All benefits + costs, CLT R$ 12.000 | < R$ 1 diff |

---

## 4. Debugging Discrepancies

### 4.1 Common Causes of Differences

**Rounding errors:**
- Simulator rounds at different stages
- Python float precision differs from JavaScript
- **Solution:** Ensure rounding after each calculation step

**Tax table mismatches:**
- Outdated tables (2023 vs 2024/2025)
- Incorrect deduction values
- **Solution:** Verify tables match exactly

**Factor 13.33 precision:**
- JavaScript: `13 + (1/3)` = 13.333333...
- Python: `13 + (1/3)` = 13.333333333333334
- **Solution:** Use same expression, accept minor float differences

**FGTS calculation:**
- Applied to wrong base (monthly vs annualized)
- Rate error (0.08 vs 8%)
- **Solution:** Verify formula: `gross * 13.333 * 0.08`

**Binary search convergence:**
- Not converging within tolerance
- Initial bounds too narrow
- **Solution:** Increase max iterations, widen initial range

### 4.2 Debugging Workflow

```
1. Identify which value differs (e.g., "IRPF amount")

2. Isolate the calculation
   python3 -c "from pj_clt_calculator import calculate_irpf; \
               print(calculate_irpf(10000, 908.85))"

3. Compare with manual calculation
   Taxable Base: 10000 - 908.85 = 9091.15
   IRPF: (9091.15 × 0.275) - 896 = 1604.07

4. Check simulator JavaScript
   Open browser console, run:
   > calculateIrpf(10000, 908.85)
   > 1604.0662499999999

5. Identify rounding difference
   Python: 1604.07 (rounded)
   JS: 1604.0662... (not rounded yet)

6. Verify final output matches after rounding
   Both should display: R$ 1.604,07
```

### 4.3 Acceptable vs Unacceptable Differences

**✓ Acceptable:**
```
Simulator: R$ 10.757,03
CLI: R$ 10.757,39
Difference: R$ 0,36 ✓ (< R$ 1,00)
```

**✓ Acceptable (floating point):**
```
Simulator: 13.333333333333334
CLI: 13.333333333333332
Difference: 0.000000000000002 ✓ (negligible)
```

**✗ Unacceptable:**
```
Simulator: R$ 10.757,03
CLI: R$ 10.850,00
Difference: R$ 92,97 ✗ (>> R$ 1,00)
→ Bug in calculation, must fix
```

**✗ Unacceptable (systematic):**
```
All test cases off by ~5%
→ Likely wrong formula or tax table
```

---

## 5. Documentation Requirements

### 5.1 Test Case Documentation Format

Each test case must be documented in `examples.md` with:

```markdown
## Test Case #N: [Description]

**Category:** [CLT→PJ / PJ→CLT] [Basic / With Benefits / Edge Case]

**Inputs:**
- CLT Gross Salary: R$ X.XXX,XX
- PJ Aliquota: X%
- PJ Invoices: [12 / 13]
- VR/VA Monthly: R$ X,XX
- Annual Bonus: R$ X.XXX,XX
- Other Benefits Monthly: R$ X,XX
- Accounting Monthly: R$ X,XX
- Other Costs Monthly: R$ X,XX
- Include FGTS: [Yes / No]

**Simulator Output:**
```
[Paste or screenshot of simulator results]
```

**CLI Command:**
```bash
python3 pj_clt_calculator.py [full command]
```

**CLI Output:**
```
[Paste CLI results]
```

**Comparison:**
| Metric | Simulator | CLI | Difference | Status |
|--------|-----------|-----|------------|--------|
| CLT Net Monthly | R$ X,XX | R$ X,XX | R$ X,XX | ✓ |
| PJ Required Monthly | R$ X,XX | R$ X,XX | R$ X,XX | ✓ |
| ... | ... | ... | ... | ... |

**Overall Status:** ✓ PASS / ✗ FAIL

**Notes:** [Any observations, edge cases, or special considerations]
```

### 5.2 Screenshot Guidelines

**When to take screenshots:**
- Initial test case setup in simulator
- Final results display
- Any error messages or warnings

**What to capture:**
- Entire calculator interface
- All input fields visible
- Complete results section
- Browser window showing URL/file path

**Naming convention:**
```
test_case_XX_[direction]_[description].png
Examples:
- test_case_01_clt_to_pj_basic.png
- test_case_05_pj_to_clt_with_benefits.png
```

---

## 6. Continuous Validation

### 6.1 When to Re-validate

**Mandatory re-validation:**
- Any change to calculation functions
- Tax table updates (annual)
- Formula modifications
- Rounding logic changes

**Optional re-validation:**
- CLI interface changes (no calculation impact)
- Output formatting changes
- Documentation updates

### 6.2 Regression Testing

Maintain a test script that runs all 10 mandatory cases:

```bash
#!/bin/bash
# regression_test.sh

echo "Running PJ vs CLT Regression Tests..."

# Test Case 1
python3 pj_clt_calculator.py \
    --mode calc --direction clt-to-pj \
    --clt-salary 5000 --pj-aliquota 6 \
    | grep "Required PJ Monthly" > test_1_result.txt

# Test Case 2
python3 pj_clt_calculator.py \
    --mode calc --direction clt-to-pj \
    --clt-salary 20000 --pj-aliquota 8.21 \
    | grep "Required PJ Monthly" > test_2_result.txt

# ... (all 10 tests)

# Compare with expected results
diff test_1_result.txt expected/test_1.txt || echo "FAIL: Test 1"
diff test_2_result.txt expected/test_2.txt || echo "FAIL: Test 2"
# ...

echo "Regression tests complete."
```

**Expected results directory:**
```
expected/
├── test_1.txt  # CLT R$ 5.000 → PJ: R$ 4.378,52
├── test_2.txt  # CLT R$ 20.000 → PJ: R$ 19.945,23
├── ...
└── test_10.txt
```

---

## 7. Validation Checklist

Before considering validation complete:

### 7.1 Functional Validation

- [ ] All 10 mandatory test cases pass (< R$ 1,00 difference)
- [ ] CLT→PJ calculations match simulator
- [ ] PJ→CLT calculations match simulator
- [ ] Benefits correctly added to CLT total
- [ ] Costs correctly subtracted from PJ net
- [ ] FGTS inclusion/exclusion works correctly
- [ ] 12 vs 13 invoices calculated correctly
- [ ] Different aliquotas (4%, 6%, 8.21%, 15%) work

### 7.2 Edge Case Validation

- [ ] Salary at INSS ceiling (R$ 7.786,02) handled correctly
- [ ] Salary above INSS ceiling capped at R$ 908,85
- [ ] Zero benefits/costs work correctly
- [ ] Minimum wage scenarios work
- [ ] Very high salaries (R$ 50.000+) work

### 7.3 Precision Validation

- [ ] All monetary values rounded to 2 decimals
- [ ] Brazilian format (R$ 1.234,56) displayed correctly
- [ ] No floating point display errors (e.g., 1604.0699999)
- [ ] Percentages displayed correctly (6% not 0.06)

### 7.4 Documentation Validation

- [ ] All test cases documented in `examples.md`
- [ ] Screenshots captured for key test cases
- [ ] Comparison tables complete
- [ ] Pass/fail status clear for each case
- [ ] Notes explain any edge cases

---

## 8. Known Limitations

### 8.1 Simulator Limitations

**JavaScript precision:**
- Limited to ~15 decimal places
- May show slight differences in intermediate calculations

**Browser differences:**
- Firefox vs Chrome may render numbers slightly differently
- Doesn't affect validation (use same browser consistently)

**Manual input:**
- Human error when copying values
- Double-check all inputs before validation

### 8.2 Python CLI Limitations

**Float representation:**
- Python floats have 53-bit precision
- Can differ from JavaScript in last decimal places
- Mitigated by rounding to 2 decimals

**Terminal encoding:**
- Windows CP1252 can't display all Unicode
- Use ASCII-safe characters ([OK] not ✓)

**Binary search:**
- May not converge to exact value
- Acceptable within R$ 1,00 tolerance
- Typical convergence: R$ 0,36 - R$ 0,80

### 8.3 Tax Law Changes

**Annual updates:**
- INSS ceiling changes every year
- IRPF brackets adjust for inflation
- Simulator and CLI must be updated together

**Current version valid for:**
- Tax year: 2024/2025
- INSS ceiling: R$ 7.786,02
- Max contribution: R$ 908,85
- IRPF brackets: As of 2024

---

## 9. Troubleshooting Guide

### 9.1 "Results differ by R$ 10+"

**Likely cause:** Wrong tax table or formula

**Debug steps:**
1. Verify INSS_TABLE matches simulator exactly
2. Verify IRPF_TABLE matches simulator exactly
3. Check FACTOR_13_33 = 13.333... not 13
4. Verify FGTS_RATE = 0.08 not 8

### 9.2 "Binary search not converging"

**Likely cause:** Initial bounds too narrow or tolerance too strict

**Debug steps:**
1. Increase max_iterations from 100 to 200
2. Widen initial range: `low = 500, high = pj_billing * 2`
3. Relax tolerance from R$ 1,00 to R$ 2,00 temporarily
4. Add debug prints to show iteration progress

### 9.3 "IRPF calculation off by R$ 100+"

**Likely cause:** Not subtracting INSS before calculating IRPF

**Debug steps:**
1. Verify: `taxable_base = gross_salary - inss`
2. Ensure INSS calculated first
3. Check IRPF uses taxable_base, not gross_salary

### 9.4 "Results match but formatting wrong"

**Likely cause:** Format function not using Brazilian style

**Debug steps:**
1. Verify format_currency() swaps separators
2. Check: 1234.56 → "1.234,56" not "1,234.56"
3. Ensure "R$ " prefix included

---

## 10. Validation Sign-off

### 10.1 Validation Statement

```
I, [Your Name], have validated the PJ vs CLT Calculator
against the official simulator on [Date].

Test Results:
- Total test cases: 10
- Passed: __/10
- Failed: __/10
- Maximum difference: R$ __,__
- Average difference: R$ __,__

Conclusion: [APPROVED / NEEDS WORK]

Edge cases verified: [Yes / No]
Documentation complete: [Yes / No]
Ready for production: [Yes / No]

Signature: ________________
Date: ____________________
```

### 10.2 Approval Criteria

**Ready for production if:**
- All 10 mandatory tests pass
- Maximum difference < R$ 1,00
- No systematic bias detected
- Documentation complete
- Edge cases handled

**Needs work if:**
- Any test fails with > R$ 1,00 difference
- Systematic bias (all results consistently high/low)
- Missing documentation
- Edge cases crash or error

---

**Last Updated:** 2026-01-07
**Validator:** [Pending]
**Status:** Validation in progress
**Next Review:** Upon any calculation logic change
