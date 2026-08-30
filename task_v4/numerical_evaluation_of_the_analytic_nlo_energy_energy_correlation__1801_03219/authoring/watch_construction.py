import sys

import watch_tournament


generation = int(sys.argv[1]) if len(sys.argv) > 1 else 2
watch_tournament.ATTEMPTS = [("concept_3",2*generation-1),("concept_3",2*generation)]
watch_tournament.main()
