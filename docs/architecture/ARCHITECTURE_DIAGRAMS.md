# PRAXIS InterviewOS — Master Architecture Diagrams

**Document ID**: ARCH-DIAGRAMS-MASTER  
**Milestone**: Four-Phase Engineering Rebuild  
**Standard**: Antigravity Pro 10/10 Engineering Standard  
**Format**: GitHub Flavored Markdown / Mermaid Diagrams  

---

## 5.1 Complete System Architecture

```mermaid
flowchart TD
    subgraph Clients["Client Layer"]
        Web["Web Client (Next.js 15 App Router)"]
        Desktop["Desktop Client (Electron + DPAPI Vault)"]
    end

    subgraph Edge["Edge & Ingress Security"]
        CDN["Cloud Armor & Cloud CDN"]
        WAF["WAF / Rate Limiter & SSL Termination"]
        EdgeLB["External HTTPS / WSS Load Balancer"]
        CDN --> EdgeLB
        WAF --> EdgeLB
    end

    Web -->|HTTPS / W3C Tracing| EdgeLB
    Desktop -->|WSS Binary Audio / REST| EdgeLB

    subgraph GCP["Google Cloud Platform (Region: asia-south1)"]
        subgraph CloudRun["Serverless Compute Cluster (Managed)"]
            APIGW["FastAPI Core Backend (praxis-api)\n2 vCPU, 2 GiB, Autoscale 1-10"]
            RTGW["Realtime Agent Gateway (praxis-realtime)\n4 vCPU, 4 GiB, Autoscale 1-5, Sticky WSS"]
            Worker["ARQ Background Workers (praxis-worker)\n2 vCPU, 2 GiB, Health Probe :8080"]
        end

        subgraph VPC["Private VPC Network (10.0.0.0/28)"]
            VPCConnector["Serverless VPC Access Connector"]
            RedisCluster[("Memorystore Redis 7\n10.0.0.4:6379\nQueue + RateLimit + State")]
        end

        subgraph Security["Cloud Security & Observability"]
            SecMgr["GCP Secret Manager (v1 Pinned)"]
            CloudTrace["Cloud Trace / OpenTelemetry Collector"]
            CloudLog["Cloud Logging (JSON + PII Redactor)"]
            Prometheus["Cloud Monitoring & Alerting"]
        end
    end

    EdgeLB -->|/api/*| APIGW
    EdgeLB -->|/ws/*| RTGW

    APIGW --> VPCConnector
    RTGW --> VPCConnector
    Worker --> VPCConnector
    VPCConnector --> RedisCluster

    APIGW -.-> SecMgr
    RTGW -.-> SecMgr
    Worker -.-> SecMgr

    APIGW --> CloudTrace
    RTGW --> CloudTrace
    Worker --> CloudTrace
    APIGW --> CloudLog
    RTGW --> CloudLog
    Worker --> CloudLog

    subgraph DataPlane["Durable Data & Identity Plane (Supabase)"]
        SupaAuth["Supabase Identity Provider\nRS256 / JWKS Cache + Auth"]
        SupaDB[("Supabase PostgreSQL 18\npgvector + Row Level Security (RLS)")]
        SupaStorage["Supabase Object Storage\nDocuments & Audio Vault"]
    end

    APIGW -->|JWT JWKS Verify| SupaAuth
    RTGW -->|Connection Auth| SupaAuth
    APIGW -->|AsyncPG Pool <= 5/inst| SupaDB
    Worker -->|AsyncPG Pool| SupaDB
    APIGW -->|Signed URL / Secure Upload| SupaStorage
    Worker -->|Document Extraction| SupaStorage

    subgraph AILayer["AI Gateway & Execution Boundaries"]
        AIGW["PRAXIS AI Gateway\nCircuit Breaker + Budget Guard"]
        WhisperVAD["Local In-Memory DSP Engine\nSilero VAD + faster-whisper (Offline)"]
        Sandbox["Coding Execution Sandbox\nIsolated Non-Root Worker (Docker)"]
    end

    RTGW --> WhisperVAD
    APIGW --> AIGW
    RTGW --> AIGW
    Worker --> AIGW
    APIGW --> Sandbox

    subgraph ExternalLLM["External LLM Providers"]
        OpenAI["Primary: OpenAI (GPT-4o)"]
        Gemini["Secondary: Google Gemini 1.5"]
        DeepSeek["Cost-Tier: DeepSeek-V3"]
        FlanT5["Offline Fallback: Local Flan-T5"]
    end

    AIGW -->|BYOK / Failover| OpenAI
    AIGW -.->|Fallback 1| Gemini
    AIGW -.->|Fallback 2| DeepSeek
    AIGW -.->|Local Degraded| FlanT5
```

---

## 5.2 Realtime Interview Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Candidate as Candidate (Desktop / Web)
    participant Edge as Edge WSS Ingress
    participant RT as Realtime Gateway (praxis-realtime)
    participant Redis as Memorystore Redis 7
    participant Auth as Supabase Auth (JWKS)
    participant DSP as Silero VAD + faster-whisper
    participant AIGW as AI Gateway (Fast/Slow Path)
    participant DB as PostgreSQL (Supabase RLS)

    Candidate->>Edge: Connect WSS /ws/interview/{session_id}
    Edge->>RT: Upgrade WebSocket Connection
    Note over Candidate,RT: AUTHENTICATION PHASE (10s Timeout)
    Candidate->>RT: Handshake Frame (Bearer JWT Token)
    RT->>Auth: Validate Token Signature (RS256 JWKS)
    Auth-->>RT: Claims: user_id, exp, tenant_id
    RT->>DB: Verify Session Ownership (candidate_id == user_id)
    DB-->>RT: Authorized (State: READY)
    RT->>Candidate: HandshakeAck (session_state: READY, audio_cfg: 16kHz mono)

    Note over Candidate,RT: AUDIO INGESTION & REALTIME FAST PATH
    loop Every 20-50ms
        Candidate->>RT: Binary Frame (>BBIdI + PCM16 16kHz Chunk)
        RT->>RT: Validate Frame Header & Monotonic Sequence Number
        RT->>DSP: Ingest Audio Bytes (Sliding Buffer)
        DSP->>DSP: Silero VAD Speech Detection
        alt Speech Detected (Fast Path)
            DSP->>DSP: faster-whisper Partial Decode (RTF = 0.185)
            DSP-->>RT: Partial Transcript + Confidence
            RT->>Candidate: Fast Event: live_transcript_update (<80ms HUD)
        else Silence >= 500ms (Utterance End)
            DSP->>DSP: faster-whisper Final Segment Decode
            DSP-->>RT: Final Segment (text, start_ms, end_ms)
            RT->>Candidate: Final Event: transcript_finalized
            RT->>Redis: Append Turn Audio Segment
        end
    end

    Note over RT,AIGW: SLOW-PATH REASONING & ADAPTIVE TURN
    RT->>DB: Retrieve Candidate Grounded Facts (pgvector verified=true)
    DB-->>RT: Verified Context Chunks
    RT->>AIGW: Evaluate Answer & Formulate Follow-up (Context + Utterance)
    AIGW-->>RT: Structured Evaluation + Next Grounded Question
    RT->>Candidate: Interviewer Event: next_question (Audio TTS + Text)
    RT->>DB: Persist TurnScore, TranscriptSegment, Metric
```

---

## 5.3 Security Architecture & Trust Boundaries

```mermaid
flowchart TD
    subgraph UntrustedZone["Untrusted External Zone"]
        PublicNet["Public Internet / Attacker Entrypoint"]
        CandidateBrowser["Candidate Browser / Desktop Renderer"]
        ResumeUploads["Untrusted Uploads (PDF / DOCX)"]
    end

    subgraph DMZ["Ingress & Perimeter Defense"]
        CloudArmor["Cloud Armor WAF (OWASP Top 10 + DDoS)"]
        TLSEndpoint["TLS 1.3 Termination (HSTS, CSP, Strict Headers)"]
        RateLimiter["IP / Token Bucket Rate Limiter (Redis)"]
    end

    PublicNet --> CloudArmor
    CandidateBrowser --> CloudArmor
    ResumeUploads --> CloudArmor
    CloudArmor --> TLSEndpoint
    TLSEndpoint --> RateLimiter

    subgraph AppTrustBoundary["Application Trust Boundary (Zero Trust)"]
        JWTValidator["JWT Asymmetric RS256 / JWKS Validator\n(Algorithm Allowlist, Replay & Expiry Checks)"]
        InputSanitizer["Pydantic Strict Schemas + SSRF Guard"]
        UploadGuard["Upload Guard: MIME Magic Sniffer, 10MB Cap, ClamAV"]
        PromptGuard["Prompt Guard: Delimiter Sandbox + Injection Shield"]
    end

    RateLimiter --> JWTValidator
    JWTValidator --> InputSanitizer
    InputSanitizer --> UploadGuard
    InputSanitizer --> PromptGuard

    subgraph InternalServices["Isolated Internal Execution (VPC)"]
        APIProcess["FastAPI API Engine (Non-Root UID 10001)"]
        WorkerProcess["ARQ Background Worker (Non-Root UID 10001)"]
        CodingSandbox["Isolated Coding Sandbox (cgroups, no net, 256MB cap)"]
    end

    UploadGuard --> WorkerProcess
    PromptGuard --> APIProcess
    APIProcess --> CodingSandbox

    subgraph DataIsolationBoundary["Data Isolation Boundary (PostgreSQL RLS)"]
        DBPool["Bounded SQLAlchemy Connection Pool (<=5/inst)"]
        RLS["PostgreSQL Row Level Security (FORCE RLS)"]
        TenantTables["Tenant-Isolated Tables (Candidate A != Candidate B)"]
        Vault["Encrypted Secrets Vault (Secret Manager v1)"]
    end

    APIProcess --> DBPool
    WorkerProcess --> DBPool
    DBPool --> RLS
    RLS --> TenantTables
    APIProcess -.-> Vault
    WorkerProcess -.-> Vault
```

---

## 5.4 Database Entity-Relationship Architecture

```mermaid
erDiagram
    users ||--o{ profiles : "has"
    profiles ||--o{ candidates : "identifies"
    profiles ||--o{ user_settings : "configures"
    profiles ||--o{ admin_users : "escalates_to"

    candidates ||--o{ resumes : "uploads"
    resumes ||--o{ resume_versions : "versions"
    resume_versions ||--o{ resume_claims : "extracts"
    resume_versions ||--o{ document_chunks : "embeds"

    candidates ||--o{ candidate_skills : "possesses"
    skills ||--o{ candidate_skills : "categorizes"
    candidates ||--o{ candidate_experiences : "records"
    candidates ||--o{ candidate_projects : "builds"
    candidate_projects ||--o{ project_metrics : "measures"
    candidates ||--o{ stories : "narrates"

    jobs ||--o{ job_blueprints : "defines"
    jobs ||--o{ job_requirements : "demands"
    jobs ||--o{ job_matches : "evaluates"
    candidates ||--o{ job_matches : "matches"

    candidates ||--o{ practice_sessions : "attends"
    practice_sessions ||--o{ session_turns : "progresses_through"
    session_turns ||--o{ transcript_segments : "transcribes"
    session_turns ||--o{ turn_metrics : "gauges"
    session_turns ||--o{ turn_scores : "evaluates"
    practice_sessions ||--o{ session_claims : "verifies"
    practice_sessions ||--o{ session_state_logs : "audits"
    practice_sessions ||--o{ session_debriefs : "summarizes"

    candidates ||--o{ study_items : "schedules"
    study_items ||--o{ study_reviews : "spaced_reviews"

    candidates ||--o{ applications : "applies"
    applications ||--o{ application_events : "tracks"
    applications ||--o{ outreach_drafts : "drafts"

    candidates ||--o{ audit_logs : "records_actions"
    candidates ||--o{ privacy_events : "requests_gdpr"
    candidates ||--o{ deletion_jobs : "purges"
```

---

## 5.5 Deployment & Networking Architecture

```mermaid
flowchart LR
    subgraph Internet["Public Ingress"]
        DNS["Google Cloud DNS"]
        ClientApp["Desktop & Web Clients"]
    end

    subgraph GCP_Project["GCP Project: praxis-interviewos (asia-south1)"]
        subgraph CloudArmorSec["Ingress Security Layer"]
            ExtLB["Global HTTPS Load Balancer"]
            Armor["Google Cloud Armor WAF"]
            SSL["Google-Managed SSL Certificate"]
            Armor --- ExtLB
            SSL --- ExtLB
        end

        subgraph ServerlessRegion["Cloud Run Services (asia-south1)"]
            APIService["praxis-api\nContainer: UID 10001\nMin: 1, Max: 10\nDirect VPC Egress"]
            RTService["praxis-realtime\nContainer: UID 10001\nMin: 1, Max: 5\nSession Affinity: true"]
            WorkerService["praxis-worker\nContainer: UID 10001\nMin: 1, Max: 4\nHealth Port: 8080"]
        end

        subgraph VPCNet["VPC: praxis-vpc (10.0.0.0/24)"]
            VPCConn["Serverless VPC Connector (10.0.0.0/28)"]
            RedisInst["Memorystore Redis 7 Basic (10.0.0.4)"]
            VPCConn --- RedisInst
        end

        subgraph SecretsAndObservability["Management & Security"]
            SecManager["Secret Manager\n(DATABASE_URL, SUPABASE_KEY)"]
            CloudLogging["Cloud Logging (Structured JSON)"]
            CloudTrace["Cloud Trace (W3C traceparent)"]
        end
    end

    subgraph SupabaseCloud["Supabase Managed Cloud"]
        SupaPostgres[("PostgreSQL 18 + pgvector\n(Pool: max 100 conns)")]
        SupaStorageBucket["Encrypted Storage Buckets\n(documents, audio)"]
    end

    ClientApp --> DNS
    DNS --> ExtLB
    ExtLB -->|Path: /api/*| APIService
    ExtLB -->|Path: /ws/*| RTService

    APIService --> VPCConn
    RTService --> VPCConn
    WorkerService --> VPCConn

    APIService --> SupaPostgres
    WorkerService --> SupaPostgres
    APIService --> SupaStorageBucket
    WorkerService --> SupaStorageBucket

    APIService -.-> SecManager
    RTService -.-> SecManager
    WorkerService -.-> SecManager

    APIService --> CloudLogging
    RTService --> CloudLogging
    WorkerService --> CloudLogging
    APIService --> CloudTrace
    RTService --> CloudTrace
```

---

## 5.6 AI/ML Architecture & Audio Intelligence

```mermaid
flowchart TD
    subgraph Ingestion["1. Candidate Document Intelligence"]
        RawResume["Raw Resume (PDF / DOCX)"] --> SafeOCR["Text Extraction & Layout Parsing"]
        SafeOCR --> Chunking["Token Chunking & Overlap"]
        Chunking --> Embedder["Embedding Generation (BAAI/bge-small-en-v1.5)"]
        Embedder --> VectorDB[("pgvector: document_chunks\n(verified_by_user = true)")]
        SafeOCR --> Extractor["Structured Extraction (Experience, Skills, Claims)"]
        Extractor --> FactReview["Candidate Verification UI (Human in the Loop)"]
        FactReview --> VerifiedFacts[("Verified Facts: resume_claims")]
    end

    subgraph AudioEngine["2. Realtime Audio & Speech Engine"]
        AudioChunk["Client PCM16 Audio Stream (16 kHz mono)"] --> ProtocolValidator["Protocol Validator (>BBIdI Layout)"]
        ProtocolValidator --> JitterBuffer["Bounded Audio Buffer (Backpressure Guard)"]
        JitterBuffer --> Silero["Silero VAD (Speech vs Silence)"]
        Silero -->|Speech Active| FasterWhisper["faster-whisper Small Quantized (Offline Baked)"]
        FasterWhisper -->|Partial Chunk| FastHUD["Fast Path: HUD Cadence (<80ms)"]
        Silero -->|Silence >= 500ms| FinalTranscript["Final Utterance Assembly"]
    end

    subgraph Orchestration["3. AI Gateway & Evaluation Engine"]
        FinalTranscript --> ContextPacker["Context Packer (RAG Retrieval + Session State)"]
        VerifiedFacts --> ContextPacker
        VectorDB --> ContextPacker
        ContextPacker --> GatewayRouter["AI Gateway Router"]
        
        GatewayRouter --> CircuitBreaker{"Circuit Breaker\nHealthy?"}
        CircuitBreaker -->|Yes| PrimaryLLM["Primary: OpenAI GPT-4o"]
        CircuitBreaker -->|Open / Timeout| FallbackLLM["Secondary: Google Gemini 1.5"]
        CircuitBreaker -->|Critical Fail| LocalModel["Local: Flan-T5 Heuristic"]

        PrimaryLLM --> Validator["Output JSON Schema & Injection Validator"]
        FallbackLLM --> Validator
        LocalModel --> Validator
    end

    subgraph Feedback["4. Scoring & Grounding"]
        Validator --> RubricEngine["6-Dimension Rubric Scoring"]
        Validator --> ClaimGrounder["Claim Grounding (SUPPORTED / CONTRADICTED)"]
        RubricEngine --> DebriefOutput["Session Debrief & Spaced Repetition Study Plan"]
        ClaimGrounder --> DebriefOutput
    end
```
