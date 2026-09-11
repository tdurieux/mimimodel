#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .optimization
bench_target=${1:-auto}
if [[ "$bench_target" == auto ]]; then
  if rg -q '\bavx\b' /proc/cpuinfo; then bench_target=sandybridge
  elif rg -q '\bssse3\b' /proc/cpuinfo; then bench_target=ssse3
  else bench_target=sse2
  fi
fi
case "$bench_target" in
  sandybridge) flags=(-march=sandybridge -DNEEDLE_SHUFFLE);;
  ssse3) flags=(-march=core2 -DNEEDLE_SHUFFLE);;
  sse2) flags=(-march=x86-64);;
  *) echo 'Expected auto, sandybridge, ssse3 or sse2' >&2;exit 2;;
esac
gcc -O3 -ffp-contract=off "${flags[@]}" -g needle.c -lm -o ".optimization/needle-$bench_target"
printf 'Built .optimization/needle-%s\n' "$bench_target"
