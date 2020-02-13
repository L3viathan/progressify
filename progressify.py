from time import sleep, time
from math import ceil, floor
from itertools import zip_longest
import subprocess


ACTIVE_PROGRESSIFYER = None
C_UP = "\x1b[1A"
C_KILL = "\x1b[0K"


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
        self.last_value = None
        self.max_bars = 1
        self.width = width or 80
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

    def __del__(self):
        self.cleanup()

    def __call__(self, *values):
        available_width = (
            self.width - len(self.LEFT_EDGE) - len(self.RIGHT_EDGE) - len(self.SPACER)
        )
        self.max_bars = max(self.max_bars, len(values))
        for value, filler in zip_longest(values, " " * self.max_bars, fillvalue=...):
            if isinstance(value, tuple):
                value, message = value
            elif isinstance(value, str):
                message = value
                value = self.last_value
            else:
                message = ""
            term_width = self.get_terminal_width()
            if len(message) + self.width > term_width:
                message = message[: term_width - self.width - 1] + "‥"
            if isinstance(value, (float, int)):
                value = value if value <= 1 else 1
                nfull = int(available_width * value)
                nempty = available_width - nfull
                print(
                    "{}{}{}{}{}{}".format(
                        C_KILL,
                        self.LEFT_EDGE,
                        self.BLOCK_FULL * nfull,
                        self.BLOCK_EMPTY * nempty,
                        self.RIGHT_EDGE,
                        (self.SPACER + message if message else ""),
                    )
                )
            elif value is None:
                boxes = self.BLOCKS_UNDEFINED * ceil(
                    available_width / len(self.BLOCKS_UNDEFINED)
                )
                t = floor(time() * len(self.BLOCKS_UNDEFINED)) % len(
                    self.BLOCKS_UNDEFINED
                )
                print(
                    "{}{}{}{}".format(
                        self.LEFT_EDGE,
                        "{}{}".format(boxes[t:], boxes[:t])[:available_width],
                        self.RIGHT_EDGE,
                        message,
                    )
                )
            elif value is ...:
                print(C_KILL)
            self.last_value = value
        print(C_UP * self.max_bars, end="", flush=True)

    def cleanup(self):
        print((C_KILL + "\n") * self.max_bars, C_UP * self.max_bars, flush=True, end="")
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
    for _ in range(25):
        p(None)
        sleep(0.02)
    p.set_style()
    for i in range(25):
        p(None, i / 25)
        sleep(0.02)
    p("An incredibly long message; too long to fit on our small screen")
    for i in range(25):
        p((i + 1) / 25)
        sleep(0.02)
    for i, im in zip(range(4), ["Homer", "Marge", "Bart", "Lisa"]):
        for j, jm in zip(
            range(7), ["likes", "loves", "hates", "dislikes", "has", "makes", "wants"]
        ):
            for k, km in zip(range(3), ["cheese", "wine", "you"]):
                p(((i + 1) / 4, im), ((j + 1) / 7, jm), ((k + 1) / 3, km))
                sleep(0.1)

for i, im in progressify(["foo", "bar", "bat"]):
    for j, jm in progressify(["bla", "Baaaa"]):
        ...
