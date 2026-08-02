import sys
import os
from fastapi.routing import APIRoute
from fastapi import APIRouter

sys.path.insert(0, os.path.abspath("src"))
from viralai.api.app import app

print("app routes:")
for index, r in enumerate(app.routes):
    print(f"[{index}] {type(r).__name__} path={getattr(r, 'path', None)} name={getattr(r, 'name', None)}")
    if isinstance(r, APIRoute):
        print("  body_field", getattr(r, 'body_field', None))
        dep = getattr(r, 'dependant', None)
        if dep is not None:
            print("  body_params", [p.name for p in dep.body_params])
    if hasattr(r, 'router'):
        print("  included router routes:")
        for sub in getattr(r, 'router').routes:
            print(f"    {type(sub).__name__} path={getattr(sub, 'path', None)} name={getattr(sub, 'name', None)}")
