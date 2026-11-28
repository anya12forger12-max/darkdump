# Darkdump

Open-source OSINT interface for deep-web search: query several engines, scrape result pages, and stream findings to a terminal or a local web UI.

> **Upstream / attribution:** Based on [josh0xA/darkdump](https://github.com/josh0xA/darkdump) by Josh Schiavone. This repository is a copy that also carries local CI, dependency, deployment, and security-hardening commits; please report issues upstream. MIT License © 2021 Josh Schiavone — see [LICENSE](LICENSE).

Darkdump takes a search query, fetches results from multiple dark-web search engines, optionally deep-scrapes each result for emails, metadata, links, documents, and images, and exports or streams the results live. Regardless of the engine, result URLs are checked against Ahmia's public abuse blacklist.

## Features

- **Six engines** via `-e` / `--engine`: `ahmia` (default, no Tor required), `notevil`, `tordex`, `tor66`, `onionland`, and `excavator`. Engines without reliable filtering require an explicit confirmation before they run.
- **Deep scraping** (`-s`) for page content and metadata, with optional image collection (`-i`, requires `-s`).
- **Deduplication** of results sharing the same title and description (`-u`).
- **Export** to JSON, CSV, or TXT, inferred from the output file extension (`-o`).
- **Breach intelligence mode** (`--breach`, `--breach-deep`, `--breach-delay`) for credential-leak queries.
- **Local web interface** with live result streaming, engine selection, a Tor proxy toggle with exit-IP display, breach mode, and the same export formats.
- **Tor-aware** routing for engines that require it.

## Install

```sh
git clone https://github.com/anya12forger12-max/darkdump.git
cd darkdump
chmod +x install.sh
./install.sh
```

The installer creates two launchers: `darkdump` (web UI) and `darkdump-cli` (CLI). It may need `sudo` on macOS. To remove the launchers, run `./uninstall.sh`.

Manual install:

```sh
pip3 install -r requirements.txt
pip3 install -r darkdump-web/requirements.txt
python3 darkdump.py --help
```

Container deployment is available through the multi-stage `Dockerfile` (`cli` and `web` targets) and `docker-compose.yml`. The Compose file binds the web port to loopback because the scan API is unauthenticated.

### Tor setup

`-p` / `--proxy` routes requests through a SOCKS5 proxy at `socks5h://localhost:9050`, Tor's standard SOCKS port. Install Tor (`sudo apt install tor` on Debian/Kali/Ubuntu, `brew install tor` on macOS), then start it with `sudo systemctl start tor.service` or `brew services start tor`. Confirm Tor is listening on port 9050 before using `-p` or a Tor-only engine; the web interface can display the current exit IP through its Tor status endpoint.

## CLI usage

```sh
# Basic Ahmia search (no Tor needed)
darkdump-cli -q "privacy tools" -a 10

# Search and deep-scrape through Tor
darkdump-cli -q "your query" -a 10 -s -p

# Scrape images, deduplicate, save JSON
darkdump-cli -q "your query" -a 15 -s -p -i -u -o results.json

# Use Not Evil, save CSV
darkdump-cli -q "your query" -a 20 -e notevil -p -o results.csv

# Breach intelligence scan
darkdump-cli --breach -q admin@example.com -e ahmia -p
```

Run `darkdump-cli -h` for the full flag list.

## Web interface

```sh
darkdump                       # launcher installed by install.sh
python3 darkdump-web/app.py    # or run from source
```

Open `http://127.0.0.1:50001` (override with the `DARKDUMP_PORT` environment variable). More details are in [DEPLOYMENT.md](DEPLOYMENT.md), [ONBOARDING.md](ONBOARDING.md), and [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Project layout

| Path | Purpose |
| :--- | :--- |
| `darkdump.py` | CLI and search/scraping implementation |
| `darkdump-web/app.py` | Local Flask web interface |
| `headers/`, `banner/` | Request headers and terminal banner helpers |
| `install.sh`, `uninstall.sh` | Launcher installation and removal |
| `Dockerfile`, `docker-compose.yml`, `vercel.json` | Deployment scaffolding |
| `tests/` | Smoke tests |

## Ethics and responsible use

Use Darkdump only for legitimate OSINT and security research where your activity is lawful. Do not access, host, or distribute illegal content, do not target people or systems without a proper basis, and treat every fetched page as untrusted input. The web scan API is unauthenticated, so keep the interface bound to loopback (the included Compose file does this by default). The original author, Josh Schiavone, disclaims responsibility for misuse.

## License

MIT License — Copyright (c) 2021 Josh Schiavone. See [LICENSE](LICENSE). Project policies: [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Quick start — 1 or 2 commands

```bash
./setup.sh          # install dependencies
./setup.sh run      # start the project (when a run target exists)
```

`setup.sh` detects this repository's build system and installs the right toolchain
dependencies. Use `./setup.sh test` to run the available checks. If a project has no
standard run target, the script prints the correct command from the sections above.
