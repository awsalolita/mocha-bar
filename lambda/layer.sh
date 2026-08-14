docker run -it -v ./python:/tmp python:3.14-slim bash

cd /tmp && pip install scapy -t . 

# exit the container
zip -r scapy.zip ./scapy

# dont need in cloudshell
aws configure --profile <cloud_user>

aws lambda publish-layer-version --profile <cloud_user> --layer-name scapy --description "scapy" --license-info "MIT" --zip-file fileb://scapy.zip --compatible-runtimes python3.14
