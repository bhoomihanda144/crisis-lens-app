"""Evidence Relationship Graph Builder Module.

Implements CrisisLens API Contract v1.0 Section 4.8.
Produces incident evidence relationship graphs strictly conforming to:
- Nodes: id equals report_id, role in [original, duplicate, forwarded, corroborating, conflicting].
- Edges: directed from later/derived report (source) to earlier/reference report (target).
- Strict provenance integrity: does not blindly classify earliest report as verified original.
- Uncertainty preservation for unknown provenance reports.
- Zero invented relationships: unrelated reports remain disconnected.
- Cycle and self-loop validation using NetworkX.
"""

from datetime import datetime, timezone
import re
from typing import List, Dict, Set, Optional, Tuple
from dateutil import parser as date_parser
import networkx as nx

from ai_engine.schemas.enums import (
    RelationshipType,
    SourceType,
    FreshnessStatus,
)
from ai_engine.schemas.internal import ReportInput
from ai_engine.schemas.analysis import ConflictItem
from ai_engine.schemas.graph import (
    EvidenceNode,
    EvidenceEdge,
    EvidenceGraphResponse,
)
from ai_engine.modules.freshness import FreshnessAnalyzer
from ai_engine.modules.duplicate import (
    DuplicateDetector,
    _extract_tokens,
    _haversine_distance_m,
    STOPWORDS,
    GENERIC_CRISIS_WORDS,
)
from ai_engine.modules.source import SourceIndependenceAnalyzer


class GraphValidationError(ValueError):
    """Raised when evidence graph validation fails (e.g., self-loops, cycles, direction)."""
    pass


def _parse_iso(timestamp_str: str) -> datetime:
    """Parses ISO timestamp string to UTC datetime."""
    try:
        dt = date_parser.parse(timestamp_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _format_excerpt(text: str, max_length: int = 60) -> str:
    """Generates clean preview excerpt according to API Contract conventions."""
    clean = " ".join(text.strip().split())
    if len(clean) > max_length:
        return clean[:max_length] + "..."
    return clean


class EvidenceGraphBuilder:
    """Builder for contract-compliant Evidence Relationship Graphs."""

    @classmethod
    def build_graph(
        cls,
        incident_id: str,
        reports: List[ReportInput],
        conflicts: Optional[List[ConflictItem]] = None,
    ) -> EvidenceGraphResponse:
        """Constructs an EvidenceGraphResponse from reports and explicit conflicts.

        Args:
            incident_id: The ID of the incident being mapped.
            reports: Associated reports.
            conflicts: Explicitly identified conflict items from report analysis.

        Returns:
            EvidenceGraphResponse with nodes and edges.

        Raises:
            GraphValidationError: If self-loops, invalid edge direction, or cycles are found.
        """
        if not reports:
            return EvidenceGraphResponse(
                incident_id=incident_id,
                nodes=[],
                edges=[],
            )

        # 1. Sort reports chronologically (earliest first)
        # Deterministic tie-breaker on report ID
        sorted_reports = sorted(
            reports,
            key=lambda r: (_parse_iso(r.reported_at), r.id),
        )
        reports_by_id: Dict[str, ReportInput] = {r.id: r for r in sorted_reports}

        # Track edges
        edges: List[EvidenceEdge] = []
        edge_pairs: Set[Tuple[str, str]] = set()

        def add_edge(source_id: str, target_id: str, rel_type: RelationshipType, label: str, confidence: float) -> None:
            """Helper to add an edge ensuring uniqueness and invariant checks."""
            if source_id == target_id:
                raise GraphValidationError(
                    f"Self-loop detected on report '{source_id}'. "
                    f"A report cannot reference itself."
                )
            pair = (source_id, target_id)
            if pair in edge_pairs:
                return
            edge_pairs.add(pair)
            edge_id = f"edge_{source_id}_{target_id}_{rel_type.value}"
            edges.append(
                EvidenceEdge(
                    id=edge_id,
                    source=source_id,
                    target=target_id,
                    type=rel_type,
                    label=label,
                    confidence=round(confidence, 2),
                )
            )

        # 2. Process Explicitly Supplied Conflicts
        if conflicts:
            for conflict in conflicts:
                rep_ids = [rid for rid in conflict.report_ids if rid in reports_by_id]
                # Compare each pair of reports in conflict
                for i in range(len(rep_ids)):
                    for j in range(i + 1, len(rep_ids)):
                        r1 = reports_by_id[rep_ids[i]]
                        r2 = reports_by_id[rep_ids[j]]
                        t1 = _parse_iso(r1.reported_at)
                        t2 = _parse_iso(r2.reported_at)
                        # Source is later report, target is earlier report
                        if t2 >= t1:
                            source, target = r2.id, r1.id
                        else:
                            source, target = r1.id, r2.id
                        add_edge(
                            source_id=source,
                            target_id=target,
                            rel_type=RelationshipType.CONFLICTING,
                            label=f"Conflicting: {conflict.topic}",
                            confidence=0.90,
                        )

        # 3. Process Explicit Forwarding & Duplicate Relationships
        for idx, current in enumerate(sorted_reports):
            earlier_reports = sorted_reports[:idx]
            if not earlier_reports:
                continue

            # A. Explicit forwarded_from reference
            if current.forwarded_from and current.forwarded_from in reports_by_id:
                parent = reports_by_id[current.forwarded_from]
                add_edge(
                    source_id=current.id,
                    target_id=parent.id,
                    rel_type=RelationshipType.FORWARDED,
                    label=f"Forwarded from {parent.id}",
                    confidence=1.0,
                )
                continue

            # B. Forwarding text markers (e.g. 'FWD:', 'forwarded message')
            if SourceIndependenceAnalyzer.is_forwarded_text(current.text):
                ref_id = SourceIndependenceAnalyzer.extract_forwarded_reference_id(current.text)
                if ref_id and ref_id in reports_by_id:
                    parent = reports_by_id[ref_id]
                    add_edge(
                        source_id=current.id,
                        target_id=parent.id,
                        rel_type=RelationshipType.FORWARDED,
                        label=f"Forwarded from {parent.id}",
                        confidence=0.95,
                    )
                    continue
                # If no explicit ID in text, look for earlier parent matching text
                fwd_parent = cls._find_forwarded_parent(current, earlier_reports)
                if fwd_parent:
                    add_edge(
                        source_id=current.id,
                        target_id=fwd_parent.id,
                        rel_type=RelationshipType.FORWARDED,
                        label=f"Forwarded copy of {fwd_parent.id}",
                        confidence=0.95,
                    )
                    continue

            # C. Duplicate Detection (via Stage 3 DuplicateDetector)
            dup_info = DuplicateDetector.detect_duplicates(
                report=current,
                context_reports=earlier_reports,
                duplicate_threshold=0.55,
            )
            has_dup_edge = False
            if dup_info.is_duplicate:
                for match in dup_info.matches:
                    if match.similarity >= 0.55:
                        add_edge(
                            source_id=current.id,
                            target_id=match.report_id,
                            rel_type=RelationshipType.DUPLICATE,
                            label=f"Duplicate ({match.similarity:.2f})",
                            confidence=match.similarity,
                        )
                        has_dup_edge = True
            if has_dup_edge:
                continue

            # D. Defensible Corroboration Detection
            # Only evaluate if current has not already been linked as forwarded or duplicate
            corrob_match = cls._find_corroborating_report(current, earlier_reports, edge_pairs)
            if corrob_match:
                target_id, corrob_score, corrob_label = corrob_match
                add_edge(
                    source_id=current.id,
                    target_id=target_id,
                    rel_type=RelationshipType.CORROBORATING,
                    label=corrob_label,
                    confidence=corrob_score,
                )

        # 4. Determine Node Roles & Labels (Preserving Provenance Integrity)
        nodes: List[EvidenceNode] = []
        outgoing_by_node: Dict[str, List[EvidenceEdge]] = {r.id: [] for r in sorted_reports}
        incoming_by_node: Dict[str, List[EvidenceEdge]] = {r.id: [] for r in sorted_reports}

        for edge in edges:
            if edge.source in outgoing_by_node:
                outgoing_by_node[edge.source].append(edge)
            if edge.target in incoming_by_node:
                incoming_by_node[edge.target].append(edge)

        for rep in sorted_reports:
            outgoing = outgoing_by_node[rep.id]
            incoming = incoming_by_node[rep.id]

            # Determine Role
            role: RelationshipType
            is_verified_original = False

            # Check outgoing edge types
            outgoing_types = [e.type for e in outgoing]
            if RelationshipType.FORWARDED in outgoing_types:
                role = RelationshipType.FORWARDED
            elif RelationshipType.DUPLICATE in outgoing_types:
                role = RelationshipType.DUPLICATE
            elif RelationshipType.CONFLICTING in outgoing_types:
                role = RelationshipType.CONFLICTING
            elif RelationshipType.CORROBORATING in outgoing_types:
                role = RelationshipType.CORROBORATING
            elif rep.provenance and rep.provenance.strip().lower() in ["forwarded"]:
                role = RelationshipType.FORWARDED
            elif rep.provenance and rep.provenance.strip().lower() in ["corroborating"]:
                role = RelationshipType.CORROBORATING
            elif incoming:
                # Other reports derive from or reference this report -> Defensible original reference
                role = RelationshipType.ORIGINAL
                is_verified_original = True
            elif rep.provenance and rep.provenance.strip().lower() in [
                "original", "firsthand", "verified_original", "primary", "verified"
            ]:
                # Explicit verifiable provenance establishes original
                role = RelationshipType.ORIGINAL
                is_verified_original = True
            else:
                # Standalone report with unestablished / unknown provenance
                # Assign contract role 'original' as candidate source,
                # but preserve uncertainty in label and do not mark verified.
                role = RelationshipType.ORIGINAL
                is_verified_original = False

            # Format Node Label
            source_cap = rep.source_type.capitalize()
            loc_label = rep.location_label or "Unknown"

            if role == RelationshipType.ORIGINAL:
                if is_verified_original:
                    label = f"{source_cap}: {loc_label}"
                else:
                    # Preserve uncertainty for unverified provenance
                    label = f"{source_cap} (Unverified): {loc_label}"
            elif role == RelationshipType.FORWARDED:
                label = f"{source_cap} (Forwarded): {loc_label}"
            elif role == RelationshipType.DUPLICATE:
                label = f"{source_cap} (Duplicate): {loc_label}"
            elif role == RelationshipType.CONFLICTING:
                label = f"{source_cap} (Conflicting): {loc_label}"
            else:
                label = f"{source_cap}: {loc_label}"

            # Calculate freshness status
            freshness_info = FreshnessAnalyzer.calculate_freshness(rep.reported_at)
            excerpt = _format_excerpt(rep.text)

            nodes.append(
                EvidenceNode(
                    id=rep.id,
                    report_id=rep.id,
                    label=label,
                    role=role,
                    source_type=SourceType(rep.source_type),
                    source_name=rep.source_name,
                    timestamp=rep.reported_at,
                    excerpt=excerpt,
                    freshness_status=freshness_info.status,
                )
            )

        # 5. NetworkX Graph Topology Validation
        cls.validate_topology(nodes, edges, reports_by_id)

        return EvidenceGraphResponse(
            incident_id=incident_id,
            nodes=nodes,
            edges=edges,
        )

    @classmethod
    def validate_topology(
        cls,
        nodes: List[EvidenceNode],
        edges: List[EvidenceEdge],
        reports_by_id: Dict[str, ReportInput],
    ) -> None:
        """Validates evidence graph topology using NetworkX.

        Enforces:
        - No self-loops (source != target).
        - Edge direction: source (later/derived) -> target (earlier/reference).
        - Directed Acyclic Graph (DAG): cycle detection raises GraphValidationError.
        """
        g = nx.DiGraph()
        for node in nodes:
            g.add_node(node.id)

        for edge in edges:
            if edge.source == edge.target:
                raise GraphValidationError(
                    f"Self-loop detected on report '{edge.source}'. "
                    f"Edge '{edge.id}' cannot have identical source and target."
                )

            src_rep = reports_by_id.get(edge.source)
            tgt_rep = reports_by_id.get(edge.target)
            if src_rep and tgt_rep:
                src_dt = _parse_iso(src_rep.reported_at)
                tgt_dt = _parse_iso(tgt_rep.reported_at)
                if src_dt < tgt_dt:
                    raise GraphValidationError(
                        f"Invalid edge direction for edge '{edge.id}': "
                        f"source '{edge.source}' ({src_rep.reported_at}) is earlier than target '{edge.target}' ({tgt_rep.reported_at}). "
                        f"Edges must point from later/derived report to earlier/reference report."
                    )

            g.add_edge(edge.source, edge.target, edge_id=edge.id, type=edge.type.value)

        if not nx.is_directed_acyclic_graph(g):
            cycles = list(nx.simple_cycles(g))
            cycle_desc = " -> ".join(cycles[0] + [cycles[0][0]]) if cycles else "cycle"
            raise GraphValidationError(
                f"Cycle detected in evidence graph: {cycle_desc}. "
                f"Evidence relationships must form a Directed Acyclic Graph (DAG)."
            )

    @staticmethod
    def _find_forwarded_parent(
        report: ReportInput,
        earlier_reports: List[ReportInput],
    ) -> Optional[ReportInput]:
        """Finds an earlier report that served as the parent of a forwarded text."""
        tokens_target = _extract_tokens(report.text)
        for earlier in reversed(earlier_reports):
            tokens_earlier = _extract_tokens(earlier.text)
            if not tokens_earlier:
                continue
            intersection = tokens_target.intersection(tokens_earlier)
            # Check if majority of earlier report text is present in the forwarded text
            ratio = len(intersection) / len(tokens_earlier)
            if ratio >= 0.70:
                return earlier
        return None

    @staticmethod
    def _find_corroborating_report(
        report: ReportInput,
        earlier_reports: List[ReportInput],
        existing_pairs: Set[Tuple[str, str]],
    ) -> Optional[Tuple[str, float, str]]:
        """Identifies defensible independent corroboration between report and earlier reports.

        Strict Guardrails:
        - Never infer independent corroboration from source_type or source_name alone.
        - Neither report can be forwarded.
        - Must have meaningful topical/event overlap and location consistency.
        - Sources must be distinct.
        """
        if bool(report.forwarded_from) or SourceIndependenceAnalyzer.is_forwarded_text(report.text):
            return None

        tokens_target = _extract_tokens(report.text)
        content_tokens_target = tokens_target - STOPWORDS - GENERIC_CRISIS_WORDS

        for earlier in reversed(earlier_reports):
            if (report.id, earlier.id) in existing_pairs or (earlier.id, report.id) in existing_pairs:
                continue

            # Cannot corroborate if earlier was forwarded copy
            if bool(earlier.forwarded_from) or SourceIndependenceAnalyzer.is_forwarded_text(earlier.text):
                continue

            # Must have distinct sources
            if report.source_name.strip().lower() == earlier.source_name.strip().lower():
                continue

            # Location consistency check
            same_location = False
            if report.location_label and earlier.location_label:
                loc_a = report.location_label.strip().lower()
                loc_b = earlier.location_label.strip().lower()
                if loc_a == loc_b or loc_a in loc_b or loc_b in loc_a:
                    same_location = True

            if not same_location and report.lat is not None and report.lng is not None and earlier.lat is not None and earlier.lng is not None:
                dist = _haversine_distance_m(report.lat, report.lng, earlier.lat, earlier.lng)
                if dist <= 1000:
                    same_location = True

            # If completely different locations, they do not corroborate
            if not same_location:
                continue

            # Content overlap check
            tokens_earlier = _extract_tokens(earlier.text)
            content_tokens_earlier = tokens_earlier - STOPWORDS - GENERIC_CRISIS_WORDS

            shared_content = content_tokens_target.intersection(content_tokens_earlier)
            all_shared = tokens_target.intersection(tokens_earlier)

            # Require shared specific content tokens OR substantial keyword overlap
            has_meaningful_content = len(shared_content) >= 1 or len(all_shared) >= 3

            if not has_meaningful_content:
                continue

            # Calculate corroboration score
            overlap_ratio = len(all_shared) / max(1, len(tokens_target.union(tokens_earlier)))
            corrob_score = min(0.85, max(0.65, overlap_ratio + 0.55))

            # Credibility boost for official/sensor/responder sources
            if report.source_type in ["official", "sensor", "responder"]:
                corrob_score = min(0.90, corrob_score + 0.10)

            label = f"Corroborating: {report.source_type.capitalize()} corroboration"
            return (earlier.id, corrob_score, label)

        return None
