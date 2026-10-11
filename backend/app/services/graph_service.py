import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
import networkx as nx

from app.models.standard import Standard, StandardStatus
from app.models.requirement import StandardRelation
from app.models.amendment import Amendment
from app.schemas.standard import StandardGraphNode, StandardGraphEdge, StandardGraphResponse

logger = logging.getLogger(__name__)

class GraphService:
    @staticmethod
    async def expand_graph(
        standard_ids: List[int], 
        db: AsyncSession, 
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        BFS traversal of StandardRelation table starting from standard_ids.
        Expands to outgoing and incoming relationships up to max_depth.
        Returns {'nodes': List[StandardGraphNode], 'edges': List[StandardGraphEdge], 'allied_standards': List[Dict]}
        """
        if not standard_ids:
            return {"nodes": [], "edges": [], "allied_standards": []}

        visited_ids: Set[int] = set(standard_ids)
        current_layer_ids: Set[int] = set(standard_ids)
        
        # Load root standards
        stmt = select(Standard).where(Standard.id.in_(standard_ids))
        res = await db.execute(stmt)
        standards_by_id: Dict[int, Standard] = {s.id: s for s in res.scalars().all()}
        
        node_depths: Dict[int, int] = {sid: 0 for sid in standard_ids}
        all_edges_raw: List[Dict[str, Any]] = []
        
        for depth in range(1, max_depth + 1):
            if not current_layer_ids:
                break
                
            # Query relations where from_standard_id or to_standard_id is in current layer
            stmt_rel = (
                select(StandardRelation)
                .where(
                    or_(
                        StandardRelation.from_standard_id.in_(current_layer_ids),
                        StandardRelation.to_standard_id.in_(current_layer_ids)
                    )
                )
            )
            rel_res = await db.execute(stmt_rel)
            relations = rel_res.scalars().all()
            
            next_layer_ids: Set[int] = set()
            for rel in relations:
                # Add to edges list
                edge_dict = {
                    "id": f"e-{rel.from_standard_id}-{rel.to_standard_id}-{rel.relationship_type}",
                    "source": str(rel.from_standard_id),
                    "target": str(rel.to_standard_id),
                    "relationship_type": rel.relationship_type,
                    "clause_reference": rel.clause_reference,
                    "label": rel.relationship_type.replace("_", " ").title()
                }
                if edge_dict not in all_edges_raw:
                    all_edges_raw.append(edge_dict)

                # Collect new unvisited node IDs
                if rel.from_standard_id not in visited_ids:
                    visited_ids.add(rel.from_standard_id)
                    next_layer_ids.add(rel.from_standard_id)
                    node_depths[rel.from_standard_id] = depth
                    
                if rel.to_standard_id not in visited_ids:
                    visited_ids.add(rel.to_standard_id)
                    next_layer_ids.add(rel.to_standard_id)
                    node_depths[rel.to_standard_id] = depth

            if next_layer_ids:
                # Fetch standard details for newly discovered IDs
                stmt_new = select(Standard).where(Standard.id.in_(next_layer_ids))
                new_res = await db.execute(stmt_new)
                for s in new_res.scalars().all():
                    standards_by_id[s.id] = s

            current_layer_ids = next_layer_ids

        # Build response nodes and allied standards list
        nodes: List[StandardGraphNode] = []
        allied_standards: List[Dict[str, Any]] = []

        for sid, std in standards_by_id.items():
            depth = node_depths.get(sid, 0)
            
            # Determine node type for color coding
            if depth == 0:
                node_type = "primary"
            elif std.status in [StandardStatus.SUPERSEDED, StandardStatus.WITHDRAWN]:
                node_type = "superseded"
            else:
                # Classify based on relationship types pointing to this standard
                rel_types = [
                    e["relationship_type"] for e in all_edges_raw 
                    if e["target"] == str(sid)
                ]
                if "test_method" in rel_types:
                    node_type = "test_method"
                elif "safety_requirement" in rel_types:
                    node_type = "safety"
                elif "installation_code" in rel_types:
                    node_type = "installation"
                else:
                    node_type = "allied"

            node = StandardGraphNode(
                id=str(std.id),
                db_id=std.id,
                is_number=std.is_number,
                label=std.is_number,
                title=std.title,
                status=std.status.value if hasattr(std.status, "value") else str(std.status),
                division=std.division_code,
                node_type=node_type,
                depth=depth,
                confidence=1.0 if depth == 0 else 0.85
            )
            nodes.append(node)

            if depth > 0:
                # Find parent IS number from incoming edges
                parent_is = "IS Unknown"
                rel_type = "allied_product"
                clause_ref = None
                for e in all_edges_raw:
                    if e["target"] == str(sid):
                        source_std = standards_by_id.get(int(e["source"]))
                        if source_std:
                            parent_is = source_std.is_number
                        rel_type = e["relationship_type"]
                        clause_ref = e["clause_reference"]
                        break
                        
                allied_standards.append({
                    "id": std.id,
                    "is_number": std.is_number,
                    "title": std.title,
                    "status": std.status.value if hasattr(std.status, "value") else str(std.status),
                    "relationship_type": rel_type,
                    "clause_reference": clause_ref,
                    "parent_is_number": parent_is,
                    "depth": depth
                })

        edges = [StandardGraphEdge(**e) for e in all_edges_raw]
        return {
            "nodes": nodes,
            "edges": edges,
            "allied_standards": allied_standards
        }

    @classmethod
    async def get_standard_graph(
        cls, 
        is_number: str, 
        db: AsyncSession, 
        depth: int = 2
    ) -> Optional[StandardGraphResponse]:
        """Returns the complete relationship graph centered on a specific IS standard."""
        stmt = select(Standard).where(Standard.is_number.ilike(f"%{is_number.strip()}%"))
        res = await db.execute(stmt)
        root_std = res.scalars().first()
        
        if not root_std:
            return None

        expanded = await cls.expand_graph([root_std.id], db, max_depth=depth)
        return StandardGraphResponse(
            root_is_number=root_std.is_number,
            nodes=expanded["nodes"],
            edges=expanded["edges"],
            total_nodes=len(expanded["nodes"]),
            total_edges=len(expanded["edges"])
        )

    @classmethod
    async def find_missing_dependencies(
        cls, 
        cited_is_numbers: List[str], 
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Tender Gap Analyzer Engine:
        Traverses mandatory normative and safety relationships from standards cited in the tender
        and identifies un-cited standards that MUST be adhered to according to BIS norms.
        """
        if not cited_is_numbers:
            return []

        # Find cited standards in DB
        stmt = select(Standard).where(
            or_(*[Standard.is_number.ilike(f"%{num.strip()}%") for num in cited_is_numbers])
        )
        res = await db.execute(stmt)
        cited_standards = res.scalars().all()
        cited_ids = {s.id for s in cited_standards}
        
        missing_gaps = []
        
        for std in cited_standards:
            # Query outgoing mandatory normative and safety relations
            stmt_rel = (
                select(StandardRelation, Standard)
                .join(Standard, StandardRelation.to_standard_id == Standard.id)
                .where(
                    StandardRelation.from_standard_id == std.id,
                    StandardRelation.relationship_type.in_([
                        "normative_reference", "test_method", "safety_requirement", "installation_code"
                    ])
                )
            )
            rel_res = await db.execute(stmt_rel)
            relations = rel_res.all()
            
            for rel, target_std in relations:
                if target_std.id not in cited_ids:
                    missing_gaps.append({
                        "gap_type": "missing_normative_test",
                        "severity": "critical" if rel.relationship_type in ["normative_reference", "safety_requirement"] else "warning",
                        "description": f"Standard {std.is_number} normatively mandates {target_std.is_number} ({target_std.title}) for {rel.relationship_type.replace('_', ' ')}, but it is omitted from the specification.",
                        "suggestion": f"Explicitly include compliance to {target_std.is_number} in tender technical requirements ({rel.clause_reference or 'mandatory clause'}).",
                        "affected_standard": std.is_number,
                        "clause_reference": rel.clause_reference,
                        "mandated_standard": target_std.is_number
                    })
                    
        return missing_gaps

graph_service = GraphService()
