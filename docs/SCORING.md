# Scoring Methodology

Answer scoring is designed to provide concrete feedback for candidates rather than act as an opaque gamified metric.

## Dimensionality
Each answer is evaluated across multiple dimensions on a continuous scale of 0.0 to 1.0:
- **Relevance**: Did the candidate answer the question asked, or did they pivot inappropriately?
- **Correctness**: Were the technical claims factually accurate?
- **Structure**: Was the answer logically organized?
- **Grounding**: (Calculated explicitly) What percentage of the candidate's factual claims could be verified against their provided context?
- **Specificity**: Did the candidate provide concrete details, or stay unhelpfully high-level?
- **Conciseness**: Was the answer sufficiently dense with information, or did it meander?

## Overall Score Calculation
The `overall` score is a deterministic weighted average of the sub-scores. This ensures transparency rather than relying on the LLM to output an arbitrary final number.
Weights:
- Correctness: 0.3
- Relevance: 0.2
- Specificity: 0.2
- Structure: 0.1
- Grounding: 0.1
- Conciseness: 0.1

## Grounding Mechanism
The `grounding` score is NOT hallucinated by the LLM. It is explicitly computed by extracting factual claims from the candidate's answer and running them through the RAG hybrid retrieval system against their verified projects and resume. `Grounding = (Verified Claims) / (Total Claims)`.

## Honest Limitations
LLM-based evaluation of "correctness" and "relevance" is inherently subjective. The model acts as an experienced interviewer proxy, but it is sensitive to phrasing and can be confidently wrong about niche technical trivia. As such, these scores act as a directional indicator of interview performance, not a definitive measurement of a candidate's absolute competence.
