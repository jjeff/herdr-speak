# Contributing

Thanks for helping. Every pull request runs the same checks as CI; when they pass and a maintainer has reviewed the change, it can merge.

## Run the checks

herdr-speak has no dependencies beyond Python 3.9+. Install [ruff](https://docs.astral.sh/ruff/) for linting, then run:

```sh
ruff check .
ruff format --check .
python3 -m unittest
```

`ruff format .` fixes formatting for you.

## What a pull request needs

- Passing CI. The `ci` check sums up lint and the tests on every platform.
- A unit test for new logic. The decision of what a poll means lives in `classify()` in `speaker.py`; extend its tests rather than relying on a live run.
- Docs updated when behavior, config, or install steps change: `README.md` for users, `AGENTS.md` for how the project works.
- Python standard library only. The Speaker runs from a plain plugin checkout, with nothing to install.

## Adding an agent

Follow "Adding a host" in [AGENTS.md](AGENTS.md). Run the live test recipe there and paste the Speaker log lines into the pull request; CI can't run agents, so that log is the evidence the host works.

## Reporting bugs

Use the bug report template, and include the Speaker log: `herdr plugin action invoke herdr-speak.log`.
