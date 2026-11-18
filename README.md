# Diagnosing the Undiagnosable: Automated Root Cause Analysis for Large-Scale LLM Failures

**Companion code and practical exercises for _Diagnosing the Undiagnosable: Automated Root Cause Analysis for Large-Scale LLM Failures_.**

**Book author:** Devin Hayes

## About the book

This book provides a comprehensive, hands-on guide to designing, deploying, and operationalizing AI-driven automated root cause analysis (RCA) systems tailored for large-scale, enterprise-grade LLM (large language model) production environments. It delivers actionable blueprints, reference architectures, and real-world case studies to address LLM-specific failure modes such as prompt failures, hallucinations, model drift, and data pipeline issues. Readers will learn practical strategies for integrating RCA with existing monitoring and incident response workflows, leveraging AI/ML techniques to automate diagnosis, and implementing remediation pipelines that enhance system reliability and uptime. The book includes companion code and modular frameworks adaptable to heterogeneous enterprise infrastructures, while addressing the challenges of proprietary systems, evolving LLM architectures, and limited access to production failure data.

## Who this is for

Enterprise AI/ML platform engineers, site reliability engineers (SREs), and technical leads responsible for deploying, maintaining, and troubleshooting large-scale LLM (large language model) systems in production environments.

## What you will find here

This repository accompanies the book with chapter-specific implementation projects, examples, and reproducible exercises. Each implementation folder has its own README with the setup and execution instructions relevant to that chapter.

The book provides the explanations and context; this repository provides the companion implementation material.

## Chapter guide

- **Chapter 1: Why LLM Incidents Defy Traditional Root Cause Analysis** — Reading chapter; no separate implementation required
- **Chapter 2: Anatomy of Large-Scale LLM Production Environments** — Reading chapter; no separate implementation required
- **Chapter 3: From Incidents to Root Causes: An LLM-Specific Failure Taxonomy** — Reading chapter; no separate implementation required
- **Chapter 4: Designing an Automated RCA Architecture for LLM Systems** — Reading chapter; no separate implementation required
- **Chapter 5: Instrumenting LLM Systems for High-Fidelity RCA Signals** — [Companion implementation](chapter-05/)
- **Chapter 6: Signal Collection and Event Correlation at Scale** — [Companion implementation](chapter-06/)
- **Chapter 7: Detecting and Localizing LLM Failures in Real Time** — [Companion implementation](chapter-07/)
- **Chapter 8: AI-Driven Root Cause Hypothesis Generation** — [Companion implementation](chapter-08/)
- **Chapter 9: Diagnosing Prompt, Policy, and Hallucination Failures** — [Companion implementation](chapter-09/)
- **Chapter 10: Diagnosing Model Drift, Routing, and Performance Regressions** — [Companion implementation](chapter-10/)
- **Chapter 11: Diagnosing Data, Retrieval, and Tooling Pipeline Failures** — [Companion implementation](chapter-11/)
- **Chapter 12: Closing the Loop: Automated Remediation and Guardrails** — [Companion implementation](chapter-12/)
- **Chapter 13: Operating and Evolving an Automated RCA System** — Reading chapter; no separate implementation required
- **Chapter 14: Adapting to Evolving LLM Architectures and Enterprise Constraints** — Reading chapter; no separate implementation required
- **Chapter 15: End-to-End Case Studies: Automated RCA for Real LLM Incidents** — [Companion implementation](chapter-15/)
- **Chapter 16: Putting It All Together: A Blueprint for Your Organization** — Reading chapter; no separate implementation required

## Getting started

1. Read the chapter you want to explore in the book.
2. Open the corresponding `chapter-XX/` folder above, where an implementation is available.
3. Follow that folder’s `README.md` for prerequisites, setup, configuration, and commands.
4. Run the chapter’s examples and compare the results with the discussion in the book.

Different chapters may have different dependencies and environment requirements; use the instructions in each chapter folder rather than assuming one setup works for all projects.

## Repository structure

```text
README.md                  # This repository overview
chapter-XX/                # Chapter-specific companion projects (where provided)
  README.md                # Setup and execution instructions for that chapter
  ...                      # Source code, tests, and other chapter assets
```

## Notes

- The chapter folders are intended to complement the book, not replace it.
- Follow each chapter README before running code, especially when external services or API credentials are involved.
- Keep secrets and local environment files out of version control.

## Book and repository

- **Companion repository:** https://github.com/bookauthority/automated-rca-llm-failures
- **Book:** Diagnosing the Undiagnosable: Automated Root Cause Analysis for Large-Scale LLM Failures

---

This README is generated from the book’s approved chapter plan. Chapter-specific instructions live in their respective folders.
