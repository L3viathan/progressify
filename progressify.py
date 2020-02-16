import sys
import inspect
import subprocess
import builtins
from functools import wraps, reduce
from collections import deque
from operator import xor
from math import ceil, floor
from threading import Thread, Lock
from time import sleep, time

C_UP = "\x1b[1A"
C_KILL = "\x1b[0K"

thread_lock = Lock()
prints = deque()
orig_print = builtins.print

def out(*args, **kwargs):
    orig_print(*args, **kwargs, sep="", end="", flush=True, file=sys.stderr)

def safe_print(*args, **kwargs):
    prints.append((args, kwargs))


def work(instances):
    with thread_lock:
        last_instances = 0
        last_hash = None

        while instances:
            while True:
                current_hash = reduce(xor, [i.hash() for i in instances], 0)
                if current_hash != last_hash:
                    last_hash = current_hash
                    break
                sleep(0.1)
            for _ in range(last_instances):
                out(C_UP, C_KILL, "\r")
            while prints:
                args, kwargs = prints.popleft()
                orig_print(*args, **kwargs)
            num_instances = None
            for num_instances, instance in enumerate(instances):
                instance.draw()
            if num_instances is None:
                break
            num_instances += 1
            last_instances = num_instances
            sleep(0.1)
        for _ in range(last_instances):
            out(C_UP, C_KILL, "\r")
        subprocess.run(["tput", "cnorm"])


class ProgressBar:
    instances = []
    thread = None
    last = None

    def __init__(self, value=None, width=None, message=None, style=None):
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
        self.width = width or 80
        self.message = message
        self.value = value

    @property
    def message(self):
        return self._message

    def hash(self):
        if self.value is None:
            return hash(time())
        return hash(self._message) ^ hash(self.value)

    @message.setter
    def message(self, msg):
        if msg is not None:
            self._message = str(msg)
        else:
            self._message = None

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
            "classic": {
                "full": "#",
                "empty": " ",
                "undefined": "-/-\\                        ",
                "left": "[",
                "right": "]",
                "spacer": " ",
            },
            "laola": {"undefined": "▂▃▄▅▆▇█▇▆▅▄▃▂"},
        }
        if isinstance(style, dict):
            self.BLOCK_FULL = style.get("full", styles[None]["full"])
            self.BLOCK_EMPTY = style.get("empty", styles[None]["empty"])
            self.BLOCKS_UNDEFINED = style.get("undefined", styles[None]["undefined"])
            self.LEFT_EDGE = style.get("left", styles[None]["left"])
            self.RIGHT_EDGE = style.get("right", styles[None]["right"])
            self.SPACER = style.get("spacer", styles[None]["spacer"])
        elif style in styles:
            self.set_style({**styles[None], **styles[style]})

    def draw(self):
        message = self.message
        value = self.value
        available_width = (
            self.width - len(self.LEFT_EDGE) - len(self.RIGHT_EDGE) - len(self.SPACER)
        )
        term_width = self.get_terminal_width()
        if message and len(message) + self.width > term_width:
            message = message[: term_width - self.width - 1] + "‥"
        if isinstance(value, (float, int)):
            value = value if value <= 1 else 1
            nfull = int(available_width * value)
            nempty = available_width - nfull
            orig_print(
                "{}{}{}{}{}".format(
                    self.LEFT_EDGE,
                    self.BLOCK_FULL * nfull,
                    self.BLOCK_EMPTY * nempty,
                    self.RIGHT_EDGE,
                    (self.SPACER + message if message else ""),
                ),
                file=sys.stderr,
            )
        elif value is None:
            boxes = self.BLOCKS_UNDEFINED * ceil(
                available_width / len(self.BLOCKS_UNDEFINED)
            )
            t = floor(time() * len(self.BLOCKS_UNDEFINED)) % len(self.BLOCKS_UNDEFINED)
            orig_print(
                "{}{}{}{}".format(
                    self.LEFT_EDGE,
                    "{}{}".format(boxes[t:], boxes[:t])[:available_width],
                    self.RIGHT_EDGE,
                    message or "",
                ),
                file=sys.stderr,
            )

    def __enter__(self):
        ProgressBar.instances.append(self)
        ProgressBar.last = self
        # if we are the first, start the thread
        if len(ProgressBar.instances) == 1:
            res = thread_lock.acquire(blocking=False)
            if res:
                self.start_thread()
                subprocess.run(["tput", "civis"])
                thread_lock.release()
            builtins.print = safe_print
        return self

    def __exit__(self, *args):
        ProgressBar.instances.pop()
        if ProgressBar.instances:
            ProgressBar.last = ProgressBar.instances[-1]
        else:
            ProgressBar.last = None
            builtins.print = orig_print

    @classmethod
    def start_thread(cls):
        cls.thread = Thread(target=work, args=(cls.instances,))
        cls.thread.start()

    @classmethod
    def stop_thread(cls):
        cls.thread.stop()

    @staticmethod
    def get_terminal_width():
        proc = subprocess.run(["stty", "size"], stdout=subprocess.PIPE)
        _, w = map(int, proc.stdout.decode().split())
        return w


def progressify(iterable_or_function=None, **kwargs):
    if callable(iterable_or_function):
        argspec = inspect.getfullargspec(iterable_or_function)
        supply_bar = "progress_bar" in argspec.kwonlyargs or argspec.varkw
        @wraps(iterable_or_function)
        def wrapper(*args, **kwargs):
            with ProgressBar() as p:
                if supply_bar:
                    return iterable_or_function(*args, progress_bar=p, **kwargs)
                return iterable_or_function(*args, **kwargs)
        return wrapper
    try:
        it = iter(iterable_or_function)
        try:
            length = len(iterable_or_function)
        except TypeError:
            try:
                length = iterable_or_function.__length_hint__()
            except AttributeError:
                length = None

        def generator():
            with ProgressBar(0, **kwargs) as bar:
                for i, element in enumerate(it):
                    bar.value = (i + 1) / length
                    yield element

        return generator()
    except TypeError:
        return ProgressBar(**kwargs)


if __name__ == '__main__':
    with progressify(style="laola") as outer:
        outer.message = "Hello"
        for item in progressify("Luke... I am your father! NOOOOOOOO!".split()):
            ProgressBar.last.message = item
            sleep(0.25)

    with progressify(style="laola") as p:
        for i in range(10, -1, -1):
            p.value = i / 10
            sleep(0.02)
        for _ in range(25):
            p.value = None
            sleep(0.02)
        p.set_style()
        for i in range(25):
            sleep(0.02)
        p.message = "An incredibly long message; too long to fit on our small screen"
        for i in range(25):
            p.value = (i + 1) / 25
            sleep(0.02)

    for i, im in zip(range(4), progressify(["Homer", "Marge", "Bart", "Lisa"], style="classic")):
        ProgressBar.instances[0].message = im
        ProgressBar.instances[0].value = (i + 1) / 4
        for j, jm in zip(
            range(7),
            progressify(["likes", "loves", "hates", "dislikes", "has", "makes", "wants"], style="classic"),
        ):
            ProgressBar.instances[1].message = jm
            ProgressBar.instances[1].value = (j + 1) / 7
            for k, km in zip(range(3), progressify(["cheese", "wine", "you"], style="classic")):
                ProgressBar.instances[2].message = km
                ProgressBar.instances[2].value = (k + 1) / 3
                sleep(0.1)

    @progressify
    def test(*, progress_bar):
        for _ in range(20):
            sleep(0.1)
        for i in range(20):
            progress_bar.value = i/20
            progress_bar.message = i
            if i % 5 == 0:
                print("hello from", i)
            sleep(0.1)

    test()
