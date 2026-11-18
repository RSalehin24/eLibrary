# Automation Support

This folder keeps the shared helper code used by the repo's local, logging, and deployment automation.

- `automation/lib/common.sh`: shared shell helpers for env setup, Docker Compose detection, log file preparation, and terminal prompts
- `automation/lib/env_tools.py`: env file scaffold and merge utilities used by the automation scripts

Application code stays in `app/`. Runtime workflows stay in `local/`, `deploy/`, and `logs/`.
