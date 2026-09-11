#!/usr/bin/env python3
"""Compare raw action JSON with pinned libneedle, without acceptance filters."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MODEL_SHA = 'b43aabfcaf1a6db6acf488076eab71d823c08697c7af4521fc1d174b60ede5ba'
LIB_SHA = '9fa5386d3e3a8ee17914fb23643bc5f5c906b683fa33561e79c5445dd78bc389'


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--binary', type=Path, default=ROOT / '.optimization/needle-parity')
    p.add_argument('--library', type=Path, default=ROOT / '.optimization/assets/libneedle.so')
    p.add_argument('--model', type=Path, default=ROOT / '.optimization/assets/needle2.cact')
    p.add_argument('--fixtures', type=Path, default=ROOT / 'optimization/parity-fixtures.json')
    p.add_argument('--output', type=Path, default=ROOT / 'optimization/results/libneedle-parity.json')
    p.add_argument('--oracle', type=Path, help='Reuse a previous report with identical fixtures and asset hashes')
    args = p.parse_args()
    model = args.model.read_bytes()
    assert hashlib.sha256(model).hexdigest() == MODEL_SHA, 'model hash mismatch'
    assert hashlib.sha256(args.library.read_bytes()).hexdigest() == LIB_SHA, 'library hash mismatch'
    cases = json.loads(args.fixtures.read_text())
    if args.oracle:
        previous = json.loads(args.oracle.read_text())
        assert previous['model_sha256'] == MODEL_SHA and previous['library_sha256'] == LIB_SHA
        assert [r['fixture'] for r in previous['cases']] == cases
        references = [r['official'] for r in previous['cases']]
    else:
        os.environ['NEEDLE_THREADS'] = '1'
        lib = ctypes.CDLL(str(args.library.resolve()))
        lib.needle_load.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        lib.needle_init.argtypes = [ctypes.c_char_p] * 3
        lib.needle_complete.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        weights = ctypes.create_string_buffer(model)
        assert lib.needle_load(weights, len(model)) == 0
        references = []
        for case in cases:
            schema = json.dumps(case['tools'], separators=(',', ':')).encode()
            assert lib.needle_init(case.get('system', '').encode(), schema, b'') >= 0
            lib.needle_reset()
            output = ctypes.create_string_buffer(65536)
            tokens = lib.needle_complete(case['text'].encode(), 384, output, len(output))
            assert tokens >= 0, case
            references.append(json.loads(output.value))
            print('oracle', len(references), '/', len(cases), flush=True)
    payload = ''.join(c.get('system', '') + '\t' + c['text'] + '\t' +
                      json.dumps(c['tools'], separators=(',', ':')) + '\n' for c in cases)
    result = subprocess.run([str(args.binary.resolve()), str(args.model.resolve()), '@-'],
                            input=payload, text=True, capture_output=True, check=True,
                            env={**os.environ, 'NEEDLE_DEBUG_REASON': '1'})
    actual = [json.loads(line.split('\t')[0]) for line in result.stdout.splitlines()
              if line.startswith('[') and not line.startswith('[prof:')]
    assert len(actual) == len(cases), result.stderr
    records = [dict(fixture=c, official=r, actual=a, match=a == r['function_calls'])
               for c, r, a in zip(cases, references, actual)]
    reasoning = iter(re.findall(r'\[reason\] <think>(.*?)</think>', result.stderr, re.S))
    for record in records:
        if record['fixture']['tools']:
            actual_reason = next(reasoning, None)
            record['actual_reasoning'] = actual_reason.strip() if actual_reason is not None else None
            record['reasoning_match'] = record['actual_reasoning'] == record['official']['reasoning'].strip()
    report = dict(model_sha256=MODEL_SHA, library_sha256=LIB_SHA,
                  source_sha256=hashlib.sha256((ROOT / 'needle.c').read_bytes()).hexdigest(),
                  binary_sha256=hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                  cases=records, matched=sum(r['match'] for r in records), total=len(records))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    args.output.with_suffix('.log').write_text(result.stderr)
    for r in records:
        print('MATCH' if r['match'] else 'DIFFER', r['fixture']['text'])
        if not r['match']:
            print('  official:', r['official']['function_calls'], '\n  actual:', r['actual'])
    print(f"{report['matched']}/{report['total']} raw action results match libneedle")
    reasoning_cases = [r for r in records if 'reasoning_match' in r]
    print(f"{sum(r['reasoning_match'] for r in reasoning_cases)}/{len(reasoning_cases)} reasoning results match")
    return 0 if all(r['match'] and r.get('reasoning_match', True) for r in records) else 1


if __name__ == '__main__':
    sys.exit(main())
