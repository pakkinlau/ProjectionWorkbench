#!/usr/bin/env python3
"""Reproduce the F.RUV.W3R.B6 repair and deterministic fixture corpus."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from repeat_use_harness.comparator_parity import repair_artifact, synthetic_corpus

def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--corpus-output',type=Path)
    args=parser.parse_args()
    repair=repair_artifact(); corpus=synthetic_corpus()
    assert repair['terminal_disposition']=='COMPARATOR_TIMING_PARITY_REPAIR_IMPLEMENTED_AT_CONTROLLED_FIXTURE_CEILING'
    assert repair['wave4_open'] is False and repair['w3q_requalification_required'] is True
    assert corpus['baseline_timing_parity_receipt']['noncompensatory_pass'] is True
    write(args.output,repair)
    if args.corpus_output: write(args.corpus_output,corpus)
    return 0
if __name__=='__main__': raise SystemExit(main())
