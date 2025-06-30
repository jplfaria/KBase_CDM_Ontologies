# Docker Permission Issues - Solutions Guide

## Problem
Docker containers often run as root, creating files that your normal user can't modify. This causes "Permission denied" errors.

## Quick Solutions

### 1. Fix Existing Permission Issues
```bash
# Option A: Use the fix script
./fix_docker_permissions.sh

# Option B: Fix all files at once
./fix_docker_permissions.sh --all

# Option C: Manual Docker fix
docker run --rm -v "$PWD:/workspace" -w /workspace --user root alpine chown -R $(id -u):$(id -g) results/
```

### 2. Use Permission-Safe Scripts
```bash
# Instead of: ./add_results_to_git.sh
# Use: ./add_results_to_git_safe.sh
```

### 3. Run Docker with Correct User
```bash
# Always export UID/GID before running Docker
export UID=$(id -u)
export GID=$(id -g)
./docker-run.sh all
```

## Permanent Solutions (For Dev Branch)

### 1. Update docker-compose.yml
Already includes:
```yaml
user: "${UID:-1000}:${GID:-1000}"
environment:
  - HOST_UID=${UID:-1000}
  - HOST_GID=${GID:-1000}
```

### 2. Use Docker Entrypoint (Future)
Add to Dockerfile:
```dockerfile
COPY --chmod=755 docker-entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
```

### 3. Always Set UID/GID
Add to your shell profile (.bashrc/.zshrc):
```bash
export UID=$(id -u)
export GID=$(id -g)
```

## Prevention Tips

1. **Before running tests**: `export UID=$(id -u) GID=$(id -g)`
2. **After Docker operations**: `./fix_docker_permissions.sh`
3. **For CI/CD**: Always use explicit user mapping

## Troubleshooting

If you see:
- `Permission denied`: Run `./fix_docker_permissions.sh`
- `Operation not permitted`: You need sudo or Docker-based fix
- Files owned by `root`: Normal for Docker, use fix scripts

## For Distribution

When sharing this pipeline:
1. Include the fix_docker_permissions.sh script
2. Document the UID/GID export requirement
3. Provide the *_safe.sh versions of scripts
4. Consider using rootless Docker/Podman as alternative