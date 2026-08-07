check_exec curl wget bash-completion

v=$(curl -L -s https://dl.k8s.io/release/stable.txt)
a=$(get_arch)

wget https://dl.k8s.io/release/$v/bin/linux/$a/kubectl -O /tmp/kubectl

sudo install -o root -g root -m 0755 /tmp/kubectl /usr/local/bin/kubectl

cat << 'EOF' >> ~/.bashrc

[ -f /usr/share/bash-completion/bash_completion ] && . /usr/share/bash-completion/bash_completion
source <(kubectl completion bash)

# Alias + Alias completion
alias k=kubectl
complete -o default -F __start_kubectl k
EOF
