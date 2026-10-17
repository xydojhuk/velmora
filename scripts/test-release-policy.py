#!/usr/bin/env python3
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('verify_release_tree', Path(__file__).parent / 'verify-release-tree.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.forbidden('.env.local')
assert module.forbidden('.bootstrap/setup_token')
assert module.forbidden('backups/production.dump')
assert module.forbidden('frontend/node_modules/file')
assert module.forbidden('frontend/dist/client/index.html')
assert module.forbidden('frontend/.env.production')
assert module.forbidden('frontend/.npmrc')
assert module.forbidden('frontend/node_modules/some-package/index.js')
assert module.forbidden('backend/.venv/bin/python')
assert module.forbidden('production-secrets.zip')
assert module.forbidden('backup.tar.gz')
assert module.forbidden('frontend/public/uploads/file.jpg')
assert not module.forbidden('.env.local.example')
assert not module.forbidden('frontend/.env.production.example')
assert not module.forbidden('backend/.env.example')
assert not module.forbidden('.env.local.example')
assert not module.forbidden('backend/tests/test_security.py')
print('Release path policy tests passed')
