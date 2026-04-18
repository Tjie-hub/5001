# Project Guidelines for Claude Code

## Security

- Never hardcode credentials, API keys, or tokens in source code
- Always use environment variables loaded via python-dotenv or os.environ
- Ensure .env is in .gitignore and provide a .env.example template
- Flag any hardcoded secrets found during code review

## Python Conventions

- Use python-dotenv for configuration management
- Keep a .env.example file in sync with required env vars
- Prefer `os.getenv('VAR', default)` with sensible defaults over bare `os.environ['VAR']`
