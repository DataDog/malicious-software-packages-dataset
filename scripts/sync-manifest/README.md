# Synchronizing manifest files

The `sync_manifest.py` script may be used to synchronize manifest files with the latest Datadog Security Research OSV advisory content.

```bash
usage: sync_manifest [-h] --ecosystem ECOSYSTEM --since SINCE [--log-level LEVEL] [--input-file PATH] [--output-file PATH]

A script for updating dataset manifests with the latest OSV advisory content

options:
  -h, --help            show this help message and exit
  --ecosystem ECOSYSTEM The package ecosystem to synchronize against (options: npm, pypi)
  --since SINCE         The lookback cutoff time to synchronize against (%Y-%m-%d %H:%M:%S)
  --log-level LEVEL     Desired logging level (default: WARNING, options: DEBUG, INFO, WARNING, ERROR)
  --input-file PATH     Input manifest file to use as a starting point when synchronizing
  --output-file PATH    Output file where the synchronized manifest should be written (default: stdout)
```
