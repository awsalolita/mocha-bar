#!/usr/bin/env bash
set -euo pipefail

# Require tools
for cmd in curl tar sha256sum sudo; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing required command: $cmd" >&2; exit 1; }
done

# Map uname -m → eksctl release arch
ARCH=$(uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/')
PLATFORM="$(uname -s)_${ARCH}"

curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_${PLATFORM}.tar.gz"

# Verify checksum (fails the script if mismatch / no match)
curl -sL "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_checksums.txt" \
  | grep "${PLATFORM}" \
  | sha256sum --check

tar -xzf "eksctl_${PLATFORM}.tar.gz" -C /tmp
rm -f "eksctl_${PLATFORM}.tar.gz"

sudo install -m 0755 /tmp/eksctl /usr/local/bin
rm -f /tmp/eksctl

# Bash completion (append once)
if [[ -f "${HOME}/.bashrc" ]] && ! grep -q 'eksctl completion bash' "${HOME}/.bashrc" 2>/dev/null; then
  echo 'source <(eksctl completion bash)' >> "${HOME}/.bashrc"
fi

# Zsh completion (append once)
mkdir -p "${HOME}/.zsh/completion"
eksctl completion zsh > "${HOME}/.zsh/completion/_eksctl"

if [[ -f "${HOME}/.zshrc" ]] || [[ ! -e "${HOME}/.zshrc" ]]; then
  touch "${HOME}/.zshrc"
  if ! grep -q '~\.zsh/completion\|\$HOME/.zsh/completion' "${HOME}/.zshrc" 2>/dev/null; then
    echo 'fpath=($fpath ~/.zsh/completion)' >> "${HOME}/.zshrc"
  fi
  if ! grep -q 'compinit' "${HOME}/.zshrc" 2>/dev/null; then
    cat <<'EOF' >> "${HOME}/.zshrc"
autoload -U compinit
compinit
EOF
  fi
fi

eksctl version