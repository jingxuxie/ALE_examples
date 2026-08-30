import argparse
import concurrent.futures
from harness import ROOT, launch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--budget", type=float, default=90)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed-label", default="v4_40")
    args = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(launch, case, "teacher", args.budget,
                               ROOT / "runs" / case / args.seed_label / "state.npz")
                   for case in args.cases]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == "__main__":
    main()
