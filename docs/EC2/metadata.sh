export TOKEN=$(curl -X PUT -H "X-aws-ec2-metadata-token-ttl-seconds: 300" http://169.254.169.254/latest/api/token)

curl http://169.254.169.254/latest/meta-data -H "X-aws-ec2-metadata-token: $TOKEN"
curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/ -H "X-aws-ec2-metadata-token: $TOKEN"

macid=$(curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/ -H "X-aws-ec2-metadata-token: $TOKEN")
vpcid=$(curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/${macid}/vpc-id -H "X-aws-ec2-metadata-token: $TOKEN")

sudo yum update && sudo yum install nginx -y
sudo systemctl start nginx

echo "" | sudo tee /usr/share/nginx/html/index.html
echo $vpcid | sudo tee /usr/share/nginx/html/index.html

sudo nginx -s reload