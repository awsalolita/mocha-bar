#!/bin/bash

# amazon linux required packages
sudo yum install -y gettext bash-completion

# install kubectl
source <(kubectl completion bash) >>~/.bashrc
source ~/.bashrc

# Install kubectx
sudo git clone https://github.com/ahmetb/kubectx /opt/kubectx
sudo ln -s /opt/kubectx/kubectx /usr/local/bin/kubectx
sudo ln -s /opt/kubectx/kubens /usr/local/bin/kubens

# Install eskctl
curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_Linux_amd64.tar.gz"
tar -xzf eksctl_Linux_amd64.tar.gz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin


# helm install 
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4 | sh
sudo sh -c 'helm completion bash > /etc/bash_completion.d/helm'

# fzf search
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install
eval "$(fzf --bash)"





