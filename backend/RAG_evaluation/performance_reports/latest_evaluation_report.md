# RAG Golden Set Evaluation Quality Gate Report

- **Date:** 2026-09-04 05:26:27 UTC
- **Knowledge Base:** `Kenya Drylands`
- **Dataset:** `/app/RAG_evaluation/example_csv_inputs/kenya_drylands_short_evaluation.csv`
- **Total Queries:** `2`
- **Average Latency:** `11.33s`
- **Quality Gate Status:** **PASSED ✅**

---

## 1. Metric Assertions & Quality Gates

| Metric | Score | Target | Status |
|---|:---:|:---:|:---:|
| **Faithfulness** | `1.0000` | `>= 0.85` | PASS ✅ |
| **Answer Relevancy** | `0.9107` | `>= 0.85` | PASS ✅ |
| **Context Precision (Groundedness)** | `1.0000` | `>= 0.90` | PASS ✅ |
| **Context Recall** | `0.8398` | `N/A` | INFO ℹ️ |
| **Answer Similarity** | `0.9201` | `N/A` | INFO ℹ️ |
| **Answer Correctness** | `0.3253` | `N/A` | INFO ℹ️ |

---

## 2. Executive Summary
- **Faithfulness Target ($\ge 0.85$):** `PASS`
- **Answer Relevancy Target ($\ge 0.85$):** `PASS`
- **Context Groundedness Target ($\ge 0.9$):** `PASS`

Report generated automatically by `TASK-OPS-501` Headless Evaluation Harness.
