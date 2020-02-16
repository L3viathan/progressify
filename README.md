# progressify

_Build progress bars from iterables, as a decorator, or as a context manager._

![a preview](https://thumbs.gfycat.com/UnderstatedPettyIndochinesetiger-size_restricted.gif)

## Installation

    pip install progressify

## Usage

In its simplest form, you just use progressify in order to loop over some
iterable:

    import progressify

    for element in progressify(range(100)):
        # do something

A progress bar will then be shown and periodically updated, based on the size
of your iterable. When the size can not be determined, a generic progress bar
is displayed that doesn't indicate how far we are.

You can also use progressify as a context manager. This is most useful when you
want to set the value of your progres bar manually. The value is always a float
between 0 and 1:

    with progressify() as p:
        p.value = 0  # to prevent a generic value-less progress bar
        do_something()
        p.value = 0.5
        do_something_else()
        p.value = 1
        cleanup()

Apart from `.value`, you can also set `.message` to a string which will be
displayed next to your progress bar.

Finally, you can use progressify as a decorator:

    @progressify
    def foo(progress_bar):
        do_something()

Whenever `foo` will be called, a progress bar will be shown, which can be
interacted with using the `progress_bar` argument.

## Advanced usage

progressify supports nested progress bars. The following code will display two progress bars below eachother:

    for x in progressify(range(10)):
        for y in progressify(range(5)):
            do_something(x, y)

When you're using progressify like this, and you want to change the message or
want to set a different attribute on the current progress bar, you can use
`progressify.last` to access the last progress bar instance.

By default, box-drawing characters are used to draw the progress bar, but the
style can be changed, either by passing a keyword argument `style` to
progressify, or by calling `.set_style` on a progress bar instance. The passed
value can either be a string (the name of a pre-defined style; currently
"classic" (ASCII-only) or "laola"), or a dictionary containing bindings for at
least some of the characters, e.g. `{"full": "X", "empty": "_"}`.

## Caveats

Due to the way progressify interacts with your terminal, printing to
stdout/stderr may be unreliable. The builtin `print` is patched while a
progress bar is visible, but if you write directly to `sys.stdout` or
`sys.stderr`, you're on your own.

## License

MIT I guess
