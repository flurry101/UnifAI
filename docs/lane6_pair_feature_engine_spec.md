# Lane 6: Pair Feature Engine Specification

## Overview
Lane 6 is responsible for extracting explicit technical features from pairs of materials (Query vs. Candidate) retrieved by Lane 5. Unlike Lane 5, which optimizes for high recall using "fuzzy" embeddings and lexical matches, Lane 6 evaluates the exact technical parameters to determine the validity of the relationship.

## Input
`(query_material, candidate_material)`

## Features

### 1. Exact Matches
Boolean or similarity indicators for direct attribute overlap:
* `manufacturer_match`: Do the manufacturers align (if present)?
* `mpn_match`: Do the MPNs align?

### 2. Normalized Attribute Matches
Extraction and hard comparison of critical technical parameters:
* `dimension_match`: Extracts dimensions (e.g., `4 IN`, `DN100`) from both descriptions and compares for equality/compatibility.
* `pressure_rating_match`: Extracts pressure classes (e.g., `CL150`, `150#`, `PN20`) and compares.
* `material_grade_match`: Extracts material grades (e.g., `WCB`, `SS316`, `A105`) and compares.
* `standard_match`: Extracts standards (e.g., `ASTM`, `ASME`, `IS`) and compares.

### 3. Technical Conflicts
A high-priority penalty feature flag.
* `technical_conflict`: Set to `True` if a hard technical parameter (dimension, pressure, material, standard) is identified in both records but explicitly mismatches. (e.g. `4 IN` vs `2 IN`, or `CL150` vs `CL300`).

### 4. Semantic Similarity
* `semantic_similarity`: The 1024-dimensional Qwen3 cosine similarity score retrieved from Lane 5.

### 5. Lexical Similarity
* `lexical_similarity`: The BM25 score retrieved from Lane 5.

## Output
`relationship_score`: A structured scoring object summarizing the pairwise relationship.

### Possible Output Classes
Based on the combined feature extraction, the engine will output one of the following decisions:
* `IDENTICAL`: Same manufacturer/MPN or completely exact technical specifications with no conflicts.
* `EQUIVALENT`: Same technical form/fit/function, but different manufacturer/MPN or unspecified manufacturer.
* `VARIANT_OF`: Subset/superset relationship (e.g. one has an extra coating, or one is an assembly containing the other).
* `UNRELATED`: Strong semantic similarity but a hard technical conflict exists (e.g., mismatched pressure rating).
