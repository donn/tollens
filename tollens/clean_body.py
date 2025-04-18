# This is free and unencumbered software released into the public domain.

# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.

# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# For more information, please refer to <https://unlicense.org/>
import re

username_rx = re.compile(r"@([\w\-]+)")


def clean_body(body):
    if body is None:
        body = ""
    return username_rx.sub(r"[\1](https://github.com/\1)", body)


if __name__ == "__main__":
    body = """
    Reading the description of volare, it sounds like you are quickly starting to reinvent existing tooling like Conda / Pip / FuseSoC / etc. Your `tool_metadata.yml` file sounds a lot like Conda's `environment.yml` and Pip's `requirements.txt`. These existing systems have quite a large amount of tooling already written for them.

    Have you considered making volare just a thin wrapper around these existing solutions (if it isn't already)?

    I know that @olofk and @proppy where looking at this problem too. @umarcor, @kgugala and @carlosedp have been working on similar problems in the FPGA space.
    """

    print(clean_body(body))
