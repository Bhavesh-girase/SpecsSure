import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
_db = os.path.join(tempfile.mkdtemp(), "specsure_test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_db}")
os.environ.setdefault("EMBEDDING_MODEL", "none")
os.environ.setdefault("RERANKER_MODEL", "none")
os.environ.setdefault("CORPUS_EMBEDDING_MODEL", "none")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("SEED_DEMO", "1")

import pytest

DEMO = os.path.join(os.path.dirname(__file__), "..", "data", "demo")


def read(name):
    with open(os.path.join(DEMO, name), "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def kb():
    from app.engine.kb import KnowledgeBase
    return KnowledgeBase.from_seed()


@pytest.fixture(scope="session")
def base_ir():
    from app.engine.docparse import parse_document
    from app.engine.tender_ir import build_ir
    return build_ir(parse_document(read("tender_phc_building.txt"), "tender_phc_building.txt"))


@pytest.fixture(scope="session")
def twin(base_ir, kb):
    from app.engine.compiler import compile_ir
    return compile_ir(base_ir, kb)
