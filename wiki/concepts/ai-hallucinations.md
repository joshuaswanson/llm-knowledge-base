---
title: AI Hallucinations
tags: [artificial-intelligence, large-language-model, error, natural-language-processing, risk-mitigation]
related: [[Retrieval-Augmented Generation]], [[Large Language Model]], [[Knowledge Graph]], [[GraphRAG]], [[Information retrieval]], [[Prompt engineering]]
---

# AI Hallucinations

**AI hallucinations** refer to instances where **Artificial Intelligence**, particularly [[Large Language Model]]s (LLMs), generate content that is factually incorrect, misleading, or not grounded in reality. While the model may produce text that appears coherent and confident, the information is often a fabrication resulting from the model's generative process rather than accurate data retrieval.

In the context of generative AI, hallucinations can manifest as describing nonexistent policies, recommending non-existent legal cases, or citing inaccurate historical data. This phenomenon is a primary driver for the development of architectures like **Retrieval-Augmented Generation** (RAG), which aim to ground model responses in external, verifiable data sources.

## Mechanisms and Causes

LLMs generate text based on patterns learned from their static [[Training data]], rather than querying a database of facts. This architecture introduces several risks for hallucination:

*   **Static Knowledge:** Models rely on pre-existing training data and do not inherently know how to access updated information or specific internal documents without architectural changes.
*   **Context Misinterpretation:** Even when provided with source material, models may misinterpret context. For example, a model might treat a rhetorical question in a source text as a factual statement.
*   **Pattern Matching:** Models prioritize syntactically meaningful patterns over factual verification, leading to confident errors.

## Impact and Examples

Hallucinations can lead to significant financial and reputational damage, particularly when used in public-facing applications.

### The Google Bard Incident
In 2023, during the debut of **Google Bard** (later re-branded to [[Gemini]]), the system provided incorrect information regarding the [[James Webb Space Telescope]].
*   **Consequence:** The error contributed to a **$100 billion** decline in [[Alphabet Inc.]]'s stock value.
*   **Significance:** This event highlighted the market sensitivity to AI reliability issues.

### Contextual Errors
[[MIT Technology Review]] cited an example where an AI system stated:
> "The United States has had one Muslim president, Barack Hussein Obama."

*   **Source:** The AI retrieved an academic book titled *Barack Hussein Obama: America’s First Muslim President?*.
*   **Error:** The model failed to understand the rhetorical nature of the title and treated it as a factual claim.

### RAG Poisoning
Even when using mitigation techniques like [[Retrieval-Augmented Generation]], hallucinations can persist through:
*   **Misleading Sources:** Retrieving factually correct but contextually misleading information.
*   **Conflict Resolution:** Struggling to determine accuracy when faced with conflicting retrieved data.
*   **Knowledge Boundaries:** Generating answers instead of indicating uncertainty when sufficient information is lacking.

## Mitigation Strategies

### Retrieval-Augmented Generation (RAG)
[[Retrieval-Augmented Generation]] is the primary technique cited for mitigating hallucinations by supplementing an LLM's static knowledge with external data sources.

#### How RAG Reduces Hallucinations
By grounding responses in retrieved text, RAG helps reduce fabrication. The process involves:
1.  **Encoding:** Converting reference data into [[Word embeddings]].
2.  **Storage:** Storing embeddings in a [[Vector database]].
3.  **Retrieval:** Selecting relevant documents for a user query.
4.  **Augmentation:** Feeding retrieved information into the LLM via [[Prompt engineering]]. This is sometimes called "prompt stuffing," guiding the model to prioritize supplied data over pre-existing knowledge.
5.  **Generation:** Synthesizing a response using the retrieved documents.

> "Blending the LLM process with a web search or other document look-up process to help LLMs stick to the facts." – **[[Ars Technica]]**

As noted by **[[IBM]]**:
> "When new information becomes available, rather than having to retrain the model, all that’s needed is to augment the model’s external knowledge base with the updated information."

### Knowledge Graph Integration
[[Knowledge Graph]]s offer a structured way to represent entities and relationships, potentially reducing ambiguity.
*   **GraphRAG:** Released in **2024** by Microsoft Research, [[GraphRAG]] integrates LLM-generated graphs into [[Retrieval-Augmented Generation]], providing a more global view of data to reduce hallucination risks associated with local context retrieval.
*   **Entity Alignment:** Resolving entities across disparate graphs helps ensure the model references the correct real-world subjects, reducing confusion.

## Limitations of Mitigation

While techniques like RAG and Knowledge Graphs improve reliability, they do not eliminate hallucinations entirely.

*   **Residual Risk:** [[Ars Technica]] notes, "It is not a direct solution because the LLM can still hallucinate around the source material in its response."
*   **Interpretation:** LLMs may generate misinformation even when pulling from factually correct sources if they misinterpret context.
*   **Conflicting Data:** Models may combine outdated and updated information misleadingly.

## See Also
*   [[Retrieval-Augmented Generation]]
*   [[Knowledge Graph]]
*   [[Large Language Model]]
*   [[Vector database]]
*   [[Prompt engineering]]
*   [[Information retrieval]]
*   [[Graph Neural Network]]