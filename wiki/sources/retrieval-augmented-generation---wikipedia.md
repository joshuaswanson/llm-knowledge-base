---
title: Retrieval-Augmented Generation
tags:
  - AI
  - Large Language Model
  - Information Retrieval
  - Natural Language Processing
  - Generative AI
related:
  - [[Large language model]]
  - [[Information retrieval]]
  - [[AI hallucinations]]
  - [[Vector database]]
  - [[Prompt engineering]]
  - [[Word embeddings]]
  - [[Knowledge graphs]]
  - [[Fine-tuning (deep learning)]]
  - [[IBM]]
  - [[Ars Technica]]
  - [[MIT Technology Review]]
---

## Overview
**Retrieval-augmented generation** (RAG) is a technique enabling [[Large language model]] (LLM) systems to retrieve and incorporate new information from external data sources before responding to user queries. Introduced in a 2020 research paper by Lewis et al., RAG supplements an LLM's static [[Training data]] with domain-specific or updated information from databases, uploaded documents, or web sources. This architecture allows LLM-based [[Chatbot]]s to access internal company data or generate responses based on authoritative sources, reducing reliance on pre-existing model knowledge.

## Core Mechanism
RAG improves LLM performance by blending the generative process with an [[Information retrieval]] mechanism, described by [[Ars Technica]] as "blending the LLM process with a web search or other document look-up process to help LLMs stick to the facts."

### Process Stages
1.  **Encoding:** Reference data is converted into [[Word embeddings]] (numerical representations in a large vector space).
2.  **Storage:** Embeddings are stored in a [[Vector database]] to enable efficient [[Document retrieval]].
3.  **Retrieval:** A document retriever selects the most relevant documents for a specific user query.
4.  **Augmentation:** Retrieved information is fed into the LLM via [[Prompt engineering]]. This technique is sometimes referred to as "prompt stuffing," where additional relevant context guides the model to prioritize supplied data over pre-existing knowledge.
5.  **Generation:** The LLM synthesizes a response using both the query and the retrieved documents.

## Benefits and Efficiency
*   **Cost Reduction:** RAG reduces the need to retrain LLMs with new data, saving computational and financial costs. As noted by [[IBM]], "when new information becomes available, rather than having to retrain the model, all that’s needed is to augment the model’s external knowledge base with the updated information."
*   **Transparency:** RAG allows LLMs to include sources in responses, enabling users to verify cited sources and cross-check accuracy.
*   **Hallucination Mitigation:** By grounding responses in retrieved text, RAG helps reduce [[AI hallucinations]], such as chatbots describing nonexistent policies or recommending non-existent legal cases.

## Limitations and Challenges
While RAG mitigates errors, it does not solve all LLM limitations.

### Persistent Hallucinations and Errors
*   **Context Misinterpretation:** LLMs may generate misinformation even when pulling from factually correct sources if they misinterpret context. [[MIT Technology Review]] cites an example where an AI stated, "The United States has had one Muslim president, Barack Hussein Obama," after retrieving an academic book rhetorically titled *Barack Hussein Obama: America’s First Muslim President?* without understanding the rhetorical nature of the title.
*   **Residual Risk:** [[Ars Technica]] notes, "It is not a direct solution because the LLM can still hallucinate around the source material in its response."
*   **Historical Impact:** Prior to RAG adoption, errors like those seen in [[Google Bard]] (later re-branded to Gemini) contributed significantly to market volatility. Bard provided incorrect information about the [[James Webb Space Telescope]] at its debut, contributing to a $100 billion decline in [[Alphabet Inc.]]'s stock value.

### RAG Poisoning
RAG systems may retrieve factually correct but misleading sources. Models may struggle to determine accuracy when faced with conflicting information or may combine outdated and updated information misleadingly. This occurs because RAG systems may misinterpret the data they retrieve.

### Knowledge Boundaries
Without specific training, models may not recognize when they lack sufficient information to provide a reliable response, generating answers instead of indicating uncertainty.

## Technical Improvements and Variations
Improvements can be applied at different stages of the RAG flow.

### Encoder Optimization
Methods focus on encoding text as dense or sparse vectors.
*   **Sparse Vectors:** Encode word identity, typically dictionary-length with mostly zeros.
*   **Dense Vectors:** Encode meaning, more compact with fewer zeros.
*   **Enhancements:**
    *   **Similarity Calculation:** Optimized using [[Dot product]] scoring and [[Approximate nearest neighbor search]] (ANN) for efficiency over [[K-nearest neighbors algorithm]] (KNN).
    *   **Late Interactions:** Refine document ranking by comparing words more precisely after retrieval (e.g., ColBERT).
    *   **Hybrid Approaches:** Combine dense representations with sparse [[One-hot]] vectors for computational efficiency.

### Retriever-Centric Methods
Aims to enhance document retrieval quality in vector databases.
*   **Inverse Cloze Task (ICT):** Pre-trains the retriever by predicting masked text within documents.
*   **Supervised Optimization:** Aligns retrieval probabilities with the generator's likelihood distribution, minimizing [[KL divergence]] between selections and model likelihoods.
*   **Reranking:** Prioritizes the most relevant documents during training.

### Language Model Redesign
*   **Retro:** Redesigned language models trained from scratch can achieve comparable perplexity to larger networks with 25-time smaller size by incorporating domain knowledge during training.
*   **Retro++:** A more reproducible version of Retro that includes in-context RAG.

### Chunking Strategies
Strategies for breaking data into vectors for retrieval:
*   **Fixed Length with Overlap:** Fast and easy; overlapping chunks maintains semantic context.
*   **Syntax-based:** Breaks documents into sentences (using libraries like spaCy or NLTK).
*   **File Format-based:** Respects natural chunks (e.g., whole functions/classes for code, leaving `<table>` or `<img>` elements intact for HTML). Libraries like Unstructured or Langchain assist here.

### Hybrid Search
Mitigates missed key facts by combining traditional text search results with vector search results, feeding the combined hybrid text into the language model. This impacts content optimization, where retrievability depends on semantic structure and entity clarity rather than traditional backlinks.

## Evaluation and Benchmarks
RAG systems are evaluated using benchmarks testing retrievability, retrieval accuracy, and generative quality.
*   **BEIR:** A suite of [[Information retrieval]] tasks across diverse domains.
*   **Natural Questions:** Google QA dataset for open-domain QA.