import random

import numpy

from bogt import spec


class FxInfo(object):

    def __init__(self, name, on_off_param, type_param, pos_code,
                 nested=False):
        self.name = name
        self.on_off_param = on_off_param
        self.type_param = type_param
        self.pos_code = pos_code
        self.nested = nested


class MutateContext(object):

    def __init__(self, patch, fxs, info_out):
        self.patch = patch
        self.fxs = fxs
        self.info_out = info_out
        # set of changed params
        self.changed = set()


FX_INFOS = [
    FxInfo("COMP", "comp_on_off", "comp_type", 0),
    FxInfo("EQ", "eq_on_off", None, 4),
    FxInfo("FX1", "fx1_on_off", "fx1_fx_type", 5, True),
    FxInfo("FX2", "fx2_on_off", "fx2_fx_type", 6, True),
    FxInfo("OD/DS", "od_ds_on_off", "od_ds_type", 15),
    FxInfo("DELAY", "delay_on_off", "delay_type", 7),
    FxInfo("PREAMP A", "preamp_a_on_off", "preamp_a_type", None),
    FxInfo("PREAMP B", "preamp_b_on_off", "preamp_b_type", None),
    FxInfo("REVERB", "reverb_on_off", "reverb_type", 9),
    FxInfo("CHORUS", "chorus_on_off", "chorus_mode", 8),
    FxInfo("PEDAL FX", "pedal_fx_on_off", "pedal_fx_wah_type", 11),
    FxInfo("ACCEL FX", None, None, 10)
]


FX_BY_NAME = dict((f.name, f) for f in FX_INFOS)


FX_NAMES = FX_BY_NAME.keys()


def normalise_weights(weights):
    weights = [float(w) for w in weights]
    tot = sum(weights)
    weights = [w / tot for w in weights]
    return weights


def weighted_choice(items, weights):
    return numpy.random.choice(items, p=weights)


def mutate_enable(ctx):
    fx_with_on_off = [f for f in ctx.fxs
                      if f.on_off_param is not None
                      and f.on_off_param not in ctx.changed]
    if not fx_with_on_off:
        return

    fx = random.choice(fx_with_on_off)
    param = fx.on_off_param
    value = ctx.patch['params'][param]
    new_value = 0 if value else 1
    ctx.patch['params'][param] = new_value
    ctx.changed.add(param)
    table = spec.table_for_parameter_key(param)
    ctx.info_out.write('  %s: %s\n' % (param, table[new_value]))
    if new_value:
        select_type(ctx, fx)


def enable_all(ctx):
    fx_with_on_off = [f for f in ctx.fxs
                      if f.on_off_param is not None
                      and f.on_off_param not in ctx.changed]
    if not fx_with_on_off:
        return

    for fx in fx_with_on_off:
        param = fx.on_off_param
        ctx.patch['params'][param] = 1
        ctx.changed.add(param)
        table = spec.table_for_parameter_key(param)
        ctx.info_out.write('  %s: %s\n' % (param, table[1]))
        select_type(ctx, fx)


def select_type(ctx, fx):
    param = fx.type_param
    if not param or param in ctx.changed:
        return
    table = spec.table_for_parameter_key(param)
    new_value = random.choice(table.keys())
    ctx.patch['params'][param] = new_value
    ctx.changed.add(param)

    ctx.info_out.write('  %s: %s\n' % (param, table[new_value]))


def mutate_reorder(ctx):
    # find fx to move which is enabled
    fx_info_pos = [f for f in ctx.fxs
                   if f.pos_code is not None
                   and f.on_off_param
                   and ctx.patch['params'][f.on_off_param]]
    if not fx_info_pos:
        return

    fx = random.choice(fx_info_pos)

    fx_chain = spec.table('FX CHAIN')
    positions = ctx.patch['params']['chainParams']['positionList']

    fx_name = fx_chain[fx.pos_code]
    from_pos = positions.index(fx.pos_code)

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

        ctx.info_out.write('  order: [')
        if to_pos != 0:
            ctx.info_out.write('%s, ' % fx_chain[npos[to_pos - 1]])
        ctx.info_out.write('*%s*, ' % fx_name)
        ctx.info_out.write('%s]\n' % fx_chain[npos[to_pos + 1]])

        chain_params = {'positionList': npos}
        for i in range(0, len(npos)):
            k = 'position%s' % (i + 1)
            chain_params[k] = npos[i]

        ctx.patch['params']['chainParams'] = chain_params
        return


def mutate_value(ctx):
    # find a value to change for an enabled fx
    enabled_fxs = [f for f in ctx.fxs
                   if f.on_off_param
                   and ctx.patch['params'][f.on_off_param]]
    if not enabled_fxs:
        return
    fx = random.choice(ctx.fxs)

    def frobbable(params):
        for v in params:
            if v['parameter'][0] != fx.name:
                continue
            if v['parameter_key'] == fx.on_off_param:
                continue
            if v['parameter_key'] == fx.type_param:
                continue
            if v['parameter_key'] in ctx.changed:
                continue
            if fx.nested:
                table = spec.table_for_parameter_key(fx.type_param)
                type_value = ctx.patch['params'][fx.type_param]
                type_value_name = table[type_value]
                nested_name = v['parameter'][1]
                if nested_name != type_value_name:
                    continue
            yield v

    # build a list of values which might be frobbed
    b2i = spec.table('BYTENUM TO INDEX')
    patch_params = list(frobbable(spec.patch().values()))
    if not patch_params:
        return

    # choose a param to frob
    patch_param = random.choice(patch_params)
    param_key = patch_param['parameter_key']
    table = spec.table_for_parameter_key(param_key)

    # frobnicate the bizbaz
    new_value = random.choice(table.keys())
    ctx.patch['params'][param_key] = b2i[new_value]
    ctx.changed.add(param_key)
    ctx.info_out.write('  %s: %s\n' % (param_key, table[new_value]))


def mutate_assign(ctx):
    ctx.info_out.write('TODO Mutate assign\n')


def finish_mutate(ctx):
    cons = 'qwrtypsdfghjklzxcvbnm'
    vowels = 'aeiou'
    name = ''
    for i in range(2):
        for j in range(3):
            name += random.choice(cons)
            name += random.choice(vowels)
        name += '  '
    ctx.patch['name'] = name
    ctx.patch['gt100Name1'] = name[:8]
    ctx.patch['gt100Name2'] = name[8:]
    ctx.patch['params']['patchname'] = name
    ctx.patch['id'] = '%010d' % random.randint(1, 9999999999)
    ctx.patch['note'] = ctx.info_out.getvalue()
    ctx.info_out.write('  patchname: %s' % name)


mutations = (
    mutate_enable,
    mutate_reorder,
    mutate_value,
    mutate_assign,
)


def select_mutations(weights, count):
    global mutations
    unordered = []
    for i in range(count):
        unordered.append(weighted_choice(mutations, weights))
    return sorted(unordered, key=lambda m: mutations.index(m))
