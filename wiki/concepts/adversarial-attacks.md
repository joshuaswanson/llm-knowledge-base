---
title: Adversarial Attacks
tags:
  - ai-safety
  - security
  - multimodal-ai
  - privacy
  - jailbreak
  - alignment
related:
  - AI Safety
  - AI Safety Frameworks
  - Modal Aphasia
  - Content Moderation
  - Deanonymization
  - Large Language Model
  - Cross-Modal Alignment
  - Red Teaming
  - Foundation Models
---

## Overview

[[Adversarial Attacks]] encompass techniques designed to manipulate [[AI systems]] into producing unintended outputs, bypass safety mechanisms, or extract sensitive information through exploitation of architectural vulnerabilities. These attacks target fundamental limitations in [[Foundation Models]], ranging from [[Jailbreak]] vectors that circumvent content filters to automated inference attacks that collapse [[pseudonymity]] protections.

## Modality-Specific Jailbreaks

Research on [[Modal Aphasia]] identifies critical [[Adversarial Attacks]] that exploit dissociations between [[Visual Memory]] and [[Textual Articulation]] in [[Unified Multimodal Models]]:

- **Asymmetric Safeguards**: Safety measures applied to [[Text Generation]] leave harmful concepts fully accessible through [[Image Generation]], allowing "a model aligned solely on text [to remain] capable of generating unsafe images"
- **Visual Bypass Vectors**: Visual modalities function as exploit paths that bypass textual content filters, creating reliable [[Jailbreak]] mechanisms
- **Moderation Failures**: [[Content Moderation]] systems assuming unified safety across modalities fail to detect harmful visual outputs, leaving gaps in [[AI Safety Frameworks]]

These attacks represent fundamental architectural properties rather than training artifacts, indicating that alignment techniques must account for [[Modality-Specific Representations]] rather than assuming transfer between vision and language.

## Automated Deanonymization Attacks

[[Large Language Model]]s enable large-scale adversarial attacks against user privacy that substantially outperform classical methods:

### Attack Methodology
The attack pipeline operates in both [[open-world]] and [[closed-world]] settings:
1. **Feature Extraction**: LLMs extract identity-relevant features from unstructured text in pseudonymous profiles
2. **Semantic Search**: [[semantic embeddings]] identify candidate matches across databases
3. **Verification**: Models reason over top candidates to verify matches and reduce false positives

### Performance Metrics
Unlike classical deanonymization attacks (such as those on the [[Netflix Prize]] dataset) requiring structured data schemas, LLM-based approaches operate directly on raw text:
- Achieved **up to 68% recall at 90% precision** in re-identifying [[Hacker News]] and [[Anthropic Interviewer]] participants
- Best non-LLM methods achieved **near 0%** under identical conditions
- Capable of matching users across platforms ([[Hacker News]] → [[LinkedIn]]) and communities ([[Reddit]] movie discussions)

## Implications for Security

### Threat Model Reconsideration
Adversarial capabilities demonstrated in recent research indicate that "the practical obscurity protecting pseudonymous users online no longer holds and that threat models for online privacy need to be reconsidered."

### Safety Framework Gaps
- **Red Teaming Blindspots**: Current [[Red Teaming]] methodologies may overlook visual-only failure modes and cross-platform inference attacks
- **Modality Asymmetry**: [[AI Safety]] evaluations must test exploit paths across all input modalities, not just text
- **Architectural Vulnerabilities**: Attacks exploiting [[Cross-Modal Alignment]] failures suggest that joint training does not produce seamless safety transfer between vision and language

## Citations

Aerni, Michael. "Modal Aphasia: Can Unified Multimodal Models Describe Images From Memory?" *arXiv preprint arXiv:2510.21842* (2025).

"Large-scale online deanonymization with LLMs." *Research paper on LLM-based privacy attacks* (source summary).

---

## Backlinks

- [[concepts/ai-safety-frameworks|AI Safety Frameworks]]
- [[concepts/ai-safety|Ai Safety]]
- [[concepts/anthropic-interviewer|Anthropic Interviewer]]
- [[concepts/artificial-intelligence|Artificial Intelligence]]
- [[concepts/content-moderation|Content Moderation]]
- [[concepts/cross-modal-alignment|Cross-Modal Alignment]]
- [[concepts/cross-modal-alignment|Cross-Modal Alignment]]
- [[concepts/cross-modal-understanding|Cross-Modal Understanding]]
- [[concepts/hacker-news|Hacker News]]
- [[concepts/image-generation|Image Generation]]
- [[concepts/large-language-model|Large Language Model]]
- [[concepts/linkedin|LinkedIn]]
- [[concepts/modal-aphasia|Modal Aphasia]]
- [[sources/modal-aphasia-can-unified-multimodal-models-describe-images-from-memory|Modal Aphasia - Can Unified Multimodal Models Describe Images From Memory?]]
- [[concepts/modality-specific-representations|Modality-Specific Representations]]
- [[concepts/multimodal-training|Multimodal Training]]
- [[concepts/multiple-architectures|Multiple Architectures]]
- [[concepts/red-teaming|Red Teaming]]
- [[concepts/reddit|Reddit]]
- [[concepts/synthetic-datasets|Synthetic Datasets]]
