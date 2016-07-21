import random

import numpy

from bogt import spec


ENABLE_CONTROLS = [
    "chorus_on_off",
    "comp_on_off",
    "delay_on_off",
    "eq_on_off",
    "fx1_on_off",
    "fx2_on_off",
    "od_ds_on_off",
    "pedal_fx_on_off",
    "preamp_a_on_off",
    "preamp_b_on_off",
    "reverb_on_off"
]


TYPE_ENABLED_CONTROLS = {
    "chorus_on_off": "chorus_mode",
    "comp_on_off": "comp_type",
    "delay_on_off": "delay_type",
    "fx1_on_off": "fx1_fx_type",
    "fx2_on_off": "fx2_fx_type",
    "od_ds_on_off": "od_ds_type",
    "pedal_fx_on_off": "pedal_fx_wah_type",
    "preamp_a_on_off": "preamp_a_type",
    "preamp_b_on_off": "preamp_b_type",
    "reverb_on_off": "reverb_type",
}


NESTED_ENABLED_CONTROLS = {
    "fx1_on_off": "fx1_fx_type",
    "fx2_on_off": "fx2_fx_type",
}


REORDERABLE = {
    0: "comp_on_off",
    4: "eq_on_off",
    5: "fx1_on_off",
    6: "fx2_on_off",
    7: "delay_on_off",
    8: "chorus_on_off",
    9: "reverb_on_off",
    10: None,  # accel has no on_off control
    11: "pedal_fx_on_off",
    15: "od_ds_on_off",
}


def normalise_weights(weights):
    weights = [float(w) for w in weights]
    tot = sum(weights)
    weights = [w / tot for w in weights]
    return weights


def weighted_choice(items, weights):
    return numpy.random.choice(items, p=weights)


def mutate_enable(patch):
    control = random.choice(ENABLE_CONTROLS)
    value = patch['params'][control]
    new_value = 0 if value else 1
    patch['params'][control] = new_value
    table = spec.table_for_parameter_key(control)
    print('  %s: %s' % (control, table[new_value]))
    if new_value:
        select_type(patch, control)


def select_type(patch, enable_control):
    if enable_control not in TYPE_ENABLED_CONTROLS:
        return
    control = TYPE_ENABLED_CONTROLS[enable_control]
    table = spec.table_for_parameter_key(control)
    new_value = random.choice(table.keys())
    patch['params'][control] = new_value
    print('  %s: %s' % (control, table[new_value]))


def mutate_reorder(patch):
    fx_chain = spec.table('FX CHAIN')
    positions = patch['params']['chainParams']['positionList']
    fx = None

    # find fx to move which is enabled
    while True:
        fx = random.choice(REORDERABLE.keys())
        enabled_control = REORDERABLE[fx]
        if not enabled_control or patch['params'][enabled_control]:
            break

    fx_name = fx_chain[fx]
    from_pos = positions.index(fx)
    print('  %s:' % fx_name)
    print('    from before: %s' % fx_chain[positions[from_pos + 1]])

    # attempt reorders until a valid one is found
    while True:
        npos = list(positions)
        npos.remove(fx)
        to_pos = random.randint(0, len(npos) - 1)
        npos.insert(to_pos, fx)

        # assertions for a valid pipeline
        # 2:PREAMP A is after 17:DIV1
        if npos.index(2) < npos.index(17):
            break

        # 13:NS1 is 2:PREAMP A plus 1
        if npos.index(13) - 1 != npos.index(2):
            break

        # 18:MIX1_DIV2 is after 13:NS1
        if npos.index(18) < npos.index(13):
            break

        # 3:PREAMP B is after 18:MIX1_DIV2
        if npos.index(3) < npos.index(18):
            break

        # 14:NS2 is 3:PREAMP B plus 1
        if npos.index(14) - 1 != npos.index(3):
            break

        # 19:MIX2 is after 14:NS2
        if npos.index(19) < npos.index(14):
            break

        # 16:USB is last
        if npos.index(16) + 1 != len(npos):
            break

        print('    to   before: %s' % fx_chain[positions[to_pos + 1]])
        chain_params = {'positionList': npos}
        for i in range(0, len(npos)):
            k = 'position%s' % (i + 1)
            chain_params[k] = npos[i]
            print('%s: %s' % (k, npos[i]))

        patch['params']['chainParams'] = chain_params
        return


def mutate_value(patch):
    # find a value to change for an enabled fx
    # frobnicate the bizbaz
    pass


def mutate_assign(patch):
    print('Mutate assign')


mutations = (mutate_enable, mutate_reorder, mutate_value, mutate_assign)


def select_mutations(weights, count):
    global mutations
    unordered = []
    for i in range(count):
        unordered.append(weighted_choice(mutations, weights))
    return sorted(unordered, key=lambda m: mutations.index(m))
