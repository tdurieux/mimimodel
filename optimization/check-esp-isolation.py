#!/usr/bin/env python3
"""Preprocess the ESP32 branch; this is not an ESP-IDF firmware build."""
from pathlib import Path
import subprocess
import tempfile
import re
root = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    for name in ['esp_heap_caps.h', 'esp_partition.h', 'esp_timer.h',
                 'freertos/FreeRTOS.h', 'freertos/task.h', 'freertos/semphr.h']:
        file = temp / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('/* Header contents are unnecessary for preprocessing. */\n')
    result = subprocess.run(['gcc', '-E', '-P', '-DESP_PLATFORM', '-D__XTENSA__',
                             '-DNEEDLE_NO_MAIN', '-U__SSE2__', '-I'+str(temp),
                             str(root/'needle.c')], text=True, capture_output=True, check=True)
    source = result.stdout
    for forbidden in ['PhiCache', 'phi_cache[', 'shuffle_matrices', 'shuffle_lut',
                      'cq_integer_cache', 'prefill_window_lo', 'seen[', 'int16_t qi[', 'cq_is_phi(']:
        assert forbidden not in source, forbidden
    assert 'int cap = sink_mode ? atoi(sink_mode) : 160;' in source
    assert 'm->cb2_scale = mx2 / 32767.0f;' in source
    assert 'float q = 32767.0f / mx;' in source
    assert 'acc += (float)d * xs[g] * fp16_to_f32(nrm[g]);' in source
    assert 'y[r] = acc * wscale;' in source
    print('PASS ESP32 excludes desktop caches, query scratch, and repetition bitmap; embedded quantization and prefix cap retained')
