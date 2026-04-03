---
title: Knowledge Graph
tags: [Technology, Data Science, Artificial Intelligence, Knowledge Representation]
related: [[Semantic Web]], [[Machine Learning]], [[Graph Database]], [[Ontology]], [[Knowledge Base]], [[Entity Alignment]]
---

# Knowledge Graph

In [[Knowledge Representation and Reasoning]], a **knowledge graph** is a [[Knowledge Base]] that uses a [[Graph (discrete mathematics)]]-structured [[Data Model]] or [[Topology]] to represent and operate on [[Data]]. Knowledge graphs store interlinked descriptions of [[Entities]] (objects, events, situations, or abstract concepts) while encoding the free-form [[Semantics]] or relationships underlying these entities [[1]][[2]].

They are historically associated with [[Search Engine]]s (e.g., [[Google]], [[Bing]], [[Yahoo]]), [[Knowledge Engine]]s (e.g., [[WolframAlpha]], [[Siri]], [[Amazon Alexa]]), and [[Social Network]]s (e.g., [[LinkedIn]], [[Facebook]]) [[3]][[4]]. Recent developments in [[Data Science]] and [[Machine Learning]], particularly in [[Graph Neural Network]]s and representation learning, have expanded their use into scientific research fields like [[Genomics]], [[Proteomics]], and [[Systems Biology]] [[5]].

## History

The term "knowledge graph" was coined as early as 1972 by the Austrian [[Linguist]] Edgar W. Schneider in the context of modular instructional systems [[6]].

*   **1980s:** The [[University of Groningen]] and [[University of Twente]] began a project called "Knowledge Graphs," focusing on the design of [[Semantic Network]]s with edges restricted to a limited set of relations to facilitate [[Graph Algebra]] [[7]].
*   **1985:** [[Wordnet]] was founded to capture semantic relationships between words and meanings.
*   **1998:** Andrew Edmonds of Science in Finance Ltd created [[ThinkBase]], offering [[Fuzzy Logic]] based reasoning in a graphical context [[8]].
*   **2005:** Marc Wirk founded [[Geonames]] to capture relationships between geographic names and locales [[9]].
*   **2007:** [[DBpedia]] and [[Freebase]] were founded as graph-based knowledge [[Repository]]s for general-purpose knowledge. DBpedia focused on data extracted from [[Wikipedia]], while Freebase included public datasets [[9]].
*   **2012:** Google introduced their [[Knowledge Graph (Google)]], building on DBpedia and Freebase. It incorporated [[RDFa]], [[Microdata]], and [[JSON-LD]] content from indexed web pages, including the [[CIA World Factbook]], [[Wikidata]], and Wikipedia. Entity types were organized using the [[Schema.org]] vocabulary [[10]][[11]][[12]].
*   **2019:** The [[IEEE]] combined its conferences on "Big Knowledge" and "Data Mining and Intelligent Computing" into the International Conference on Knowledge Graph [[14]].
*   **2024:** Microsoft Research's [[GraphRAG]] exemplified the integration of LLM-generated graphs into [[Retrieval-Augmented Generation]], expanding interest in dynamically constructed and adaptive graph structures [[15]][[16]][[17]].

Following Google, several large multinationals advertised their use of knowledge graphs, including [[Facebook]], [[LinkedIn]], [[Airbnb]], [[Microsoft]], [[Amazon]], [[Uber]], and [[eBay]] [[13]].

## Definitions

There is no single commonly accepted definition of a knowledge graph. Most definitions view the topic through a [[Semantic Web]] lens and include these features [[18]]:

*   **Flexible relations among knowledge in topical domains:**
    1.  Defines [[Abstract Class]]es and relations of entities in a schema.
    2.  Mainly describes real world entities and their interrelations, organized in a graph.
    3.  Allows for potentially interrelating arbitrary entities with each other.
    4.  Covers various topical domains [[19]].
*   **General structure:** A network of entities, their semantic types, properties, and relationships. Properties are often represented by categorical or numerical values [[20]][[21]].
*   **Supporting reasoning over inferred ontologies:** A knowledge graph acquires and integrates information into an [[Ontology]] and applies a reasoner to derive new knowledge [[3]].

A simpler definition describes it as a digital structure that represents knowledge as concepts and the relationships between them (facts), potentially including an [[Ontology]] to allow humans and machines to understand and reason about contents [[22]][[23]].

## Implementations

The term "knowledge graph" describes various systems and projects:

*   **Open Knowledge Projects:** [[YAGO]], [[Wikidata]], and the [[Linked Open Data]] cloud [[24]].
*   **Commercial Search Tools:** Yahoo's [[Spark]], Google's [[Knowledge Graph]], and Microsoft's [[Satori]] [[3]].
*   **Social Entity Graphs:** [[LinkedIn]] and [[Facebook]] entity graphs [[3]].
*   **Note-taking Software:** Applications allowing users to build a [[Personal Knowledge Graph]] [[25]].
*   **Graph Databases:** Tools such as [[Neo4j]], [[GraphDB]], and [[AgensGraph]] allow users to store data as entities and interrelationships, facilitating operations like data reasoning, node embedding, and [[Ontology]] development [[26]][[27]][[28]].
*   **Virtual Knowledge Graphs:** Systems that do not store information in specialized databases but rely on an underlying [[Relational Database]] or [[Data Lake]] to answer queries. They require mappings defining the relationship between data source elements and the graph structure [[29]][[30]].

## Reasoning and Machine Learning

A knowledge graph formally represents semantics by describing [[Entity]]s and their relationships. They may use [[Ontology]]s as a schema layer to allow [[Logical Inference]] for retrieving [[Implicit Knowledge]] rather than only explicit knowledge [[31]][[32]].

To support [[Machine Learning]] tasks, methods for deriving latent feature representations of entities and relations have been devised. These [[Knowledge Graph Embedding]]s connect knowledge graphs to methods requiring feature vectors like [[Word Embedding]] [[33]].

*   **Graph Neural Networks (GNNs):** Models for generating useful [[Knowledge Graph Embedding]]s are commonly the domain of GNNs. These deep learning architectures comprise edges and nodes corresponding to entities and relationships. GNNs provide a domain for [[Semi-supervised Learning]], training networks to predict node or edge values [[36]][[37]].
*   **Applications:** These embeddings complement estimates of conceptual similarity and support complex tasks such as knowledge graph reasoning and alignment [[34]][[35]].

## Entity Alignment

As knowledge graphs are produced across various fields, the same [[Entity]] is inevitably represented in multiple graphs. Resolving which entities from disparate graphs correspond to the same real-world subject is known as [[Knowledge Graph Entity Alignment]] [[38]].

*   **Challenges:** No single standard for construction exists, making alignment a non-trivial task.
*   **Strategies:** Methods generally seek to identify similar substructures, semantic relationships, shared attributes, or combinations of these between two distinct graphs [[39]].
*   **LLM Integration:** Recent successes of [[Large Language Model]]s (LLMs) in producing syntactically meaningful embeddings have spurred their use in the task of entity alignment [[41]].
*   **Importance:** Developing dependable methods for alignment is crucial for the integration and cohesion of knowledge graph data as storage amounts grow [[40]].

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
*   [[YAGO (Database)]]