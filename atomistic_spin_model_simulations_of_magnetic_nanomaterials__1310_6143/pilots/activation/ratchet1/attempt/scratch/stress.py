from validate import *


def run():
    generator = np.random.default_rng(72)
    for index in range(18):
        count = int(generator.choice([8, 24, 80, 256]))
        easy = float(generator.uniform(.2, .7))
        exchange = float(generator.uniform(.8, 12))
        longitudinal = easy * float(generator.uniform(.025, .8))
        transverse = easy * float(generator.uniform(.02, .20))
        case = generate(count, easy=easy, exchange=exchange, hard=.15,
                        field=(transverse, 0, longitudinal))
        try:
            check_case(f"random{index}", case, connectivity=True)
        except Exception as error:
            print("FAIL", index, error, flush=True)
            Path(f"scratch/failure{index}.json").write_text(json.dumps(case))
    for field in (.03, .06, .09, .12, .18):
        easy = np.r_[np.full(96, .15), np.full(160, .50)]
        case = generate(256, easy=easy, exchange=3, field=(.03, 0, field))
        model = solve.SpinModel(case["exchange_meV"], case["anisotropy_meV"], case["field_meV"], case["minimum_a"], case["minimum_b"])
        planar = solve.PlanarModel(model, model.plane())
        seed = planar.start.copy()
        seed[:96] = planar.finish[:96]
        intermediate = planar.relax(seed, maxiter=2500, safe=True)
        if np.max(abs(solve.wrap(intermediate - planar.finish))) < 1e-3:
            name = "interface_direct"
        else:
            case["minimum_a"] = planar.spins(intermediate).tolist()
            name = "interface_depinning"
        try:
            check_case(name + str(field), case, connectivity=True)
        except Exception as error:
            print("FAIL interface", field, error, flush=True)
            Path(f"scratch/interface{field}.json").write_text(json.dumps(case))


if __name__ == "__main__":
    run()
