#define NEEDLE_NO_MAIN
#include "../needle.c"
#include <assert.h>

static void test_rounding(void) {
    for (int i = -127; i < 127; i++) {
        float half = i + 0.5f;
        float samples[] = {half, nextafterf(half, -INFINITY),
                           nextafterf(half, INFINITY), (float)i};
        for (unsigned j = 0; j < sizeof samples / sizeof *samples; j++)
            assert(quant_round(samples[j]) == lroundf(samples[j]));
    }
    assert(quant_round(-0.f) == 0);
}

static void test_dot(void) {
    int16_t a[2048], b[2048];
    for (int trial = 0; trial < 5; trial++) {
        int64_t expected = 0;
        for (int i = 0; i < 2048; i++) {
            a[i] = trial == 0 ? 127 : (i * 31 + trial * 7) % 255 - 127;
            b[i] = trial == 0 ? 127 : (i * 17 + trial * 29) % 255 - 127;
            expected += (int32_t)a[i] * b[i];
            if (i == 7 || i == 63 || i == 127 || i == 255 || i == 2047)
                assert(dot_i16(a, b, i + 1) == expected);
        }
    }
}

static void test_empty_grammar(void) {
    NTool tool = {0};
    strcpy(tool.name, "todo");
    ByteGrammar grammar = {0};
    grammar.state = BG_ARRAY_OPEN;
    grammar.tools = &tool;
    grammar.n_tools = grammar.max_calls = 1;
    grammar.tool = grammar.param = -1;
    assert(bg_consume_piece(&grammar, "[]", 2));
    assert(grammar.state == BG_DONE);
    assert(!bg_consume_piece(&grammar, "{}", 2));
    grammar.state = BG_CALL_OPEN;
    grammar.calls = 1;
    assert(!bg_consume_piece(&grammar, "]", 1));
}

static void test_cq(void) {
    static Needle m;
    float scratch[256], input[256], scales[2];
    int16_t quantized[256];
    m.xh = scratch; m.xq[0] = quantized; m.xs[0] = scales;
    m.cb2_scale = .001f; m.cb4_scale = .002f;
    for (unsigned byte = 0; byte < 256; byte++) {
        for (unsigned j = 0; j < 4; j++)
            m.lut2_i16[byte][j] = ((byte >> (j * 2)) & 3) * 84 - 126;
        for (unsigned j = 0; j < 2; j++)
            m.lut4_i16[byte][j] = ((byte >> (j * 4)) & 15) * 16 - 120;
    }
    uint8_t packed[129 * 256 / 2];
    uint16_t norms[258];
    for (unsigned i = 0; i < 258; i++) norms[i] = i % 2 ? 0x3800 : 0x3c00;
    for (unsigned i = 0; i < sizeof packed; i++) packed[i] = i * 113 + 37;
    for (unsigned bits = 2; bits <= 4; bits += 2) {
        CQMat w = {packed, norms, 129, 256, 256, 128, bits};
        for (unsigned trial = 0; trial < 3; trial++) {
            for (unsigned i = 0; i < 256; i++)
                input[i] = trial == 0 ? 0 : ((int)(i * 23 % 101) - 50) * .01f * trial;
            cq_prepare_x(&m, &w, input, scratch);
            float actual[129];
            cq_matvec(&m, &w, scratch, actual);
            for (unsigned row = 0; row < 129; row++) {
                float expected = 0;
                for (unsigned g = 0; g < 2; g++) {
                    int dot = 0;
                    for (unsigned k = 0; k < 128; k++) {
                        unsigned index = row * 256 + g * 128 + k;
                        int weight = bits == 2 ? m.lut2_i16[packed[index / 4]][index % 4]
                                               : m.lut4_i16[packed[index / 2]][index % 2];
                        dot += weight * quantized[g * 128 + k];
                    }
                    expected += (float)dot * scales[g] *
                        (bits == 2 ? m.cb2_scale : m.cb4_scale) * fp16_to_f32(norms[row * 2 + g]);
                }
                assert(actual[row] == expected);
            }
        }
        needle_host_cache_clear();
    }
}

int main(void) {
    test_rounding();
    test_dot();
    test_empty_grammar();
    test_cq();
    puts("PASS rounding boundaries, integer dots, empty calls, CQ2 and CQ4");
}
