import random

import numpy

from bogt import spec


class FxInfo(object):

    def __init__(self, name, control_on_off, control_type, pos_code,
                 nested=False):
        self.name = name
        self.control_on_off = control_on_off
        self.control_type = control_type
        self.pos_code = pos_code
        self.nested = nested


FX_INFOS = [
    FxInfo("COMP", "comp_on_off", "comp_type", 0),
    FxInfo("EQ", "eq_on_off", None, 4),
    FxInfo("FX1", "fx1_on_off", "fx1_fx_type", 5, True),
    FxInfo("FX2", "fx2_on_off", "fx2_fx_type", 6, True),
    FxInfo("OS/DS", "od_ds_on_off", "od_ds_type", 15),
    FxInfo("DELAY", "delay_on_off", "delay_type", 7),
    FxInfo("PREAMP A", "preamp_a_on_off", "preamp_a_type", None),
    FxInfo("PREAMP B", "preamp_b_on_off", "preamp_b_type", None),
    FxInfo("REVERB", "reverb_on_off", "reverb_type", 9),
    FxInfo("CHORUS", "chorus_on_off", "chorus_mode", 8),
    FxInfo("PEDAL FX", "pedal_fx_on_off", "pedal_fx_wah_type", 11),
    FxInfo("ACCEL FX", None, None, 10)
]


def normalise_weights(weights):
    weights = [float(w) for w in weights]
    tot = sum(weights)
    weights = [w / tot for w in weights]
    return weights


def weighted_choice(items, weights):
    return numpy.random.choice(items, p=weights)


def mutate_enable(patch):
    fx_with_on_off = [f for f in FX_INFOS if f.control_on_off is not None]

    fx = random.choice(fx_with_on_off)
    control = fx.control_on_off
    value = patch['params'][control]
    new_value = 0 if value else 1
    patch['params'][control] = new_value
    table = spec.table_for_parameter_key(control)
    print('  %s: %s' % (control, table[new_value]))
    if new_value:
        select_type(patch, fx)


def select_type(patch, fx):
    control = fx.control_type
    if not control:
        return
    table = spec.table_for_parameter_key(control)
    new_value = random.choice(table.keys())
    patch['params'][control] = new_value
    print('  %s: %s' % (control, table[new_value]))


def mutate_reorder(patch):
    fx_chain = spec.table('FX CHAIN')
    positions = patch['params']['chainParams']['positionList']
    fx = None
    fx_info_pos = [f for f in FX_INFOS if f.pos_code is not None]

    # find fx to move which is enabled
    while True:
        fx = random.choice(fx_info_pos)
        enabled_control = fx.control_on_off
        if not enabled_control or patch['params'][enabled_control]:
            break

    fx_name = fx_chain[fx.pos_code]
    from_pos = positions.index(fx.pos_code)
    print('  %s:' % fx_name)
    print('    from before: %s' % fx_chain[positions[from_pos + 1]])

    # attempt reorders until a valid one is found
    while True:
        npos = list(positions)
        npos.remove(fx.pos_code)
        to_pos = random.randint(0, len(npos) - 1)
        npos.insert(to_pos, fx.pos_code)

        # assertions for a valid pipeline

        # don't put back in the same position
        if from_pos == to_pos:
            break

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

        patch['params']['chainParams'] = chain_params
        return


def mutate_value(patch):
    # find a value to change for an enabled fx
    # fx_chain = spec.table('FX CHAIN')
    # while True:
    #     fx = random.choice(REORDERABLE.keys())
    #     enabled_control = REORDERABLE[fx]
    #     if not enabled_control or patch['params'][enabled_control]:
    #         break

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
