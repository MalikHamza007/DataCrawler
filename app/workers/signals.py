from __future__ import annotations

import signal


class ShutdownFlag:
    def __init__(self) -> None:
        self.requested = False

    def request(self, *_: object) -> None:
        self.requested = True


def install_signal_handlers(flag: ShutdownFlag) -> None:
    signal.signal(signal.SIGINT, flag.request)
    signal.signal(signal.SIGTERM, flag.request)
