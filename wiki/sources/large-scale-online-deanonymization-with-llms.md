---
title: Large-scale online deanonymization with LLMs
tags:
  - LLM
  - deanonymization
  - privacy
  - security
  - online-identity
  - natural-language-processing
related:
  - Large Language Model
  - Deanonymization
  - Pseudonymity
  - Semantic Embeddings
  - Privacy Engineering
  - Hacker News
  - Reddit
  - LinkedIn
---

## Overview

This paper demonstrates that [[Large Language Model]]s (LLMs) enable automated, large-scale [[deanonymization]] of pseudonymous online users. Researchers show that an LLM agent with full Internet access can re-identify [[Hacker News]] users and [[Anthropic Interviewer]] participants at high precision using only pseudonymous profiles and conversation histories—matching what would require hours of manual investigation by a dedicated human. Unlike classical deanonymization attacks (such as those on the [[Netflix Prize]] dataset) that required structured data, this approach operates directly on raw, unstructured text across arbitrary platforms.

## Attack Methodology

The paper describes attacks for both [[open-world]] and [[closed-world]] settings:

### Open-World Setting
With full Internet access, the agent can browse the web to cross-reference pseudonymous profiles against public data to re-identify individuals.

### Closed-World Setting
Given two databases of pseudonymous individuals containing unstructured text written by or about each person, the attack pipeline uses LLMs to:
1. **Extract identity-relevant features** from text
2. **Search for candidate matches** via [[semantic embeddings]]
3. **Reason over top candidates** to verify matches and reduce false positives

## Datasets and Evaluation

The researchers constructed three datasets with known ground-truth to evaluate performance:

- **Cross-Platform (Hacker News → LinkedIn):** Matches Hacker News accounts to [[LinkedIn]] profiles using cross-platform references appearing in the profiles
- **Cross-Community (Reddit):** Matches users across different [[Reddit]] movie discussion communities
- **Temporal Split (Reddit):** Splits a single user's Reddit history at a point in time to create two separate pseudonymous profiles to be matched

## Key Results

LLM-based methods substantially outperform classical baselines:

- Achieved **up to 68% recall at 90% precision**
- Best non-LLM method achieved **near 0%** under the same conditions
- Works directly on raw user content without requiring structured data schemas

## Implications

The findings indicate that [[pseudonymity]] no longer provides reliable protection through "practical obscurity." The authors conclude that "the practical obscurity protecting pseudonymous users online no longer holds and that threat models for online privacy need to be reconsidered."

This research suggests that traditional assumptions about [[online privacy]] and [[identity protection]] must be updated to account for LLM-based inference capabilities that can aggregate disparate unstructured text traces across the internet to uniquely identify individuals.

---

## Backlinks

- [[concepts/ai-safety-frameworks|AI Safety Frameworks]]
