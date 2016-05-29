import logging

from cliff import command
import inotify_simple
import inquirer

from bogt import config
from bogt import tsl


class SendData(command.Command):
    '''Send data from a TSL file to the device'''

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(SendData, self).get_parser(prog_name)
        parser.add_argument(
            '--tls',
            metavar='<file>',
            help=('Path to TLS file to select patch from.')
        )
        parser.add_argument(
            '--watch',
            action='store_true',
            help=('Watch for data changes and resend patch')
        )

        return parser

    def watch(self, file_path, get_patch, preset):
        inotify = inotify_simple.INotify()
        f = inotify_simple.flags
        watch_flags = f.ACCESS | f.MODIFY
        inotify.add_watch(file_path, watch_flags)
        while True:
            for event in inotify.read():
                print(event)
                for flag in f.from_mask(event.mask):
                    print('    ' + str(flag))

    def take_action(self, parsed_args):
        conf = config.load_config()
        liveset = tsl.load_tsl_from_file(parsed_args.tls, conf)
        last_send = conf.get('last_send', {})
        answer = self.prompt_preset(last_send, liveset.patches)
        conf['last_send'] = answer
        config.save_config(conf)
        liveset.to_midi(answer['patch'], answer['preset'])
        # def get_patch():
        #     return db.fetch_patch(patch_id)

        # tsl.patch_to_midi(conf, get_patch(), preset)
        # if parsed_args.watch:
        #     self.watch(db.db_path, get_patch, preset)

    def prompt_preset(self, last_send, patches):
        def validate_bank(answers, value):
            try:
                i = int(value)
                return i > 0 and i < 51
            except ValueError:
                return False

        def build_presets(answers):
            bank = 'U%02d' % int(answers['bank'])
            return ['%s-%s' % (bank, i) for i in range(1, 5)]

        q = [
            inquirer.List(
                'patch',
                message="Patch to send",
                default=last_send.get('patch'),
                choices=patches,
            ),
            inquirer.Text(
                'bank',
                message='User bank to write patch to (1 to 50)',
                default=last_send.get('bank'),
                validate=validate_bank
            ),
            inquirer.List(
                'preset',
                message='Preset to write patch to',
                default=last_send.get('preset'),
                choices=build_presets
            ),
        ]
        answer = inquirer.prompt(q)
        return answer
