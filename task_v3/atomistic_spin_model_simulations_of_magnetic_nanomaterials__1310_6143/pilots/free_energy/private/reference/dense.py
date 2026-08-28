import concurrent.futures
import json
import math

from generate import REFERENCE, ROOT, worker


def main():
    manifest=json.loads((ROOT/"private/challenge_pool/manifest.json").read_text())
    cases=[json.loads((ROOT/entry["path"]).read_text()) for entries in manifest.values() for entry in entries]
    jobs=[(case,math.pi*index/32,chain,"validation",6000,10000)
          for case in cases for index in range(1,16,2) for chain in range(2)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=48) as executor:
        for index,token in enumerate(executor.map(worker,jobs)):
            if index%24 == 0:
                print(token,flush=True)


if __name__ == "__main__":
    main()
