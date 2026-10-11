"""
SpecSure as a Model Context Protocol (MCP) server.

Any MCP-capable AI assistant (Claude Desktop, IDE agents, GeM-side copilots …) can call SpecSure's
*deterministic* tender tools instead of guessing: the assistant converses, SpecSure proves.

Run (stdio):        python mcp_server.py
Claude Desktop config:
  {"mcpServers": {"specsure": {"command": "python", "args": ["<path>/backend/mcp_server.py"]}}}

Uses the curated seed knowledge base, so it works fully offline.
"""
import json
import os
import sys
from datetime import date
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:  # MCP Python SDK v2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # v1
    from mcp.server.fastmcp import FastMCP as _Server  # type: ignore

from app.engine import equivalence
from app.engine.compiler import compile_ir
from app.engine.constraints import Atom, verify
from app.engine.docparse import parse_text
from app.engine.kb import seed_kb
from app.engine.temporal import resolve
from app.engine.tender_ir import build_ir
from app.engine.sarif import to_sarif

server = _Server(name="specsure", instructions=(
    "SpecSure tender-intelligence tools for Indian public procurement. Results are deterministic and cite clauses; "
    "always show the clause references to the user and treat outputs as decision support, not legal determinations."))


@server.tool(description="Lint a tender / specification text: findings with rule IDs, severities, clause references and fixes.")
def lint_tender(text: str, as_of: Optional[str] = None) -> str:
    tw = compile_ir(build_ir(parse_text(text, "mcp_input.txt"), doc_type="tender"), seed_kb(),
                    as_of=date.fromisoformat(as_of) if as_of else None, market=True)
    out = {"readiness": tw["readiness"]["score"], "gate": tw["readiness"]["gate"],
           "findings": [{k: f[k] for k in ("rule_id", "severity", "clause_key", "message", "suggestion")} for f in tw["findings"]]}
    return json.dumps(out, indent=1)


@server.tool(description="Lint a tender and return SARIF 2.1.0 JSON.")
def lint_tender_sarif(text: str) -> str:
    return json.dumps(to_sarif(compile_ir(build_ir(parse_text(text, "mcp_input.txt"), doc_type="tender"), seed_kb())))


@server.tool(description="Which edition / amendments / QCOs of an Indian Standard applied on a given date (YYYY-MM-DD)?")
def resolve_standard(citation: str, as_of: Optional[str] = None) -> str:
    r = resolve(seed_kb(), citation, date.fromisoformat(as_of) if as_of else date.today())
    return json.dumps({k: r.to_dict()[k] for k in ("citation", "status", "replacement", "explanation", "amendments_in_force", "regulations_in_force")}, indent=1)


@server.tool(description="Formally check numeric requirements for contradictions. constraints: JSON list of "
                          "{id, parameter (e.g. steel.yield_strength), min, max, clause}.")
def check_contradictions(constraints_json: str) -> str:
    cons = json.loads(constraints_json)
    atoms = [Atom(c.get("id") or f"C{i}", c["parameter"], "requirement", lo=c.get("min"), hi=c.get("max"), clause_key=c.get("clause"),
                  description=f"{c['parameter']} [{c.get('min')}, {c.get('max')}]") for i, c in enumerate(cons)]
    return json.dumps(verify(atoms).to_dict(), indent=1)


@server.tool(description="Compare two standards/grades parameter-by-parameter (e.g. a='IS 1786', b='BS 4449'). Never concludes equivalence.")
def compare_standards(a: str, b: str, grade_a: Optional[str] = None, grade_b: Optional[str] = None) -> str:
    return json.dumps(equivalence.compare(a, b, grade_a, grade_b, seed_kb()), indent=1)


if __name__ == "__main__":
    server.run()
