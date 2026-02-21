# Plan 3: Objective-Driven Case Extraction

## Context & Strategic Decisions

This plan emerges from a series of product architecture decisions made during a deep design session. Here is the full context you need:

### The Big Picture

We redesigned the product into three levels:

1. **Project level = Orientation.** Documents → chunks → hierarchical clustering → landscape view. No graph extraction at this level. The project is a container that shows themes, coverage, insights. (See Plan 1)

2. **Chat level = Exploration.** Conversations with an organic companion that tracks structure, feeds back into chat context, and does background research. (See Plan 2)

3. **Case level = Investigation.** This is where the reasoning graph lives. A case has an objective (a `decision_question`). The graph (Claims, Evidence, Assumptions, Tensions) is built here, focused on the objective. Blind spots are analyzed, assumptions tested, tensions mapped — all scoped to the decision.

**The key decision: Node extraction happens at the case level, not the project level.** When a case is opened with a decision question, the system:

1. Finds the most relevant chunks from the project's documents
2. Extracts Claims/Evidence/Assumptions/Tensions **with the objective as context**
3. Builds a focused case graph
4. Runs analysis (blind spots, assumption quality, tension mapping)

This is fundamentally different from the current architecture where extraction happens at document upload time (project level) and cases just pull in pre-extracted nodes via embedding similarity.

### Why This Is Better

**Focused extraction:** With an objective, the LLM extracts what matters. Same document, different case = different nodes. A paragraph about PostgreSQL connection pooling produces different nodes for a "schema design" case vs a "performance optimization" case.

**Less noise:** Instead of 200 generic nodes across a project, you get 30-40 focused nodes per case. Every node is relevant to the decision.

**Cheaper:** Extraction is expensive (complex LLM prompt with tool_use). Only running it when a case opens, on relevant chunks only, dramatically reduces cost.

**Better quality:** The extraction prompt includes the decision question, so it can:
- Identify claims that support or oppose the decision
- Surface assumptions specific to this decision
- Find tensions between sources relevant to this question
- Flag evidence that constrains the answer

### How a Case Gets Opened

Cases can be opened from multiple entry points:

1. **From chat companion** (Plan 2): The companion detects a "decision shape" and suggests opening a case. Companion state transfers: established constraints, open questions, eliminated options, research results.

2. **From project insights** (Plan 1): A ProjectInsight (tension, blind spot, pattern) prompts the user to investigate. The insight becomes the seed of the case.

3. **Manually**: User creates a case directly, states the decision question.

4. **From existing flow**: The current `create_case_from_analysis()` path, where chat analysis suggests a case. This already works and we're extending it.

---

## Current Architecture (What Exists Today)

### Case Models (`backend/apps/cases/models.py`)

**Case model:**
- `title`, `status` (draft|active|archived), `stakes` (low|medium|high)
- Decision frame: `decision_question` (TextField), `constraints` (JSONField), `success_criteria` (JSONField), `stakeholders` (JSONField)
- `position` (TextField) — current thesis
- Epistemic confidence: `user_confidence` (0-100), `what_would_change_mind`
- `project` FK (required), `user` FK
- `main_brief` FK → WorkingDocument
- `intelligence_config` JSONField: {auto_validate, background_research, gap_detection}
- `investigation_preferences` JSONField: {rigor, evidence_threshold, disable_locks}
- `embedding` JSONField (nullable)

**WorkingDocument model:**
- `case` FK, `inquiry` FK (nullable)
- `document_type`: case_brief | inquiry_brief | research | source | notes
- `content_markdown` TextField, `ai_structure` JSONField
- Versioned via WorkingDocumentVersion

**InvestigationPlan model:**
- `case` OneToOne, `stage` (exploring|investigating|synthesizing|ready)
- `current_version` int, `position_statement` text
- Versioned via PlanVersion with content: {phases, assumptions, decision_criteria}

### Case Service (`backend/apps/cases/services.py`)

**`create_case()`:**
- Creates case + auto-creates brief
- Calls `GraphService.auto_pull_project_nodes(case)` — embeds decision_question, finds similar nodes (threshold 0.5, top_k=20), creates CaseNodeReferences

**`create_case_from_analysis()`:**
- Creates case from chat conversation analysis
- Pre-populates brief, creates inquiries from key_questions
- Creates initial investigation plan

### Current Extraction (`backend/apps/graph/extraction.py`)

**`extract_nodes_from_document(document_id, project_id)`:**
- Full pipeline: token count → LLM extraction (tool_use) → node creation → edge creation → batch embeddings → chunk provenance matching
- For long docs: section-based with dedup (cosine sim > 0.90) + consolidation pass
- Creates Nodes with `source_type=document_extraction`, `source_document` FK

**This pipeline currently runs at document upload (project level). We're repurposing it to run at case creation, with modifications.**

### Current Auto-Pull (`backend/apps/graph/services.py`)

**`auto_pull_project_nodes(case)`:**
- Embeds case focus text (decision_question + position)
- pgvector similarity search on existing nodes, threshold 0.5, top_k=20
- Creates CaseNodeReference records

**This will be replaced.** Instead of pulling pre-extracted nodes, we'll pull relevant chunks and extract new nodes from them.

### Graph Visualization (Frontend)

**`GraphCanvas.tsx`** — ReactFlow-based graph with:
- Node types: GraphNodeCard (claim/evidence/assumption/tension), ClusterNode
- Edge types: SupportsEdge, ContradictsEdge, DependsOnEdge
- ELK-powered layout via `useGraphLayout.ts`
- Filter bar, health bar, cluster hulls, node detail drawer, minimap

**This stays as-is for cases.** The graph visualization is a case-level tool. No changes needed to the graph components themselves.

---

## Implementation Plan

### Phase 1: Objective-Driven Chunk Retrieval

#### 1.1 Create CaseChunkRetriever

**File:** `backend/apps/cases/chunk_retrieval.py` (new)

This service finds the most relevant document chunks for a case's decision question. It replaces `auto_pull_project_nodes()`.

```python
class CaseChunkRetriever:

    def retrieve_relevant_chunks(
        self,
        case: Case,
        max_chunks: int = 50,
        similarity_threshold: float = 0.45,
    ) -> list[DocumentChunk]:
        """Find the most relevant chunks from the project's documents
        for this case's decision question.

        Strategy:
        1. Embed the decision question + position + constraints
        2. pgvector similarity search across all project chunks
        3. Also pull chunks from relevant theme clusters (from hierarchy)
        4. Deduplicate and rank by relevance
        5. Return top-K chunks with their similarity scores
        """

        # Build the focus text from case context
        focus_parts = [case.decision_question]
        if case.position:
            focus_parts.append(case.position)
        if case.constraints:
            focus_parts.extend([c['description'] for c in case.constraints])

        # If case was created from companion, include established facts
        companion_state = case.metadata.get('companion_origin', {})
        if companion_state.get('established'):
            focus_parts.extend(companion_state['established'])

        focus_text = ' '.join(focus_parts)

        # Strategy 1: Direct embedding similarity
        focus_embedding = generate_embedding(focus_text)
        similar_chunks = DocumentChunk.objects.filter(
            document__project_id=case.project_id,
        ).order_by(
            CosineDistance('embedding', focus_embedding)
        )[:max_chunks * 2]  # Get more than needed for merging

        # Strategy 2: Hierarchy-aware retrieval (if hierarchy exists)
        hierarchy_chunks = self._retrieve_from_hierarchy(
            case.project_id, focus_embedding, max_chunks
        )

        # Merge and deduplicate
        all_chunks = self._merge_and_rank(similar_chunks, hierarchy_chunks, max_chunks)

        return all_chunks

    def _retrieve_from_hierarchy(
        self,
        project_id: uuid.UUID,
        focus_embedding: list[float],
        max_chunks: int,
    ) -> list[DocumentChunk]:
        """Find relevant theme clusters, then pull all chunks from those clusters.
        This catches chunks that might not individually match the query
        but belong to a relevant topic cluster."""

        from apps.graph.models import ClusterHierarchy

        hierarchy = ClusterHierarchy.objects.filter(
            project_id=project_id,
            is_current=True,
        ).first()
        if not hierarchy:
            return []

        # Find Level 1 (topic) or Level 2 (theme) nodes whose summary
        # embeddings are close to the focus
        tree = hierarchy.tree
        relevant_cluster_chunk_ids = []

        # Walk the tree, compare summary embeddings at Level 1 and 2
        for theme in tree.get('children', []):
            theme_sim = cosine_similarity(focus_embedding, theme.get('embedding', []))
            if theme_sim > 0.5:
                # Pull all chunk IDs from this theme's subtree
                relevant_cluster_chunk_ids.extend(
                    self._collect_chunk_ids(theme)
                )
            else:
                # Check topic level within this theme
                for topic in theme.get('children', []):
                    topic_sim = cosine_similarity(focus_embedding, topic.get('embedding', []))
                    if topic_sim > 0.55:
                        relevant_cluster_chunk_ids.extend(topic.get('chunk_ids', []))

        if not relevant_cluster_chunk_ids:
            return []

        return DocumentChunk.objects.filter(
            id__in=relevant_cluster_chunk_ids[:max_chunks]
        ).select_related('document')

    def _collect_chunk_ids(self, node: dict) -> list[str]:
        """Recursively collect all chunk IDs from a hierarchy node's subtree."""
        ids = node.get('chunk_ids', [])
        for child in node.get('children', []):
            ids.extend(self._collect_chunk_ids(child))
        return ids

    def _merge_and_rank(
        self,
        embedding_chunks: QuerySet,
        hierarchy_chunks: list,
        max_chunks: int,
    ) -> list[DocumentChunk]:
        """Merge chunks from both strategies, deduplicate, rank by relevance."""
        seen_ids = set()
        ranked = []

        # Embedding matches first (higher relevance)
        for chunk in embedding_chunks:
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                ranked.append(chunk)

        # Then hierarchy matches (contextually relevant)
        for chunk in hierarchy_chunks:
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                ranked.append(chunk)

        return ranked[:max_chunks]
```

### Phase 2: Case-Level Extraction

#### 2.1 Create CaseExtractionService

**File:** `backend/apps/cases/extraction_service.py` (new)

This is the core of Plan 3. It takes relevant chunks + the case objective and extracts a focused graph.

```python
class CaseExtractionService:

    async def extract_case_graph(
        self,
        case: Case,
        chunks: list[DocumentChunk],
    ) -> CaseExtractionResult:
        """Extract Claims/Evidence/Assumptions/Tensions from relevant chunks,
        focused on the case's decision question.

        Returns nodes, edges, and analysis metadata.
        """

        # 1. Group chunks by document for context
        chunks_by_doc = self._group_by_document(chunks)

        # 2. Build extraction prompt with objective
        prompt = self._build_extraction_prompt(case, chunks_by_doc)

        # 3. Call LLM with tool_use (reuse existing extraction tool schema)
        raw_result = await self._call_extraction_llm(prompt)

        # 4. Validate and create nodes
        nodes = []
        for item in raw_result.get('nodes', []):
            validated = self._validate_extraction_item(item)
            if validated:
                node = await GraphService().create_node(
                    project=case.project,
                    node_type=validated['type'],
                    content=validated['content'],
                    source_type='document_extraction',
                    case=case,  # Case-scoped
                    scope='case',
                    properties=validated.get('properties', {}),
                    confidence=validated.get('confidence', 0.8),
                    created_by=case.user,
                )
                nodes.append(node)

        # 5. Create edges
        edges = []
        for edge_data in raw_result.get('edges', []):
            validated = self._validate_extraction_edge(edge_data)
            if validated:
                edge = await GraphService().create_edge(
                    source_node=node_id_map[validated['source_id']],
                    target_node=node_id_map[validated['target_id']],
                    edge_type=validated['edge_type'],
                    source_type='document_extraction',
                    provenance=validated.get('provenance', ''),
                )
                edges.append(edge)

        # 6. Match source chunks (provenance)
        for node, item in zip(nodes, raw_result['nodes']):
            matched_chunks = self._match_source_chunks(item, chunks)
            node.source_chunks.set(matched_chunks)

        # 7. Emit GraphDelta
        delta = GraphDelta.objects.create(
            project=case.project,
            case=case,
            trigger='document_upload',
            patch={
                'nodes_added': [str(n.id) for n in nodes],
                'edges_added': [str(e.id) for e in edges],
            },
            narrative=f"Extracted {len(nodes)} nodes and {len(edges)} edges for case '{case.title}'",
            nodes_created=len(nodes),
            edges_created=len(edges),
        )

        return CaseExtractionResult(
            nodes=nodes,
            edges=edges,
            delta=delta,
            chunk_count=len(chunks),
        )

    def _build_extraction_prompt(
        self,
        case: Case,
        chunks_by_doc: dict,
    ) -> str:
        """Build the extraction prompt with the case objective as lens.

        This is the key difference from project-level extraction:
        the prompt explicitly scopes extraction to the decision question.
        """
        # See section 2.2 for the full prompt

    def _validate_extraction_item(self, item: dict) -> Optional[dict]:
        """Reuse existing validation from extraction.py with minor modifications."""
        # Same validation logic, but additionally:
        # - Check relevance to case objective (LLM already filtered, but sanity check)
        # - Ensure content is standalone and self-contained

    def _validate_extraction_edge(self, edge: dict) -> Optional[dict]:
        """Reuse existing edge validation."""

    def _match_source_chunks(self, item: dict, chunks: list) -> list[DocumentChunk]:
        """Reuse existing chunk matching logic from extraction.py."""
        # Strategy 1: Text match
        # Strategy 2: Substring match
        # Strategy 3: Embedding similarity
```

#### 2.2 Case Extraction Prompt

**File:** `backend/apps/cases/extraction_prompts.py` (new)

The extraction prompt is similar to the existing document extraction prompt but with a critical addition: the case objective as a focusing lens.

```python
def build_case_extraction_prompt(
    case: Case,
    chunks_by_doc: dict[str, list[dict]],
    companion_state: Optional[dict] = None,
) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) for case-level extraction.

    Key differences from project-level extraction:
    1. The decision question is front and center
    2. Node extraction is focused on relevance to the decision
    3. Assumptions and tensions are specifically about the decision
    4. Established facts from companion are pre-seeded as Evidence
    """

    system_prompt = """You are an expert analyst extracting structured reasoning
    from source documents to help make a specific decision.

    DECISION CONTEXT:
    {decision_question}

    CURRENT POSITION:
    {position}

    KNOWN CONSTRAINTS:
    {constraints}

    YOUR TASK:
    Extract Claims, Evidence, Assumptions, and Tensions from the source material
    that are RELEVANT to this decision. Do not extract everything — only what
    helps reason about the decision.

    NODE TYPES:
    - CLAIM: An assertion relevant to the decision. Must be specific and falsifiable.
      Examples: "Schema-per-tenant provides stronger data isolation"
    - EVIDENCE: A fact, data point, or observation that supports or contradicts claims.
      Examples: "PostgreSQL RLS adds ~3ms overhead per query"
    - ASSUMPTION: Something being taken as true but not verified. CRITICAL for decisions.
      Examples: "We assume query volume will stay under 1000/minute"
    - TENSION: A contradiction or conflict between sources relevant to the decision.
      Examples: "Document A recommends RLS for simplicity, but Document B warns about RLS performance at scale"

    EDGES:
    - SUPPORTS: Evidence/reasoning that favors the target node
    - CONTRADICTS: Evidence/reasoning that opposes the target node
    - DEPENDS_ON: Source node requires target node to hold true

    FOCUS:
    - Extract nodes that MATTER for the decision
    - Prioritize TENSIONS between sources — these are decision-critical
    - Identify ASSUMPTIONS that could change the decision if wrong
    - Flag EVIDENCE that constrains the answer
    - Claims should be scoped to the decision, not general statements

    QUALITY REQUIREMENTS:
    - Each node's content must be STANDALONE — readable without the source
    - Content must be SUBSTANTIVE — no vague statements
    - Importance (1-3): 3 = directly addresses the decision question
    - Include source_passage for provenance
    """

    user_prompt = """SOURCE MATERIAL:

    {formatted_chunks}

    {companion_context}

    Extract the reasoning structure from these sources relevant to the decision:
    "{decision_question}"

    Return nodes and edges using the extraction tool.
    """
```

### Phase 3: Case Analysis Pipeline

#### 3.1 Create CaseAnalysisService

**File:** `backend/apps/cases/analysis_service.py` (new)

After extraction, run analysis on the case graph to identify blind spots, assess assumption quality, and surface key tensions.

```python
class CaseAnalysisService:

    async def analyze_case(self, case: Case) -> CaseAnalysis:
        """Run full analysis on a case's graph after extraction."""

        graph = GraphService().get_case_graph(case.id)
        health = GraphService().compute_case_graph_health(case.id)

        analysis = CaseAnalysis()

        # 1. Blind spot detection
        analysis.blind_spots = await self._detect_blind_spots(case, graph)

        # 2. Assumption assessment
        analysis.assumption_assessment = await self._assess_assumptions(case, graph)

        # 3. Key tensions
        analysis.key_tensions = await self._identify_key_tensions(case, graph)

        # 4. Evidence coverage
        analysis.evidence_coverage = self._assess_evidence_coverage(graph, health)

        # 5. Decision readiness
        analysis.readiness = self._compute_readiness(analysis)

        return analysis

    async def _detect_blind_spots(self, case: Case, graph: dict) -> list[BlindSpot]:
        """What's missing? What hasn't been considered?

        Approach:
        1. Look at the decision question and extracted nodes
        2. Ask LLM: what aspects of this decision are NOT covered by the evidence?
        3. Cross-reference with project hierarchy — are there relevant theme clusters
           that weren't pulled into the case?
        """
        # Get hierarchy themes that WEREN'T in the retrieved chunks
        hierarchy = ClusterHierarchy.objects.filter(
            project_id=case.project_id, is_current=True
        ).first()

        if hierarchy:
            # Find themes with some relevance to the decision but no chunks in the case
            uncovered_themes = self._find_uncovered_relevant_themes(
                case, hierarchy, graph
            )
        else:
            uncovered_themes = []

        # LLM analysis: what's missing?
        prompt = f"""Given this decision: "{case.decision_question}"
        And these extracted nodes: {self._format_nodes(graph['nodes'])}

        What important aspects of this decision are NOT covered?
        Consider: stakeholder impact, implementation risks, alternative approaches,
        second-order effects, timing considerations, reversibility.

        Also, these project themes were NOT included in the analysis:
        {self._format_uncovered_themes(uncovered_themes)}
        Are any of these relevant?
        """

        result = await self._call_llm(prompt)
        return self._parse_blind_spots(result)

    async def _assess_assumptions(self, case: Case, graph: dict) -> list[AssumptionAssessment]:
        """For each assumption in the case graph:
        - How load-bearing is it? (if wrong, does the decision change?)
        - Is it testable?
        - What evidence supports or challenges it?
        - Is it implicit or explicit?
        """
        assumptions = [n for n in graph['nodes'] if n['node_type'] == 'assumption']
        if not assumptions:
            return []

        assessments = []
        for assumption in assumptions:
            # Find supporting/contradicting edges
            related_edges = [e for e in graph['edges']
                           if e['source_node'] == assumption['id']
                           or e['target_node'] == assumption['id']]

            assessments.append(AssumptionAssessment(
                node_id=assumption['id'],
                content=assumption['content'],
                load_bearing=assumption.get('properties', {}).get('load_bearing', False),
                supporting_evidence=len([e for e in related_edges if e['edge_type'] == 'supports']),
                contradicting_evidence=len([e for e in related_edges if e['edge_type'] == 'contradicts']),
                testable=assumption.get('properties', {}).get('testable', True),
                implicit=assumption.get('properties', {}).get('implicit', False),
            ))

        return assessments

    async def _identify_key_tensions(self, case: Case, graph: dict) -> list[TensionSummary]:
        """Identify the most decision-critical tensions."""
        tensions = [n for n in graph['nodes'] if n['node_type'] == 'tension']
        contradicts_edges = [e for e in graph['edges'] if e['edge_type'] == 'contradicts']

        # Rank by relevance to decision
        # Tensions that involve high-importance claims are more critical

        return [TensionSummary(
            node_id=t['id'],
            content=t['content'],
            status=t['status'],
            involved_nodes=[...],  # Nodes connected to this tension
        ) for t in tensions]

    def _assess_evidence_coverage(self, graph: dict, health: dict) -> EvidenceCoverage:
        """How well-supported are the claims?"""
        claims = [n for n in graph['nodes'] if n['node_type'] == 'claim']
        evidence = [n for n in graph['nodes'] if n['node_type'] == 'evidence']

        unsupported_claims = []
        for claim in claims:
            supporting_edges = [e for e in graph['edges']
                              if e['target_node'] == claim['id']
                              and e['edge_type'] == 'supports']
            if not supporting_edges:
                unsupported_claims.append(claim)

        return EvidenceCoverage(
            total_claims=len(claims),
            supported_claims=len(claims) - len(unsupported_claims),
            unsupported_claims=unsupported_claims,
            total_evidence=len(evidence),
            evidence_per_claim=len(evidence) / max(len(claims), 1),
        )

    def _compute_readiness(self, analysis: CaseAnalysis) -> DecisionReadiness:
        """Overall assessment: is this decision ready to be made?"""
        issues = []

        if analysis.blind_spots:
            issues.append(f"{len(analysis.blind_spots)} blind spots identified")

        untested_assumptions = [a for a in analysis.assumption_assessment
                               if a.load_bearing and not a.supporting_evidence]
        if untested_assumptions:
            issues.append(f"{len(untested_assumptions)} load-bearing untested assumptions")

        unresolved_tensions = [t for t in analysis.key_tensions if t.status != 'resolved']
        if unresolved_tensions:
            issues.append(f"{len(unresolved_tensions)} unresolved tensions")

        if analysis.evidence_coverage.unsupported_claims:
            issues.append(f"{len(analysis.evidence_coverage.unsupported_claims)} unsupported claims")

        return DecisionReadiness(
            ready=len(issues) == 0,
            issues=issues,
            confidence=max(0, 1 - (len(issues) * 0.15)),
        )
```

### Phase 4: Wire Into Case Creation Flow

#### 4.1 Modify Case Creation

**File:** `backend/apps/cases/services.py` (modify)

```python
async def create_case(self, user, title, position="", stakes=MEDIUM,
                      thread_id=None, project_id=None, decision_question=""):
    # ... existing case creation ...

    # REMOVE: auto_pull_project_nodes (no longer extracting at project level)
    # OLD: GraphService().auto_pull_project_nodes(case)

    # NEW: Schedule case extraction pipeline (async)
    schedule_async(self._run_case_extraction_pipeline(case))

    return case, brief

async def _run_case_extraction_pipeline(self, case: Case):
    """The full case extraction pipeline. Runs async after case creation."""

    # Step 1: Retrieve relevant chunks
    retriever = CaseChunkRetriever()
    chunks = retriever.retrieve_relevant_chunks(case, max_chunks=50)

    # Step 2: Extract with objective
    extractor = CaseExtractionService()
    extraction_result = await extractor.extract_case_graph(case, chunks)

    # Step 3: Analyze
    analyzer = CaseAnalysisService()
    analysis = await analyzer.analyze_case(case)

    # Step 4: Store analysis results (could be in case metadata or separate model)
    case.metadata['extraction_result'] = {
        'node_count': extraction_result.node_count,
        'edge_count': extraction_result.edge_count,
        'chunk_count': extraction_result.chunk_count,
        'analysis': {
            'blind_spots': [bs.to_dict() for bs in analysis.blind_spots],
            'assumption_count': len(analysis.assumption_assessment),
            'tension_count': len(analysis.key_tensions),
            'readiness': analysis.readiness.to_dict(),
        }
    }
    case.save(update_fields=['metadata'])

    # Step 5: Emit event for frontend (SSE or polling)
    emit_event('CASE_EXTRACTION_COMPLETE', {
        'case_id': str(case.id),
        'node_count': extraction_result.node_count,
        'analysis_summary': analysis.readiness.to_dict(),
    })
```

#### 4.2 Modify create_case_from_analysis (Chat → Case Bridge)

**File:** `backend/apps/cases/services.py` (modify)

```python
async def create_case_from_analysis(self, user, analysis, thread_id,
                                     correlation_id, user_edits=None):
    # ... existing case creation + brief + inquiries + plan ...

    # NEW: Transfer companion state
    companion_state = analysis.get('companion_state', {})
    if companion_state:
        case.metadata['companion_origin'] = companion_state

    # NEW: Transfer research results as working documents
    if thread_id:
        from apps.chat.models import ResearchResult
        research_results = ResearchResult.objects.filter(
            thread_id=thread_id,
            status='complete',
        )
        for result in research_results:
            WorkingDocumentService().create_working_document(
                case=case,
                document_type='research',
                title=f"Research: {result.question}",
                content_markdown=self._format_research_as_markdown(result),
                generated_by_ai=True,
                agent_type='research',
            )

    case.save(update_fields=['metadata'])

    # NEW: Schedule extraction pipeline (includes companion context)
    schedule_async(self._run_case_extraction_pipeline(case))

    return case, brief, inquiries, plan
```

### Phase 5: Progressive Loading Frontend

#### 5.1 Case Extraction Progress View

**File:** `frontend/src/components/workspace/case/CaseExtractionProgress.tsx` (new)

When a case is created, the user shouldn't stare at a loading screen. They should see:
1. **Immediately**: The case brief, decision question, relevant themes from the project
2. **After ~3s**: Source material (relevant chunks) start appearing
3. **After ~10-15s**: Graph nodes appear progressively
4. **After ~20-30s**: Analysis results (blind spots, assumptions, readiness)

```typescript
interface CaseExtractionProgressProps {
  caseId: string;
  extractionStatus: ExtractionStatus;
  onComplete: () => void;
}

type ExtractionStatus =
  | { phase: 'retrieving'; message: 'Finding relevant source material...' }
  | { phase: 'extracting'; message: 'Analyzing sources for your decision...'; progress: number }
  | { phase: 'analyzing'; message: 'Identifying blind spots and tensions...' }
  | { phase: 'complete'; summary: ExtractionSummary }

// Renders animated progress phases like the existing ProjectSummaryView generating state:
// Phase 1: "Reading documents..." ✓
// Phase 2: "Extracting claims and evidence..." (in progress)
// Phase 3: "Analyzing assumptions and tensions..."
// Phase 4: "Assessing decision readiness..."
```

#### 5.2 Update Case Home to Show Analysis

**File:** `frontend/src/components/workspace/case/CaseHome.tsx` (modify)

After extraction completes, the case home shows:

1. **Decision Question** (existing)
2. **Graph** (existing — GraphCanvas with case-scoped nodes)
3. **Analysis Panel** (new):
   - Decision readiness indicator (ready / not ready + reasons)
   - Blind spots list (expandable, actionable)
   - Assumption quality (load-bearing untested assumptions highlighted)
   - Key tensions (linked to tension nodes in graph)
   - Evidence coverage (% of claims supported)

```typescript
interface CaseAnalysisPanel {
  readiness: {
    ready: boolean;
    confidence: number;
    issues: string[];
  };
  blindSpots: Array<{
    description: string;
    severity: 'high' | 'medium' | 'low';
    suggestedAction: string;
  }>;
  assumptions: Array<{
    nodeId: string;
    content: string;
    loadBearing: boolean;
    tested: boolean;
    supportingEvidence: number;
  }>;
  tensions: Array<{
    nodeId: string;
    content: string;
    status: string;
    involvedNodes: string[];
  }>;
  evidenceCoverage: {
    totalClaims: number;
    supportedClaims: number;
    unsupportedClaims: Array<{ nodeId: string; content: string }>;
  };
}
```

#### 5.3 TypeScript Types

**File:** `frontend/src/lib/types/case.ts` (extend)

```typescript
interface CaseExtractionMeta {
  node_count: number;
  edge_count: number;
  chunk_count: number;
  analysis: {
    blind_spots: BlindSpot[];
    assumption_count: number;
    tension_count: number;
    readiness: DecisionReadiness;
  };
}

interface BlindSpot {
  description: string;
  severity: 'high' | 'medium' | 'low';
  suggested_action: string;
  relevant_theme_ids?: string[];  // From project hierarchy
}

interface DecisionReadiness {
  ready: boolean;
  confidence: number;
  issues: string[];
}
```

#### 5.4 API Endpoints

**File:** `backend/apps/cases/views.py` (add/modify endpoints)

```
GET /api/cases/{case_id}/extraction-status/
  → Returns current extraction pipeline status
  → Polled by frontend during extraction

GET /api/cases/{case_id}/analysis/
  → Returns CaseAnalysis results (blind spots, assumptions, tensions, readiness)

POST /api/cases/{case_id}/re-extract/
  → Re-runs extraction with current chunks + any new documents
  → Useful when user adds documents to the case or project

POST /api/cases/{case_id}/extract-additional/
  → Pull in more chunks (expand search) and extract additional nodes
  → For when the user wants broader coverage
```

**File:** `frontend/src/lib/api/cases.ts` (add methods)

```typescript
casesAPI.getExtractionStatus(caseId: string): Promise<ExtractionStatus>
casesAPI.getAnalysis(caseId: string): Promise<CaseAnalysis>
casesAPI.reExtract(caseId: string): Promise<void>
casesAPI.extractAdditional(caseId: string, options?: { maxChunks: number }): Promise<void>
```

### Phase 6: Incremental Extraction (When Case Evolves)

#### 6.1 Re-extraction on New Evidence

When the user adds documents to the case or project, or when chat reveals new constraints, the case graph should be updated.

**File:** `backend/apps/cases/extraction_service.py` (extend)

```python
async def incremental_extract(
    self,
    case: Case,
    new_chunks: list[DocumentChunk],
    existing_nodes: list[Node],
) -> CaseExtractionResult:
    """Extract from new chunks, aware of existing case graph.

    The prompt includes:
    - The decision question (always)
    - Summaries of existing nodes (so the LLM doesn't duplicate)
    - The new chunks to extract from
    - Instructions to find connections to existing nodes
    """

    prompt = self._build_incremental_extraction_prompt(
        case, new_chunks, existing_nodes
    )
    raw_result = await self._call_extraction_llm(prompt)

    # Create new nodes and edges
    # Also create edges between new nodes and existing nodes
    # Emit GraphDelta with incremental patch
```

#### 6.2 Companion-Triggered Re-extraction

When the chat companion (Plan 2) discovers new constraints or the user reveals information that changes the case, the companion can trigger a re-analysis:

```python
# In CompanionService (Plan 2):
async def on_case_context_change(self, case_id: uuid.UUID, new_established: list[str]):
    """Called when companion detects new constraints relevant to the case."""
    case = Case.objects.get(id=case_id)

    # Check if new established facts change the extraction context
    existing_constraints = [c['description'] for c in (case.constraints or [])]
    truly_new = [e for e in new_established if e not in existing_constraints]

    if truly_new:
        # Update case constraints
        case.constraints = (case.constraints or []) + [
            {'type': 'companion_discovered', 'description': c} for c in truly_new
        ]
        case.save(update_fields=['constraints'])

        # Re-run analysis with new context (lightweight, no full re-extraction)
        analyzer = CaseAnalysisService()
        await analyzer.analyze_case(case)
```

---

## Migration Path

### From Current Architecture

1. **Keep existing `auto_pull_project_nodes()`** temporarily. If there are already extracted nodes at the project level (from existing projects), cases can still reference them. New cases will use the new extraction pipeline.

2. **Feature flag:** `USE_CASE_LEVEL_EXTRACTION = True/False`. When True, case creation uses the new pipeline. When False, falls back to auto_pull. This allows gradual rollout.

3. **Existing case graphs are unaffected.** Cases that already have nodes keep them. Only new cases use the new extraction.

4. **No database migration needed for existing data.** New models (none specific to this plan beyond what's already in the codebase) are additive.

---

## Dependencies

- **Plan 1 (Hierarchy):** CaseChunkRetriever uses the hierarchy for theme-aware retrieval. If hierarchy isn't built yet, falls back to pure embedding similarity (still works).
- **Plan 2 (Companion):** Companion state transfers to case on creation. If companion isn't built yet, cases still work — just without pre-seeded constraints and research.

---

## Definition of Done

1. Case creation triggers chunk retrieval + objective-driven extraction (not auto_pull_project_nodes)
2. Extraction prompt includes the decision question, constraints, and companion state
3. Extracted nodes are case-scoped with correct provenance
4. Case analysis runs after extraction: blind spots, assumption assessment, tension mapping, evidence coverage, readiness
5. Frontend shows progressive loading during extraction
6. Analysis results visible in case home page
7. Re-extraction works when new documents are added
8. Existing cases and graph visualization are unaffected
9. Feature flag allows gradual rollout
