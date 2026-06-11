## Development

```bash
pip install -e ".[dev]"
pytest
```

## Build and publish

```bash
pip install hatch
hatch build          # creates dist/its_a_dt-*.whl and dist/its_a_dt-*.tar.gz
hatch publish        # upload to PyPI (configure credentials first)
```

To publish via GitHub Actions, create a PyPI trusted publisher for this repository, then cut a GitHub release. The workflow in `.github/workflows/publish.yml` builds and uploads the package automatically.
