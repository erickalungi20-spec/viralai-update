import sys
import os

# Ensure the project's src/ is on sys.path so `import viralai` works
root = os.path.dirname(__file__)
src_path = os.path.join(root, "viralai", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import pytest

if __name__ == '__main__':
    sys.exit(pytest.main(sys.argv[1:]))
