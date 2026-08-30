import json
import multiprocessing
import os
import resource
import sys


def child(connection):
    connection.send({"affinity": sorted(os.sched_getaffinity(0)), "address_space_limit": resource.getrlimit(resource.RLIMIT_AS), "cpu_limit": resource.getrlimit(resource.RLIMIT_CPU)})
    connection.close()


if __name__ == "__main__":
    parent_connection, child_connection = multiprocessing.Pipe()
    process = multiprocessing.Process(target=child, args=(child_connection,))
    process.start()
    result = {"parent_affinity": sorted(os.sched_getaffinity(0)), "parent_address_space_limit": resource.getrlimit(resource.RLIMIT_AS), "parent_cpu_limit": resource.getrlimit(resource.RLIMIT_CPU), "child": parent_connection.recv()}
    process.join()
    print(json.dumps(result), file=sys.stderr, flush=True)
    for line in sys.stdin:
        print('{"actions":[]}', flush=True)
