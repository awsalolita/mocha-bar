-- Find the 25 most recently added log events. 
fields @timestamp, @message | sort @timestamp desc | limit 25

-- Amazon VCP flow logs
-- Find the top 15 packet transfers across hosts:
stats sum(packets) as packetsTransferred by srcAddr, dstAddr
    | sort packetsTransferred  desc
    | limit 15

-- Find the IP addresses that use UDP as a data transfer protocol.
filter protocol=17 | stats count(*) by srcAddr

-- Find a single record for each connection, to help troubleshoot network connectivity issues.
fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, bytes 
| filter logStream = 'vpc-flow-logs' and interfaceId = 'eni-0123456789abcdef0' 
| sort @timestamp desc 
| dedup srcAddr, dstAddr, srcPort, dstPort, protocol 
| limit 20

-- Queries for Route 53 logs
-- Find the distribution of records per hour by query type.
stats count(*) by queryType, bin(1h)

-- Find the 10 DNS resolvers with the highest number of requests.
stats count(*) as numRequests by resolverIp
    | sort numRequests desc
    | limit 10

-- Find the number of records by domain and subdomain where the server failed to complete the DNS request.
filter responseCode="SERVFAIL" | stats count(*) by queryName

-- Queries for CloudTrail logs
-- Find the number of log entries for each service, event type, and AWS Region.
stats count(*) by eventSource, eventName, awsRegion

-- Find the Amazon EC2 hosts that were started or stopped in a given AWS Region.
filter (eventName="StartInstances" or eventName="StopInstances") and awsRegion="us-east-2"

-- Find the AWS Regions, user names, and ARNs of newly created IAM users.
filter eventName="CreateUser"
    | fields awsRegion, requestParameters.userName, responseElements.user.arn

-- Find log entries where TLS 1.0 or 1.1 was used
filter tlsDetails.tlsVersion in [ "TLSv1", "TLSv1.1" ]
| stats count(*) as numOutdatedTlsCalls by userIdentity.accountId, recipientAccountId, eventSource, eventName, awsRegion, tlsDetails.tlsVersion, tlsDetails.cipherSuite, userAgent
| sort eventSource, eventName, awsRegion, tlsDetails.tlsVersion

-- Queries for Amazon API Gateway
-- Find the last 10 4XX errors
fields @timestamp, status, ip, path, httpMethod
| filter status>=400 and status<=499
| sort @timestamp desc
| limit 10

-- Identify the 10 longest-running Amazon API Gateway requests in your Amazon API Gateway access log group
fields @timestamp, status, ip, path, httpMethod, responseLatency
| sort responseLatency desc
| limit 10

-- Queries for NAT gateway
-- Find the instances that are sending the most traffic through your NAT gateway.
filter (dstAddr like 'x.x.x.x' and srcAddr like 'y.y.') 
| stats sum(bytes) as bytesTransferred by srcAddr, dstAddr
| sort bytesTransferred desc
| limit 10

-- Determine the internet destinations that the instances in your VPC communicate with most often for uploads and downloads.
-- For uploads
filter (srcAddr like 'x.x.x.x' and dstAddr not like 'y.y.') 
| stats sum(bytes) as bytesTransferred by srcAddr, dstAddr
| sort bytesTransferred desc
| limit 10

-- For downloads
filter (dstAddr like 'x.x.x.x' and srcAddr not like 'y.y.') 
| stats sum(bytes) as bytesTransferred by srcAddr, dstAddr
| sort bytesTransferred desc
| limit 10
