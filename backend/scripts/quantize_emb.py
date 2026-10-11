"""int8-quantise a float dense index (per-vector scale) so the bge-m3 index fits the repository: 29.9k × 1024 → ~31 MB.
Usage: python scripts/quantize_emb.py var/emb/scope_emb_bgem3.npy data/corpus/scope_emb_bgem3.i8.npy"""
import json, shutil, sys
import numpy as np
src, dst = sys.argv[1], sys.argv[2]
x = np.load(src).astype("float32")
scale = np.abs(x).max(axis=1)
scale[scale == 0] = 1
q = np.round(x / scale[:, None] * 127).astype("int8")
np.save(dst, q)
np.save(dst.replace(".i8.npy", ".scale.npy"), scale.astype("float16"))
shutil.copy(src.replace(".npy", "_ids.json"), dst.replace(".i8.npy", "_ids.json"))
back = q.astype("float32") * (scale[:, None] / 127)
cos = (back * x).sum(1) / (np.linalg.norm(back, axis=1) * np.linalg.norm(x, axis=1))
print(f"{x.shape} → {dst}; mean cosine to original {cos.mean():.5f}, min {cos.min():.5f}")
