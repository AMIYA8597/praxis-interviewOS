# PRAXIS InterviewOS — Phase 2 System Design Intelligence

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Workstream**: WORKSTREAM H — SYSTEM DESIGN INTELLIGENCE  
**Classification**: PRODUCTION ARCHITECTURE SPECIFICATION  

---

## 1. 24-Step Structured Interview Flow

The System Design Engine (`backend/app/services/system_design_engine.py`) drives candidates through a disciplined, realistic architecture interview sequence across 10 progressive phases:

1. Requirements Gathering (Functional requirements, scale estimates, latency SLAs)
2. Scope & Clarification (Assumptions, out-of-scope boundaries)
3. High-Level Design (Core component topology, client request path)
4. Deep-Dive Component Architecture (Internal state, data structures, caching layers)
5. Scalability Challenges (Handling 10x spikes, replication, partitioning)
6. Data Modeling & Storage Engine (SQL vs NoSQL, indexes, normalization trade-offs)
7. API & Contract Design (REST, gRPC, WebSocket streaming)
8. Failure Scenarios & SPoF Analysis (Network partitions, node crashes, split-brain)
9. Optimization & Caching Strategy (Cache invalidation, write-through vs write-back)
10. Wrap-Up & Trade-off Defense (CAP theorem implications, operational cost)

---

## 2. Dedicated System Design Rubric (`SystemDesignScore`)

Evaluated on a continuous scale $[0.0, 1.0]$:
- `requirements_clarification`: Did candidate establish constraints and question ambiguity?
- `high_level_design`: Coherence and completeness of top-level architecture.
- `scalability`: Realistic load handling, horizontal scaling, and sharding.
- `data_modeling`: Storage engine selection, indexing strategy, and schema design.
- `api_design`: Interface contract precision and protocol suitability.
- `bottleneck_identification`: Ability to spot single points of failure and hot spots.
- `trade_off_reasoning`: Explicit justification of architectural choices.
- `communication`: Clear conceptual narration and proactive collaboration.
