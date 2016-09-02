import copy
import logging
import os
from StringIO import StringIO
import sys

from cliff import command
import inquirer

from bogt import config
from bogt import io
from bogt import tsl
from bogt_rando import mutate


class MutateCmd(command.Command):
    '''Interactively apply or revert mutations from a base patch'''

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(MutateCmd, self).get_parser(prog_name)
        parser.add_argument(
            'out',
            metavar='<file>',
            help=('Path of TSL file to append mutated patches.')
        )
        parser.add_argument(
            '--mutations',
            type=int,
            default=10,
            help=('Number of mutations to perform in each iteration. '
                  '(Default 4)')
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
        self.out = os.path.abspath(parsed_args.out)
        self.liveset = tsl.LiveSet(self.conf, path=parsed_args.out)
        self.stack_liveset = tsl.LiveSet(self.conf)
        self.session = io.Session(self.conf)
        self.mutations = parsed_args.mutations
        self.weights = mutate.normalise_weights(parsed_args.weights.split(','))

        fx_names = parsed_args.fx.split(',')
        if parsed_args.fx_ignore:
            fxi = parsed_args.fx_ignore.split(',')
            for f in fxi:
                if f in fx_names:
                    fx_names.remove(f)
        self.fx = [f for f in mutate.FX_INFOS if f.name in fx_names]

        # store in the tsl whatever is initially in the temporary preset
        patch = self.session.receive_preset(None)
        self.stack_liveset.add_patch(patch)
        self.save()
        action = 'Save'

        while True:
            action = self.prompt_mutate(action)
            if action == 'Quit':
                sys.exit(0)
            if action == 'Mutate':
                self.mutate()
            if action == 'Revert':
                self.revert()
            if action == 'Save':
                self.save()

    def prompt_mutate(self, last_action):
        actions = [
            'Mutate',
        ]
        if last_action != 'Save':
            actions.insert(0, 'Save')
        if len(self.stack_liveset.patches) > 1:
            actions.append('Revert')
        actions.append('Quit')
        q = [
            inquirer.List(
                'action',
                message="Next action",
                default=last_action,
                choices=actions,
            ),
        ]
        answer = inquirer.prompt(q)
        return answer['action']

    def save(self):
        patch_key = self.stack_liveset.patches.keys()[-1]
        patch = self.stack_liveset.patches[patch_key]
        result = copy.deepcopy(patch)
        self.liveset.add_patch(result)
        self.liveset.store()

    def revert(self):
        patch_key = self.stack_liveset.patches.keys()[-1]
        print('removing %s' % patch_key)
        self.stack_liveset.remove_patch(patch_key)
        patch_key = self.stack_liveset.patches.keys()[-1]
        print('sending %s' % patch_key)
        patch = self.stack_liveset.patches[patch_key]
        print('Reverting to "%s"\n' % patch['name'])
        self.session.patch_to_midi(patch, None)

    def mutate(self):
        patch_key = self.stack_liveset.patches.keys()[-1]
        patch = self.stack_liveset.patches[patch_key]
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
        self.session.patch_to_midi(result, None)
        self.stack_liveset.add_patch(result)

    def mutate_patch(self, ctx):
        for mutation in mutate.select_mutations(self.weights, self.mutations):
            mutation(ctx)
