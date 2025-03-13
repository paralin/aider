# Aider Development Guide

## Build/Test/Lint Commands
- Install dev environment: `python -m venv ../aider_venv && source ../aider_venv/bin/activate && pip install -e . && pip install -r requirements/requirements-dev.txt`
- Run all tests: `pytest`
- Run specific test: `pytest tests/basic/test_coder.py::TestCoder::test_specific_case`
- Run pre-commit hooks: `pre-commit run --all-files`
- Update dependencies: `./scripts/pip-compile.sh`
- Build docs locally: `cd aider/website && bundle exec jekyll serve`

## Code Style Guidelines
- Python compatibility: 3.9, 3.10, 3.11, 3.12
- Line length: 100 characters max
- Formatting: Black with `--preview` flag
- Import sorting: isort with Black profile
- **NO type hints** (project explicitly doesn't use them)
- Naming: snake_case for functions/variables, PascalCase for classes
- Use relative imports for internal modules
- Custom exceptions defined in exceptions.py (e.g., UnknownEditFormat)
- Test files follow naming convention test_*.py
- Follow PEP 8 with exceptions noted in .pre-commit-config.yaml
- Use pre-commit hooks for code quality

## Scripting API

Aider can be scripted via command line or Python API:

### Command Line
```bash
# One-off message to edit file(s)
aider --message "add docstrings to functions" file.py

# Useful flags: --yes, --no-stream, --dry-run
```

### Python API

```python
from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput
from aider.commands import Commands

# Setup
model = Model("gpt-4-turbo")  # Or other supported model
fnames = ["file.py"]  # Files to add to chat

# Auto-confirm all prompts with yes=True
io = InputOutput(yes=True)

# Create coder (available types: EditBlockCoder, WholeFileCoder, UnifiedDiffCoder, etc.)
coder = Coder.create(main_model=model, fnames=fnames, io=io)

# Run instructions
coder.run("add error handling to the main function")
coder.run("/tokens")  # Run chat commands

# Key methods
# --------------------
# File management
coder.add_rel_fname("another_file.py")  # Add file to chat
coder.drop_rel_fname("file.py")  # Remove file from chat
files = coder.get_inchat_relative_files()  # Get files in chat

# Git integration
coder.auto_commit(edited_files)  # Auto-commit changes if enabled
coder.dirty_commit()  # Commit files before editing

# Advanced usage
coder_clone = coder.clone(edit_format="udiff")  # Clone with different edit format
repo_map = coder.get_repo_map()  # Get repository map for context
coder.check_for_file_mentions("Let's check utils.py")  # Scan for file mentions
coder.run_shell_commands()  # Run suggested shell commands
coder.show_usage_report()  # Show token usage and cost info

# Commands API
# --------------------
# Use commands directly through the coder.commands object
coder.commands.cmd_reset("")  # Clear files and chat history
coder.commands.cmd_add("new_file.py")  # Add a file to the chat
coder.commands.cmd_drop("file.py")  # Remove a file from chat
coder.commands.cmd_tokens("")  # Show token usage
coder.commands.cmd_commit("Commit message")  # Commit changes to git
coder.commands.cmd_diff("")  # Show code changes
coder.commands.cmd_ls("")  # List all files
coder.commands.cmd_run("pytest tests/")  # Run a shell command
```
