def reproduce(deployment, errors, priority):
    remaining = set(errors)
    records = []
    identities = {}
    corrected = []
    initial_odd = 0

    def insert(order, origin):
        identity = frozenset(order)
        if identity not in identities:
            identities[identity] = len(records)
            records.append((list(order), origin, identity))
        return identities[identity]

    for origin, specification in enumerate(deployment["passes"]):
        permutation = specification["permutation"]
        for start in range(0, len(permutation), specification["block_size"]):
            order = permutation[start:start + specification["block_size"]]
            insert(order, origin)
            if origin == 0:
                initial_odd += sum(position in remaining for position in order) % 2
        while True:
            selected_index = None
            selected_rank = None
            for record_index, (order, record_origin, identity) in enumerate(records):
                if len(identity.intersection(remaining)) % 2 == 0:
                    continue
                rank = (record_origin, len(order), record_index) if priority == "earliest" else (len(order), record_origin, record_index)
                if selected_rank is None or rank < selected_rank:
                    selected_rank, selected_index = rank, record_index
            if selected_index is None:
                break
            order, record_origin, identity = records[selected_index]
            while len(order) > 1:
                midpoint = len(order) // 2
                left_index = insert(order[:midpoint], record_origin)
                right_index = insert(order[midpoint:], record_origin)
                left_record = records[left_index]
                selected_index = left_index if len(left_record[2].intersection(remaining)) % 2 else right_index
                order, record_origin, identity = records[selected_index]
            remaining.remove(order[0])
            corrected.append(order[0])
    assert all(len(identity.intersection(remaining)) % 2 == 0 for order, origin, identity in records)
    assert set(corrected).union(remaining) == set(errors)
    return {"priority": priority, "initial_odd": initial_odd, "corrected": sorted(corrected), "residual": sorted(remaining), "known_blocks": len(records)}
