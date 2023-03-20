import os
import re
from glob import glob
from pathlib import Path

num_samples = len(glob('samples/**/*.zip'))
readme_path = Path(os.path.join(
  os.path.basename(os.path.abspath( __file__ )), '..', 'README.md'
)).resolve()

with open(readme_path, 'r') as f:
  readme = f.read()
  
# Replace the package count placeholder with the actual count
readme = re.sub(r'<span id="num-samples">.*</span>', f'<span id="num-samples">{num_samples}</span>', readme)

with open(readme_path, 'w') as f:
  f.write(readme)