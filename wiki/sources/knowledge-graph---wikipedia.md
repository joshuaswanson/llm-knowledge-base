---
title: Knowledge Graph
tags: [technology, data-science, artificial-intelligence, semantic-web, knowledge-representation]
related: [[Knowledge Base]], [[Semantic Web]], [[Graph Database]], [[Machine Learning]], [[Ontology]], [[Entity Alignment]], [[Graph Neural Network]]
---

# Knowledge Graph

In **knowledge representation and reasoning**, a [[Knowledge Graph]] is a [[Knowledge Base]] that uses a [[Graph (discrete mathematics)]]-structured [[Data Model]] or [[Topology]] to represent and operate on [[Data]]. Knowledge graphs store interlinked descriptions of [[Entities]] – objects, events, situations, or abstract concepts – while encoding the free-form [[Semantics]] or relationships underlying these entities.[^1][^2]

Historically associated with the [[Semantic Web]] and [[Linked Open Data]], knowledge graphs focus on connections between [[Concept]]s and entities.[^3][^4] They are widely used by [[Search Engine]]s (e.g., [[Google]], [[Bing]], [[Yahoo]]), [[Knowledge Engine]]s (e.g., [[WolframAlpha]], [[Apple]], [[Amazon Alexa]]), and [[Social Network]]s (e.g., [[LinkedIn]], [[Facebook]]). Recent developments in [[Machine Learning]], particularly [[Graph Neural Network]]s, have broadened their scope into scientific research fields such as [[Genomics]], [[Proteomics]], and [[Systems Biology]].[^5]

## History

The term was coined as early as **1972** by Austrian [[Linguist]] [[Edgar W. Schneider]] regarding modular instructional systems.[^6] Key milestones in development include:

*   **Late 1980s:** [[University of Groningen]] and [[University of Twente]] launched a project focusing on [[Semantic Network]] design with restricted edges to facilitate [[Graph Algebra]].[^7]
*   **1985:** [[Wordnet]] founded to capture semantic relationships between words.
*   **1998:** Andrew Edmonds created [[ThinkBase]], offering [[Fuzzy Logic]] based reasoning in a graphical context.[^8]
*   **2005:** Marc Wirk founded [[Geonames]] for geographic name relationships.
*   **2007:** [[DBpedia]] and [[Freebase]] founded as graph-based repositories. DBpedia focused on [[Wikipedia]] data, while Freebase included public datasets.
*   **2012:** [[Google]] introduced the [[Knowledge Graph (Google)]], building on DBpedia and Freebase. This introduced the term to common use and complemented string-based search. It incorporated [[RDFa]], [[Microdata]], and [[JSON-LD]], organized using the [[Schema.org]] vocabulary.[^10][^11]
*   **2019:** [[IEEE]] combined conferences on "Big Knowledge" and "Data Mining" into the **International Conference on Knowledge Graph**.[^14]
*   **2024:** Microsoft Research released [[GraphRAG]], integrating LLM-generated graphs into [[Retrieval-Augmented Generation]].[^15]

Since Google's introduction, multinationals including [[Facebook]], [[LinkedIn]], [[Airbnb]], [[Microsoft]], [[Amazon]], [[Uber]], and [[eBay]] have advertised their use of knowledge graphs.[^13]

## Definitions

There is no single commonly accepted definition of a knowledge graph. Most definitions view the topic through a [[Semantic Web]] lens and include these features:[^18]

*   **Flexible relations:** Defines [[Abstract Class]]es and relations of entities in a schema, describes real-world entities in a graph structure, allows interrelating arbitrary entities, and covers various topical domains.[^19]
*   **General structure:** A network of entities, their semantic types, properties, and relationships. Properties often use categorical or numerical values.[^20][^21]
*   **Supporting reasoning:** Acquires and integrates information into an [[Ontology]] and applies a reasoner to derive new knowledge.[^3]

A simpler definition often used is:
> "A digital structure that represents knowledge as concepts and the relationships between them (facts). A knowledge graph can include an ontology that allows both humans and machines to understand and reason about its contents."[^22][^23]

## Implementations

Knowledge graph implementations vary from open projects to commercial tools:

*   **Open Projects:** [[YAGO]], [[Wikidata]], and the [[Linked Open Data]] cloud.
*   **Search Tools:** Google's [[Knowledge Graph]], Yahoo's Spark, Microsoft's Satori.
*   **Entity Graphs:** [[LinkedIn]] and [[Facebook]] entity graphs.
*   **Note-taking:** Applications allowing users to build a [[Personal Knowledge Graph]].[^25]
*   **Graph Databases:** Specialized databases like [[Neo4j]], [[GraphDB]], and [[AgensGraph]] allow users to store data as entities and relationships, facilitating data reasoning and [[Node Embedding]].[^26][^27][^28]
*   **Virtual Knowledge Graphs:** Do not store information in specialized databases; they rely on underlying [[Relational Database]]s or [[Data Lake]]s. Queries are answered through mappings defining the relationship between data sources and the virtual graph ontology.[^29][^30]

## Reasoning and Machine Learning

A knowledge graph formally represents semantics by describing entities and relationships, often using an [[Ontology]] as a schema layer. This allows for [[Logical Inference]] to retrieve [[Implicit Knowledge]] rather than only explicit knowledge.[^31][^32]

To integrate with [[Machine Learning]] tasks, methods for deriving latent feature representations ([[Knowledge Graph Embedding]]) have been devised. These connect knowledge graphs to methods requiring feature vectors like [[Word Embedding]].[^33][^34][^35]

*   **Graph Neural Networks (GNNs):** Deep learning architectures comprising edges and nodes corresponding to entities and relationships. They provide a domain for [[Semi-Supervised Learning]], where networks predict node or edge values based on adjacent nodes. These tasks serve as abstractions for knowledge graph reasoning and alignment.[^36][^37]
*   **Large Language Models (LLMs):** The development of LLMs expanded interest in knowledge graphs as a way to structure information from unstructured text. Advances in language processing enable automatic or semi-automatic generation and expansion of graphs.[^15][^16][^17]

## Entity Alignment

As knowledge graphs grow across various fields, the same entity is often represented in multiple graphs. Resolving which entities from disparate graphs correspond to the same real-world subject is known as [[Knowledge Graph Entity Alignment]].[^38]

*   **Strategies:** Identify similar substructures, semantic relationships, shared attributes, or combinations thereof between distinct graphs.
*   **Methods:** Use structural similarities between generally non-isomorphic graphs to predict node correspondence.[^39][^40]
*   **LLMs:** Recent successes of [[Large Language Model]]s, particularly in producing syntactically meaningful embeddings, have spurred their use in entity alignment tasks.[^41]

## See Also

*   [[Concept Map]]
*   [[Formal Semantics (Natural Language)]]
*   [[Graph Database]]
*   [[Knowledge Base]]
*   [[Knowledge Graph Embedding]]
*   [[Logical Graph]]
*   [[Semantic Integration]]
*   [[Semantic Technology]]
*   [[Topic Map]]
*   [[Vadalog]]
*   [[Wikibase]]
*   [[Wikidata]]
*   [[YAGO (database)]]

---
[^1]: "What is a Knowledge Graph?", ontotext. 2018.
[^2]: Kumar Pandey, Atul (2020-12-18). "What defines a knowledge graph?", AtulHost.
[^3]: Ehrlinger, Lisa; Wöß, Wolfram (2016). "Towards a Definition of Knowledge Graphs", SEMANTiCS2016.
[^4]: Soylu, Ahmet (2020). "Enhancing Public Procurement in the European Union...", The Semantic Web – ISWC 2020.
[^5]: Mohamed, Sameh K. et al. (2021). "Biological applications of knowledge graph embedding models", Briefings in Bioinformatics.
[^6]: Schneider, Edward W. (1973). "Course Modularization Applied...", ERIC.
[^7]: Victor, Filippov et al. (2024). "Algorithms and methods for automated construction of knowledge graphs...", E3S Web of Conferences.
[^8]: "US Trademark no 75589756".
[^9]: Michael, Färber et al. (2015). "A Comparative Survey of DBpedia, Freebase, OpenCyc, Wikidata, and YAGO".
[^10]: Singhal, Amit (May 16, 2012). "Introducing the Knowledge Graph: things, not strings", Official Google Blog.
[^11]: Schwartz, Barry (December 17, 2014). "Google's Freebase To Close...", Search Engine Roundtable.
[^12]: McCusker, James P.; McGuiness, Deborah L. "What is a Knowledge Graph?", www.authorea.com.
[^13]: "Knowledge Graph Enterprises", kgkg.factnexus.com (2020).
[^14]: "2021 IEEE International Conference on Knowledge Graph (ICKG)*", KMedu Hub.
[^15]: Edge, Darren et al. (2025). "From Local to Global: A Graph RAG Approach...", arXiv.
[^16]: Yih, Wen-tau et al. (July 2015). "Semantic Parsing via Staged Query Graph Generation...", ACL.
[^17]: Lewis, Patrick et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", NeurIPS.
[^18]: Ehrlinger, Lisa; Wöß, Wolfram (2016).
[^19]: McCusker, James P.; McGuiness, Deborah L.
[^20]: "What is a Knowledge Graph?", ontotext. 2018.
[^21]: Kumar Pandey, Atul (2020).
[^22]: McCusker, James P.; McGuiness, Deborah L.
[^23]: "What defines a knowledge graph?", AtulHost.
[^24]: Soylu, Ahmet (2020).
[^25]: "What defines a knowledge graph?", AtulHost.
[^26]: Neo4j documentation.
[^27]: GraphDB documentation.
[^28]: AgensGraph documentation.
[^29]: "What is a Knowledge Graph?", ontotext. 2018.
[^30]: Kumar Pandey, Atul (2020).
[^31]: Soylu, Ahmet (2020).
[^32]: Ehrlinger, Lisa; Wöß, Wolfram (2016).
[^33]: Mohamed, Sameh K. et al. (2021).
[^34]: Yih, Wen-tau et al. (July 2015).
[^35]: Lewis, Patrick et al. (2020).
[^36]: Mohamed, Sameh K. et al. (2021).
[^37]: Edge, Darren et al. (2025).
[^38]: Edge, Darren et al. (2025).
[^39]: Yih, Wen-tau et al. (July 2015).
[^40]: Lewis, Patrick et al. (2020).
[^41]: Edge, Darren et al. (2025).