## Setup AWS Client VPN with mutual Authentication
```bash
# Clone Easy-RSA

git clone https://github.com/OpenVPN/easy-rsa.git
cd easy-rsa/easyrsa3

# Initialize the PKI (Public Key Infrastructure)
./easyrsa init-pki

# Build the CA (Certificate Authority)
# You'll be prompted for a passphrase
./easyrsa build-ca nopass

# Generate the server certificate
./easyrsa --san=DNS:server build-server-full server nopass

# Generate a client certificate
./easyrsa build-client-full client1.domain.tld nopass

```

Import Certs to ACM
```bash
# Import the server certificate
aws acm import-certificate \
  --certificate fileb://pki/issued/server.crt \
  --private-key fileb://pki/private/server.key \
  --certificate-chain fileb://pki/ca.crt \
  --region us-east-1

# Import the client certificate
aws acm import-certificate \
  --certificate fileb://pki/issued/client1.domain.tld.crt \
  --private-key fileb://pki/private/client1.domain.tld.key \
  --certificate-chain fileb://pki/ca.crt \
  --region us-east-1

```

Create Client VPN Endpoint
```bash
# Create the Client VPN endpoint
aws ec2 create-client-vpn-endpoint \
  --client-cidr-block "10.100.0.0/16" \
  --server-certificate-arn "arn:aws:acm:us-east-1:123456789012:certificate/server-cert-id" \
  --authentication-options 'Type=certificate-authentication,MutualAuthentication={ClientRootCertificateChainArn=arn:aws:acm:us-east-1:123456789012:certificate/client-cert-id}' \
  --connection-log-options '{
    "Enabled": true,
    "CloudwatchLogGroup": "/aws/clientvpn",
    "CloudwatchLogStream": "connections"
  }' \
  --dns-servers "10.0.0.2" \
  --transport-protocol udp \
  --vpn-port 443 \
  --split-tunnel \
  --description "Production VPN - Mutual Auth"

```
Associate with Subnets

```bash
# Associate with a private subnet in AZ-a
aws ec2 associate-client-vpn-target-network \
  --client-vpn-endpoint-id cvpn-endpoint-abc123 \
  --subnet-id subnet-111111

# Associate with a private subnet in AZ-b for redundancy
aws ec2 associate-client-vpn-target-network \
  --client-vpn-endpoint-id cvpn-endpoint-abc123 \
  --subnet-id subnet-222222
```

Configure Authorization Rule

```bash
# Allow all authenticated users to access the entire VPC
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id cvpn-endpoint-abc123 \
  --target-network-cidr "10.0.0.0/16" \
  --authorize-all-groups \
  --description "Allow VPC access for all VPN users"

# Or restrict to specific subnets
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id cvpn-endpoint-abc123 \
  --target-network-cidr "10.0.1.0/24" \
  --authorize-all-groups \
  --description "Allow access to database subnet only"
```

Add Routes

```bash
# Add a route to a peered VPC through the first associated subnet
aws ec2 create-client-vpn-route \
  --client-vpn-endpoint-id cvpn-endpoint-abc123 \
  --destination-cidr-block "172.16.0.0/16" \
  --target-vpc-subnet-id subnet-111111

# Add the same route through the second associated subnet
aws ec2 create-client-vpn-route \
  --client-vpn-endpoint-id cvpn-endpoint-abc123 \
  --destination-cidr-block "172.16.0.0/16" \
  --target-vpc-subnet-id subnet-222222
```

Download Client Configuration
```bash
# Download the OpenVPN configuration
aws ec2 export-client-vpn-client-configuration \
  --client-vpn-endpoint-id cvpn-endpoint-abc123 \
  --output text > client-config.ovpn
```

We need to append the key
```bash
# Add client certificate and key to the config file
echo '<cert>' >> client-config.ovpn
cat pki/issued/client1.domain.tld.crt >> client-config.ovpn
echo '</cert>' >> client-config.ovpn

echo '<key>' >> client-config.ovpn
cat pki/private/client1.domain.tld.key >> client-config.ovpn
echo '</key>' >> client-config.ovpn

```

## The console way
things to do:
1. we should create the certs with cli and push them to the ACM
2. then we should add the dns as 10.0.0.2 (vpc range 10.0.0.0/16)
3. attach a range for the vpn (eg. 10.165.0.0/22)
4. select mutual authentication
5. select full tunnel mode
6. after creating we should associate the vpn client network to the vpc private subnet which has route to NAT
7. the security group should allow inbound the vpc range for all traffic
8. for authorization rule we add the route 0.0.0.0/0
9. the vpn client route table we add the route 0.0.0.0/0
10. then install openvpn and import the config
