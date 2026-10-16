int nb_clamp_i32(int x,int lo,int hi) { return x<lo?lo:x>hi?hi:x; }
int nb_dynamic_v3_core_bonus(const int *counts,int strong) {
    static const int temple_lut[4] = {0, 25, 45, 60};
    static const int wm_lut[3]     = {0, 55, 85};
    static const int ac_lut[5]     = {0, 20, 40, 55, 65};
    static const int sh_lut[3]     = {0, 20, 50};
    static const int om_lut[4]     = {0, 25, 40, 50};
    static const int ba_lut[4]     = {0, 20, 35, 50};
    static const int ft_lut[4]     = {0, 20, 35, 50};
    static const int vi_lut[6]     = {0, 10, 20, 30, 40, 50};
    static const int op_lut[4]     = {0, 15, 30, 40};
    static const int tc_lut[5]     = {0, 10, 18, 25, 30};

    int score = 0;
    score += wm_lut[nb_clamp_i32(counts[0] - 1, 0, 2)];
    score += temple_lut[nb_clamp_i32(counts[1] - 1, 0, 3)];
    score += temple_lut[nb_clamp_i32(counts[2] - 1, 0, 3)];
    score += om_lut[nb_clamp_i32(counts[3] - 1, 0, 3)];
    score += ac_lut[nb_clamp_i32(counts[4] - 2, 0, 4)];
    score += vi_lut[nb_clamp_i32(counts[5] - 6, 0, 5)];
    score += tc_lut[nb_clamp_i32(counts[6] - 8, 0, 4)];
    score += nb_clamp_i32(counts[7] - 8, 0, 4) * 5;
    score += nb_clamp_i32(counts[8] - 4, 0, 4) * 5;
    score += nb_clamp_i32(counts[9] - 10, 0, 10) * 2;
    score += ft_lut[nb_clamp_i32(counts[10] - 1, 0, 3)];
    score += ba_lut[nb_clamp_i32(counts[11] - 2, 0, 3)];
    score += op_lut[nb_clamp_i32(counts[12] - 2, 0, 3)];
    score += sh_lut[nb_clamp_i32(strong - 1, 0, 2)];
    return score;
}
int nb_dynamic_v3_optional(const int *opt_counts) {
    static const int hut_lut[4]   = {0, 30, 50, 60};
    static const int trail_lut[4] = {0, 25, 40, 50};
    static const int igloo_lut[3] = {0, 25, 40};
    static const int or_lut[3]    = {0, 10, 20};
    static const int bt_lut[5]    = {0, 10, 20, 25, 30};

    int score = hut_lut[nb_clamp_i32(opt_counts[0], 0, 3)]
              + igloo_lut[nb_clamp_i32(opt_counts[1], 0, 2)]
              + trail_lut[nb_clamp_i32(opt_counts[2], 0, 3)]
              + or_lut[nb_clamp_i32(opt_counts[3], 0, 2)]
              + bt_lut[nb_clamp_i32(opt_counts[4], 0, 4)];
    return score;
}
int nb_dynamic_v3_biome_bonus(unsigned int bonus) {
    static const int points[10] = {25, 35, 40, 35, 20, 15, 10, 20, 25, 15};
    int score = 0, n_lux = 0;
    for(int i = 0; i < 10; i++) {
        if(bonus & (1u << i)) {
            score += points[i];
            n_lux++;
        }
    }
    if(n_lux >= 7) score += 25;
    else if(n_lux >= 5) score += 10;
    return score;
}