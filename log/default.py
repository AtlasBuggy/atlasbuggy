import os
import logging

log_buffer_start = "[log buffer start]\n"
log_buffer_end = "[log buffer end]"


class DefaultSettings:
    instance_made = False

    def __init__(self):
        DefaultSettings.instance_made = True

    settings = dict(
        write=False, level=logging.INFO,
        log_format="[%(name)s @ %(filename)s:%(lineno)d][%(levelname)s] %(asctime)s: %(message)s",
        file_name="%H_%M_%S.log", directory=os.path.join("logs", "%Y_%b_%d", "%(name)s"),
        custom_fields_fn=None
    )

    @staticmethod
    def update(d):
        DefaultSettings.settings.update(d)

    def __getitem__(self, item):
        return DefaultSettings.settings[item]


if not DefaultSettings.instance_made:
    default_settings = DefaultSettings()
