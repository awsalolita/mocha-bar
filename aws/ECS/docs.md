### ecs cloudmap
the ecs cloudmap is the route53 dns private hosted zone for connecting ecs service with domain name:
1. I create svc.local namespace
2. for services (e.g. plant -> plant.svc.local) 

### ecs profile ec2 profile
should have this `AmazonEC2ContainerServiceforEC2Role` managed policy
