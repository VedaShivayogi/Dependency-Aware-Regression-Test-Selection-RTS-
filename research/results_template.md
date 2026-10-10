# Results Template & Evaluation Formulations

## 1. Metric Definitions & Mathematical Formulas

### A. Test Selection Ratio
\[ \text{Selection Ratio} = \frac{|T_{\text{selected}}|}{|T_{\text{total}}|} \]

### B. Execution Time Savings (%)
\[ \text{Time Reduction (\%)} = \frac{T_{\text{full}} - T_{\text{selected}}}{T_{\text{full}}} \times 100 \]

### C. Regression Failure Detection Rate (%)
\[ \text{Detection Rate (\%)} = \frac{|\text{Failures}_{\text{selected}} \cap \text{Failures}_{\text{full}}|}{|\text{Failures}_{\text{full}}|} \times 100 \]

### D. Missed Regressions Count
\[ \text{Missed Regressions} = |\text{Failures}_{\text{full}}| - |\text{Failures}_{\text{selected}}| \]

### E. Precision & Recall
\[ \text{Precision} = \frac{|T_{\text{selected}} \cap T_{\text{affected}}|}{{|T_{\text{selected}}|}} \]
\[ \text{Recall} = \frac{|T_{\text{selected}} \cap T_{\text{affected}}|}{{|T_{\text{affected}}|}} \]

---

## 2. Experimental Summary Results Template

| Scenario ID | Selection Mode | Selected / Total Tests | Selection Ratio (%) | Exec Time (s) | Time Reduction (%) | Regressions Detected | Detection Rate (%) | Missed Regressions | Precision | Recall |
|---|---|---|---|---|---|---|---|---|---|---|
| `ECOM-BUGGY-01` | `full` | 6 / 6 | 100.0% | 2.037s | 0.0% | 2 / 2 | 100.0% | 0 | 0.33 | 1.00 |
| `ECOM-BUGGY-01` | `changed_file` | 6 / 6 | 100.0% | 1.750s | 22.5% | 2 / 2 | 100.0% | 0 | 0.33 | 1.00 |
| `ECOM-BUGGY-01` | `dependency_aware` | 6 / 6 | 100.0% | 1.603s | 29.0% | 2 / 2 | 100.0% | 0 | 0.33 | 1.00 |
