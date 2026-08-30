from variants import ExactPolicy


class BalancedPolicy(ExactPolicy):
    sampler_name = '../sampler2.so'

    def candidate_pool(self, posterior):
        maximum = self.hello['max_matching_size']
        minimum = max(3, (maximum+1)//2) if self.family==1 else (3*maximum+4)//5
        count = 360//(maximum-minimum+1)
        candidates = []
        for size in range(minimum, maximum+1):
            candidates += self.grid.pool(self.generator, count, size, varied=False)
        return candidates


class ShortPolicy(BalancedPolicy):
    depth_multipliers = (0.85, 1.3)
