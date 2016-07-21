import copy
import logging
import os

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
        self.start_mutate()

    def start_mutate(self):
        count = 0
        out = tsl.empty_tsl(self.conf)

        while True:
            for name, patch in self.liveset.patches.items():
                count += 1
                if count > self.count:
                    return
                print('Mutating %s ' % name)
                result = self.mutate_patch(copy.deepcopy(patch))
                out.add_patch(result)
        return out

    def mutate_patch(self, patch):
        for mutation in mutate.select_mutations(self.weights, self.mutations):
            mutation(patch)
        return patch
