# Generating manifest files

The `generate_manifest.py` script in this directory may be used to regenerate the manifest file for each ecosystem based on the current contents of the repository.

```bash
usage: generate_manifest [-h] [--output-file FILE] PATH

Generate a JSON manifest file for an ecosystem's malicious package samples

positional arguments:
  PATH                The path to the top-level directory containing the samples

options:
  -h, --help          show this help message and exit
  --output-file FILE  A file where the manifest should be written (stdout otherwise)
```
