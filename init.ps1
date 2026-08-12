$env:AWS_ACCESS_KEY_ID = ""
$env:AWS_SECRET_ACCESS_KEY = ""
$env:AWS_SESSION_TOKEN = ""

# Setting alias
Set-Alias -Name tf -Value terraform
Set-Alias -Name k -Value kubectl

function ka { k apply -f $args }
function kg { k get -f $args }
function kd { k describe -f $args }
function kx { k delete -f $args }

function ti { terraform init $args }
function ta { terraform apply --parallelism 100 $args }
function taa { terraform apply --auto-approve --parallelism 100 $args }