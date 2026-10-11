"""
Step 6 (optional): dense index over "title + scope clause" of every standard, with the corpus embedding model
(settings.CORPUS_EMBEDDING_MODEL, default intfloat/multilingual-e5-small). Output: var/corpus/scope_emb.npy (float16)
and scope_emb_ids.json. Multilingual model → Hindi / Tamil / … queries match English standards directly.
"""
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def main():
    import argparse
    import numpy as np
    from app.services.corpus_service import EMB, EMB_IDS, Corpus, corpus_model, passage_prefix
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="override CORPUS_EMBEDDING_MODEL (e.g. BAAI/bge-m3)")
    ap.add_argument("--out", default=None, help="output .npy (ids file written next to it)")
    ap.add_argument("--max-seq", type=int, default=256)
    ap.add_argument("--append-missing", action="store_true", help="embed only standards missing from the existing output (e.g. new BIS-portal titles)")
    a = ap.parse_args()
    out, out_ids = (a.out, a.out.replace(".npy", "_ids.json")) if a.out else (EMB, EMB_IDS)
    c = Corpus().load()
    if a.model:
        from sentence_transformers import SentenceTransformer
        m, name = SentenceTransformer(a.model, device="cpu"), a.model
    else:
        from app.config import settings
        m, name = corpus_model(), settings.CORPUS_EMBEDDING_MODEL
    if m is None:
        print("corpus embedding model disabled/unavailable")
        return
    m.max_seq_length = a.max_seq
    ids = c.docs
    prev_vecs, prev_ids = None, []
    if a.append_missing and os.path.exists(out) and os.path.exists(out_ids):
        prev_vecs, prev_ids = np.load(out), json.load(open(out_ids))
        have = set(prev_ids)
        ids = [b for b in c.docs if b not in have]
        print(f"{len(ids)} standards to add to {len(prev_ids)} already embedded", flush=True)
    texts = []
    for b in ids:
        latest = c.catalogue[b][-1]
        g = c.graph.get(b) or {}
        texts.append(passage_prefix(name) + f"{b} {latest['title']}. {(g.get('scope') or '')[:600]}")
    t0 = time.time()
    parts = []
    for i in range(0, len(texts), 256):
        parts.append(m.encode(texts[i:i + 256], batch_size=32, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True))
        print(f"{i + 256}/{len(texts)} {time.time() - t0:.0f}s", flush=True)
    vecs = np.concatenate(parts) if parts else np.zeros((0, 1), dtype="float16")
    if prev_vecs is not None and len(ids):
        vecs = np.concatenate([prev_vecs.astype("float16"), vecs.astype("float16")])
        ids = prev_ids + ids
    elif prev_vecs is not None:
        print("nothing to add"); return
    np.save(out, vecs.astype("float16"))
    json.dump(ids, open(out_ids, "w"))
    print(f"embedded {len(ids)} standards with {name} in {time.time() - t0:.0f}s → {out}")


if __name__ == "__main__":
    main()
