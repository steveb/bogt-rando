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
    select_type(patch, control)


def mutate_reorder(patch):
    print('Mutate reorder')


def mutate_value(patch):
    print('Mutate value')


def mutate_assign(patch):
    print('Mutate assign')


mutations = (mutate_enable, mutate_reorder, mutate_value, mutate_assign)


def select_mutations(weights, count):
    global mutations
    unordered = []
    for i in range(count):
        unordered.append(weighted_choice(mutations, weights))
    return sorted(unordered, key=lambda m: mutations.index(m))
