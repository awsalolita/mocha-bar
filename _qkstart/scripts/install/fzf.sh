check_exec git

git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install --all --no-zsh --no-fish --no-update-rc

cat << 'EOF' >> ~/.bashrc
export PATH="$HOME/.fzf/bin:$PATH"
eval "$(fzf --bash)"
EOF

