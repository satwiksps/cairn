# Installation

Steadlith supports CPython 3.10 through 3.14 on Windows, macOS, and Linux. The core package contains the CLI, chunking algorithms, local SQLite index, embedding cache, offline hash provider, migration workflow, and benchmark fixtures.

## Install from PyPI

Create a virtual environment for application use:

```bash
python -m venv .venv
```

Activate it on Linux or macOS:

```bash
source .venv/bin/activate
```

Activate it in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install Steadlith:

```bash
python -m pip install --upgrade pip
python -m pip install steadlith
```

Confirm both entry points:

```bash
steadlith --version
python -m steadlith --version
```

For a CLI-only machine, [pipx](https://pipx.pypa.io/) can keep Steadlith isolated:

```bash
pipx install steadlith
```

## Optional embedding providers

The default `hash` provider is included in the core package and makes no network requests. Install only the provider integration you need.

OpenAI:

```bash
python -m pip install "steadlith[openai]"
```

Sentence Transformers:

```bash
python -m pip install "steadlith[sentence-transformers]"
```

Both optional providers require `--allow-network` on commands that may contact an API or download a model. The confirmation applies to one command invocation. It is not stored in the project configuration.

## Install from a source checkout

Use an editable install when contributing:

```bash
git clone https://github.com/satwiksps/steadlith.git
cd steadlith
python -m venv .venv
python -m pip install -e ".[dev]"
```

The repository `main` branch can be newer than the latest release. Use a tagged release when reproducibility matters.

## Upgrade

Inspect the [changelog](../changelog.md) and [compatibility policy](../compatibility.md), then upgrade in the same environment:

```bash
python -m pip install --upgrade steadlith
steadlith --version
steadlith plan
steadlith verify
```

`plan` is read-only and reveals any identity or source-scope change before the index is modified.

Users of Cairn 0.2 should follow [Adopt a 0.2 project](../guides/migrations.md#adopt-a-02-project) instead of renaming state files by hand.

## Troubleshooting installation

`steadlith` is not recognized
: Run `python -m steadlith --version`. If that works, the environment's script directory is not on `PATH`, or the virtual environment is not active.

`No module named steadlith`
: Check `python -m pip --version` and `python --version`. They must refer to the same environment used for installation.

Optional provider import error
: Install the matching extra. Provider SDKs are deliberately absent from the core installation.

SQLite error during startup
: Confirm the state directory is writable and that the cache and index are different files. Paths must remain below the configuration directory.
