from time import sleep, time
from math import ceil, floor
import subprocess


ACTIVE_PROGRESSIFYER = None


class ProgressifyMeta(type):
    def __call__(self, *args, **kwargs):
        if ACTIVE_PROGRESSIFYER:
            return ACTIVE_PROGRESSIFYER(*args, **kwargs)
        return super().__call__(*args, **kwargs)


class progressify(metaclass=ProgressifyMeta):
    def __init__(self, iterable_maybe=None, width=None, message=None, style=None):
        """
        Show a progress bar.
        This should be able to be used in the following ways:

        for element in progressify(some_iterable):
            ...


        with progressify() as p:
            ...

        At any time, you should be able to access and manipulate the state of the
        progress bar.
        One can set the length of items manually (for the for loop variant), have
        it infered from len() or __length_hint__(), with a fallback to a
        "continuous" progress bar.

        This means:
            - What we return needs to be a context manager (so it can be used in
              with statements).
            - What we return needs to be iterable.
        """
        self.set_style(style)
        try:
            self.length = len(iterable_maybe)
        except TypeError:
            try:
                self.length = iterable_maybe.__length_hint__()
            except AttributeError:
                self.length = None
        self.iterable = iter(iterable_maybe) if iterable_maybe else None
        self.yielded = 0
        self.width = width or 80
        self._last_val = None
        self.message = message or ""
        subprocess.run(["tput", "civis"])
        global ACTIVE_PROGRESSIFYER
        ACTIVE_PROGRESSIFYER = self

    def set_style(self, style=None):
        styles = {
            None: {
                "full": "█",
                "empty": "░",
                "undefined": " ░▒▓▒░",
                "left": "╡",
                "right": "╞",
                "spacer": " ",
            },
            "laola": {"undefined": "▂▃▄▅▆▇█▇▆▅▄▃▂"},
        }
        if isinstance(style, dict):
            self.BLOCK_FULL = style["full"]
            self.BLOCK_EMPTY = style["empty"]
            self.BLOCKS_UNDEFINED = style["undefined"]
            self.LEFT_EDGE = style["left"]
            self.RIGHT_EDGE = style["right"]
            self.SPACER = style["spacer"]
        elif style in styles:
            self.set_style({**styles[None], **styles[style]})

    def __iter__(self):
        return self

    def __next__(self):
        self.yielded += 1
        self.draw()
        try:
            return next(self.iterable)
        except StopIteration as e:
            self.cleanup()
            raise e

    def draw(self):
        self(self.yielded / (self.length + 1))

    def __enter__(self):
        return self

    def __exit__(self, *whatever):
        self.cleanup()

    def __call__(self, value):
        available_width = (
            self.width - len(self.LEFT_EDGE) - len(self.RIGHT_EDGE) - len(self.SPACER)
        )
        if isinstance(value, (float, int)):
            value = value if value <= 1 else 1
            nfull = int(available_width * value)
            nempty = available_width - nfull
            print(
                "{}{}{}{}{}\r".format(
                    self.LEFT_EDGE,
                    self.BLOCK_FULL * nfull,
                    self.BLOCK_EMPTY * nempty,
                    self.RIGHT_EDGE,
                    (self.SPACER + self.message if self.message else ""),
                ),
                end="",
                flush=True,
            )
            self._last_val = value
        elif isinstance(value, str):
            term_width = self.get_terminal_width()
            if len(value) + self.width > term_width:
                value = value[: term_width - self.width - 1] + "‥"
            if self.message:
                self.message = " " * len(self.message)
                self(self._last_val)
            self.message = value
            self(self._last_val)
        elif value is None:
            boxes = self.BLOCKS_UNDEFINED * ceil(
                available_width / len(self.BLOCKS_UNDEFINED)
            )
            t = floor(time() * len(self.BLOCKS_UNDEFINED)) % len(self.BLOCKS_UNDEFINED)
            print(
                "{}{}{}{}\r".format(
                    self.LEFT_EDGE,
                    "{}{}".format(boxes[t:], boxes[:t])[:available_width],
                    self.RIGHT_EDGE,
                    self.message,
                ),
                end="",
                flush=True,
            )
            self._last_val = value

    def cleanup(self):
        if self.message:
            self.message = " " * len(self.message)
            self(self._last_val)
        subprocess.run(["tput", "cnorm"])
        global ACTIVE_PROGRESSIFYER
        ACTIVE_PROGRESSIFYER = None

    @staticmethod
    def get_terminal_width():
        proc = subprocess.run(["stty", "size"], stdout=subprocess.PIPE)
        _, w = map(int, proc.stdout.decode().split())
        return w


for item in progressify("Luke... I am your father! NOOOOOOOO!".split()):
    progressify(item)
    sleep(0.25)

with progressify(style="laola") as p:
    for i in range(10, -1, -1):
        p(i / 10)
        sleep(0.2)
    for _ in range(25):
        p(None)
        sleep(0.02)
    p.set_style()
    for _ in range(25):
        p(None)
        sleep(0.02)
    p("An incredibly long message; too long to fit on our small screen")
    for i in range(25):
        p((i + 1) / 25)
        sleep(0.02)
