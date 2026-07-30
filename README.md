README.md

# IDX Walkforward 5001

## Project Overview

Institutional-grade research...

Institutional-grade research and production framework for systematic trading in the Indonesian Stock Exchange (IDX).

The repository combines production trading infrastructure, walkforward validation, research workflows, Telegram integration, reporting, and supporting tools used to develop and validate quantitative trading strategies.

> **Status:** Active development

## Key Features

- Walkforward backtesting framework
- Production screening engine
- Research framework
- Telegram notification system
- Statistical validation pipeline
- Chart viewer
- Pine Script utilities
- Strategy research documentation

## Architecture Overview

```text
                 +---------------------+
                 |   Scheduler / Cron  |
                 +----------+----------+
                            |
                     Screening Engine
                            |
        +-------------------+-------------------+
        |                                       |
 Telegram Notifications                  Reports / Logs
        |
        |
 Walkforward Database
        |
        |
 Research Framework
        |
 Strategy Development
```
 
## Repository Structure

```text
.
├── Audit/                Audit reports
├── docs/                 Documentation
├── PLAN/                 Development plans
├── chart-viewer/         Chart viewer
├── pine/                 Pine Script utilities
├── registry/             Registry schemas
├── research_reports/     Research reports
├── out/                  Generated reports
├── requirements.txt      Python dependencies
└── README.md
```

## Quick Start

```bash
git clone git@github.com:Tjie-hub/idx-walkforward-5001.git
cd 5001

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

pytest
```
## Prerequisites

### Runtime

- Python 3.14+
- Git

### Recommended (Windows)

- WSL2
- Ubuntu 26.04 LTS
- VS Code Remote - WSL

### Test Dependencies

- Node.js LTS (required only for `tests/test_value_format.py` and the full test suite)

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd 5001
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. (Optional) Install Node.js for the full test suite

```bash
nvm install --lts
```
## Running the Project

Start the production application:

```bash
python app.py
```

By default the application:

- Starts the Flask web server
- Starts the production scheduler
- Starts the Telegram polling service
- Initializes required database tables

The web interface is available at:

```
http://localhost:5001
```

Health endpoint:

```
http://localhost:5001/health
```

Prometheus metrics:

```
http://localhost:5001/metrics
```
## Running Tests

Run the complete regression suite:

```bash
pytest
```

Expected baseline:

```text
1193 passed
3 skipped
```

For verbose output:

```bash
pytest -v
```

## Development Workflow

## Documentation

Additional documentation is available in:

- `docs/`
- `PLAN/`
- `Audit/`

Other useful references:

- `PLAN.md`
- `TODO.md`
- `rule.md`

## Troubleshooting

### `FileNotFoundError: node`

Install Node.js LTS:

```bash
nvm install --lts
```

### VS Code opens Windows instead of WSL

Ensure the status bar displays:

```text
WSL: Ubuntu
```

### Wrong Python interpreter

Verify that Python is running from the virtual environment:

```bash
which python
```

## Current Status

Environment verified on:

- Ubuntu 26.04 LTS
- WSL2
- Python 3.14
- Node.js LTS
- VS Code Remote WSL

Current regression baseline:

```text
1193 passed
3 skipped
```
## Roadmap

- Improve production engine
- Expand research framework
- Enhance statistical validation
- Improve documentation
## License

Internal project.