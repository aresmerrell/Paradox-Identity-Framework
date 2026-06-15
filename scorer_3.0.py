# PIF 3.0 Scorer - Clean & Runnable
# Full Layer 5 math + examples

class PIF3Scorer:
    def __init__(self):
        self.theta = 0.5
        self.alpha = 0.35
        self.mu = 0.55
        self.gamma = 0.5

    def run(self, payload, i_prior=0.62, l1=0.38):
        d_m = payload['d_m']
        s_p = payload['s_p']
        c_a = payload['c_a']
        v_c = payload['v_c']
        mri = payload['mri']

        # Layer 5 core
        r_so = 0.0 if v_c < 0 else max(0, v_c) * c_a * (s_p * mri)
        i_adj = i_prior + self.alpha * r_so * 0.42 - self.mu * d_m if r_so == 0 else i_prior + self.alpha * r_so * 0.42
        i_final = min(max(0, i_adj), l1 + self.gamma * l1**2)

        return {'r_so': round(r_so, 2), 'i_final': round(i_final, 2), 'verdict': 'Pass' if i_final > 0.4 else 'Fail'}

# Examples
scorer = PIF3Scorer()

negative = {'d_m': 0.65, 's_p': 0.45, 'c_a': 0.15, 'v_c': -0.72, 'mri': 0.85}
positive = {'d_m': 0.68, 's_p': 0.62, 'c_a': 0.78, 'v_c': 0.81, 'mri': 0.88}

print("Negative case:", scorer.run(negative))
print("Positive case:", scorer.run(positive))
