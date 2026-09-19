# Real CPSE Benchmark — UnifAI SIH26099

## Purpose
This directory contains candidate pairs mined from the real 21,513-record CPSE corpus
for human review and benchmark construction.

## Files
- 
eal_candidate_pairs.csv: All mined candidate pairs with automated signals
- 
eal_review_queue.csv: Stratified sample for human review

## Important
- 
eview_relation is initially NULL (not reviewed)
- 
eview_status is initially UNREVIEWED
- Automated signals (semantic_similarity, technical_conflict, etc.) are NOT labels
- Do NOT train on these signals as ground truth
- Human review must populate 
eview_relation before use as training labels

## Statistics
- Total candidate pairs: 45017
- Review queue size: 800
- Generated: 2026-09-19
