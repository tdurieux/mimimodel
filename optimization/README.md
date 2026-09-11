# Linux libneedle behavior parity

This branch builds on the empty-array and repeated-tool grammar fixes. It matches libneedle 2.0.4's quantization, rounding, repetition penalty, and 32-token prefill window behavior on Linux. The host path caches rowwise int8 MHC weights, about 1.27 MiB for the pinned model. The prefill fix needs one four-byte window boundary.

The regression corpus covers 35 action results and 34 reasoning outputs, including negative examples, repeated calls, custom extraction, and a transcript longer than the attention window. Matching these cases does not establish full API parity. Confidence scoring, validation, and learned retrieval for more than five tools remain outside this implementation.

Run from the repository root on Linux x86-64:

```sh
python3 optimization/prepare.py
gcc -O3 -ffp-contract=off needle.c -lm -o .optimization/needle-parity
python3 optimization/parity.py --oracle optimization/libneedle-oracle.json
```

Omit `--oracle` to regenerate reference responses using the pinned native library. The script checks asset hashes before using either path. Assets come from the pinned Hugging Face revision in `prepare.py`; their license is downloaded alongside them. Generated reports stay in `optimization/results/` and are ignored.

```sh
gcc -O2 bench/test_byte_grammar.c -lm -o .optimization/test-grammar
.optimization/test-grammar
gcc -O2 -fsanitize=address,undefined optimization/test_parity.c -lm -o .optimization/test-parity
.optimization/test-parity
python3 optimization/check-esp-isolation.py
```

Host caches, attention scratch, the repetition bitmap, and the prefill boundary are excluded from ESP32. Its original quantization and 160-token prefix cap remain. The isolation check preprocesses the embedded path with header stubs; it does not replace an ESP-IDF build or hardware test.
