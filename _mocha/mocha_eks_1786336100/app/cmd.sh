eksctl create iamserviceaccount \
  --region us-east-1 \
  --cluster unicorn-cluster \
  --namespace app \
  --name grow \
  --attach-policy-arn arn:aws:iam::353615901360:policy/game-dynamo-put \
  --override-existing-serviceaccounts \
  --approve
