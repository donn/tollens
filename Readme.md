# Tollens - Donn's Repository Mirroring Script(s)

These are scripts I'm using to mirror repositories with issues and pull requests
in tow.

Currently, only the part where mirroring issues and pull requests (by
re-creating them) works:

```sh
python3 -m venv venv
./venv/bin/python3 -m pip3 install -r requirements.txt
./venv/bin/python3 -m tollens copy-issues -t <a bot account's github token> -T <target-owner/target-repo> <source-owner/source-repo>
```

> [!WARNING] 
> This set of scripts are very hacky and known to the State of California to cause
> cancer, birth defects, or reproductive harm. You WILL have to babysit them and
> you ARE using them entirely at your own risk.

# License

Everything except tollens/github.py: The Unlicense. See 'UNLICENSE'.

tollens/github.py: Apache 2.0 (adapted from a project using the same license):
https://www.apache.org/licenses/LICENSE-2.0
