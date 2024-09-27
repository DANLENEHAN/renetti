# renetti
Machine Learning and Data Pipelining Service

# Setup
## Poetry
Poetry is a Python dependency management and packaging tool.
### Create Poetry Env
Here we're creating a poetry env with a specific python version
```bash
poetry env use /opt/homebrew/bin/python3
```
### Activate Env created by poetry
```bash
poetry shell
```
### Add package
```bash
poetry add package
```
### Add package to the dev group
```bash
poetry add --group dev black
```
### Remove package
```bash
poetry remove package
```
### Install project as editable package
```bash
poetry add -e .
```
## Pre-commit
### Install pre-commit
```bash
poetry add --group dev pre-commit
```
### Auto update all pre-commits
```bash
pre-commit autoupdate
```
### Run pre-commit on all files
```bash
pre-commit run --all-files
```