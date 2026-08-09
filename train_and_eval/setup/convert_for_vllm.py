"""Convert an unsloth-saved gemma-4-E2B checkpoint for serving in vLLM 0.26.

vLLM's Gemma4 arch expects:
  1. keys under `language_model.model.*` (HF/unsloth save them as
     `model.language_model.*`) — rename the prefix;
  2. a `k_norm` weight on EVERY decoder layer — HF's checkpoint only stores them on the
     non-shared layers (text_config.num_kv_shared_layers=20 → 15 unique, layers 15-34
     share with layer % 15). Duplicate from the source layer.

Usage:
  python convert_for_vllm.py --src /root/cadqa-sft-merged --dst /root/cadqa-sft-merged-vllm
  vllm serve /root/cadqa-sft-merged-vllm   # or LLM(model=...)
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from safetensors.torch import load_file, save_file

_PREFIX_RENAMES = (
    ("model.language_model.", "language_model.model."),
    ("model.vision_tower.", "vision_tower."),
    ("model.audio_tower.", "audio_tower."),
)


def rename_key(key: str) -> str:
    for old, new in _PREFIX_RENAMES:
        if key.startswith(old):
            return new + key[len(old):]
    return key


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--dst", type=Path, required=True)
    ap.add_argument("--unique-kv-layers", type=int, default=15,
                    help="text_config.num_hidden_layers - num_kv_shared_layers")
    args = ap.parse_args()

    os.makedirs(args.dst, exist_ok=True)
    for fn in os.listdir(args.src):
        if not fn.endswith(".safetensors"):
            shutil.copy(os.path.join(args.src, fn), os.path.join(args.dst, fn))

    tensors = load_file(str(args.src / "model.safetensors"))
    out = {rename_key(k): v for k, v in tensors.items()}
    n = len(out)

    # duplicate shared-layer k_norm (layers >= unique count share with layer % unique)
    added = 0
    layer_keys = [k for k in out if ".self_attn.k_norm.weight" in k]
    if layer_keys:
        max_layer = max(int(k.split(".layers.")[1].split(".")[0]) for k in layer_keys)
        for layer in range(args.unique_kv_layers, max_layer + 1):
            key = f"language_model.model.layers.{layer}.self_attn.k_norm.weight"
            if key not in out:
                src_key = f"language_model.model.layers.{layer % args.unique_kv_layers}.self_attn.k_norm.weight"
                if src_key in out:
                    out[key] = out[src_key].clone()
                    added += 1

    save_file(out, str(args.dst / "model.safetensors"))
    print(f"converted {n} tensors (+{added} shared k_norm) -> {args.dst}")


if __name__ == "__main__":
    main()
