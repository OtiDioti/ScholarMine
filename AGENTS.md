# Agent instructions

### Design

- Prefer existing libraries, straightforward files and small reversible designs. Add an abstraction only for a demonstrated requirement or actual duplication.
- Handle realistic errors and write tests with consequences, not defences against hypothetical failures.
- Replace superseded code instead of keeping it alongside for compatibility.
### Code

- Python 3.11 or later; concurrency is asyncio, with no new threads or blocking wrappers.
- Every module opens with a docstring saying what it is for; comments explain why, not what.
- Type hints on every public function; dataclasses for plain data.
- One statement per line. A module stays under about 500 lines: split a bigger one by responsibility.
- Formatting is `ruff format`'s. `uv run ruff format`, `uv run ruff check` and `uv run pyright` pass, with the configuration in `pyproject.toml`.

### Repository layout

- One uv project per repository: the package in `src/<package>/`, tests in `tests/`, `uv.lock` committed.
- `README.md` says what it is, how to install it and how to use it; `docs/` holds one file per topic. A change of behaviour updates them.

### Tests

- `unittest`: `uv run python -m unittest discover -s tests -t .` passes before every commit.

### Git

- Commit messages and pull request descriptions carry no AI attribution: no `Co-Authored-By: Claude` trailer and no "Generated with Claude Code" line.
