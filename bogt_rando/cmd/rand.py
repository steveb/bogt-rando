import copy
import logging
import os
from StringIO import StringIO

from cliff import command

from bogt import config
from bogt import tsl
from bogt_rando import mutate


class RandCmd(command.Command):
    '''Generate mutated patches from a base patch'''

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(RandCmd, self).get_parser(prog_name)
        parser.add_argument(
            'tsl',
            metavar='<file>',
            help=('Path to TSL file to mutate patches from.')
        )
        parser.add_argument(
            'out',
            metavar='<file>',
            help=('Path to save TSL file of mutated patches.')
        )
        parser.add_argument(
            '--count',
            type=int,
            default=64,
            help=('Number of mutated patches to generate. '
                  '(Default 64)')
        )
        parser.add_argument(
            '--mutations',
            type=int,
            default=10,
            help=('Number of mutations to perform on the base patch. '
                  '(Default 10)')
        )
        parser.add_argument(
            '--weights',
            default='10,20,50,20',
            metavar='<enable,reorder,value,assign>',
            help=('Relative weights for choosing mutation type. '
                  '(Default 10,20,50,20)')
        )
        fx_names = ','.join(mutate.FX_NAMES)
        parser.add_argument(
            '--fx',
            default=fx_names,
            help=('Which effects to mutate. (Default %s)' % fx_names)
        )
        parser.add_argument(
            '--fx-ignore',
            default='',
            help=('Which effects to exclude from mutate.')
        )

        return parser

    def take_action(self, parsed_args):
        self.conf = config.load_config()
        self.tsl = os.path.abspath(parsed_args.tsl)
        self.out = os.path.abspath(parsed_args.out)
        if not os.path.exists(self.tsl) or not os.path.isfile(self.tsl):
            raise Exception('TSL file not found: %s' % self.tsl)
        self.liveset = tsl.load_tsl_from_file(parsed_args.tsl, self.conf)
        self.count = parsed_args.count
        self.mutations = parsed_args.mutations
        self.weights = mutate.normalise_weights(parsed_args.weights.split(','))
        fx_names = parsed_args.fx.split(',')
        if parsed_args.fx_ignore:
            fxi = parsed_args.fx_ignore.split(',')
            for f in fxi:
                if f in fx_names:
                    fx_names.remove(f)
        self.fx = [f for f in mutate.FX_INFOS if f.name in fx_names]
        new_liveset = self.mutate_liveset()
        new_liveset.store()

    def mutate_liveset(self):
        count = 0
        out = tsl.LiveSet(self.conf, path=self.out)

        while True:
            for name, patch in self.liveset.patches.items():
                count += 1
                if count > self.count:
                    return out
                result = copy.deepcopy(patch)

                info_out = StringIO()
                info_out.write('Mutating "%s"\n' % patch['name'])
                ctx = mutate.MutateContext(result, self.fx, info_out)

                # If specific fx are selected, make sure they are enabled
                if len(self.fx) != len(mutate.FX_INFOS):
                    mutate.enable_all(ctx)

                self.mutate_patch(ctx)
                tsl.write_patch_order(result, info_out)
                mutate.finish_mutate(ctx)
                print(info_out.getvalue())
                out.add_patch(result)

    def mutate_patch(self, ctx):
        for mutation in mutate.select_mutations(self.weights, self.mutations):
            mutation(ctx)
