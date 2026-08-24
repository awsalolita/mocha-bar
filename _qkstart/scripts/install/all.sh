# install every package in one shot
# usage: q i all [-y]

# propagate -y so each sub-install runs unattended when requested
y=""
for a in "$@"; do
  [ "$a" = "-y" ] && y="-y"
done

for pkg in basic zsh kubectl fzf eksctl k9s helm docker aws_autocomplete kubectx terraform alias; do
  echo "[all] installing $pkg"
  q i "$pkg" $y
done
