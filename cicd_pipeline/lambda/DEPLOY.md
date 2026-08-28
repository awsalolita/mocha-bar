## Deploy lambda function with CodeDeploy

1. create the codecommit repository with the below files:
    1. lambda_function.py
    2. buildspec.yml

```bash
# Publish initial version if not yet published
aws lambda publish-version --function-name MyLambdaFunction

# Create an alias named 'live' pointing to version 1
aws lambda create-alias \
  --function-name MyLambdaFunction \
  --name live \
  --function-version 1

```

* create the `buildspec.yml`

```yaml
version: 0.2

phases:
  build:
    commands:
      - echo "Packaging application..."
      - zip -r function.zip . -x "*.git*"
      
      - echo "Updating code and publishing new version..."
      - aws lambda update-function-code --function-name test --zip-file fileb://function.zip
      - NEW_VERSION=$(aws lambda publish-version --function-name test --query 'Version' --output text)
      
      - echo "Fetching current alias version..."
      - CURRENT_VERSION=$(aws lambda get-alias --function-name test --name live --query 'FunctionVersion' --output text)
      
      - echo "Generating dynamic AppSpec file..."
      - |
        cat <<EOF > appspec.yaml
        version: 0.0
        resources:
          - test:
              type: AWS::Lambda::Function
              properties:
                Name: "test"
                Alias: "live"
                CurrentVersion: "$CURRENT_VERSION"
                TargetVersion: "$NEW_VERSION"
        EOF

artifacts:
  files:
    - appspec.yaml
```


* IAM persmission for CodeBuild:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:PublishVersion",
        "lambda:GetAlias",
        "lambda:GetFunction"
      ],
      "Resource": "arn:aws:lambda:REGION:ACCOUNT_ID:function:MyLambdaFunction*"
    }
  ]
}
```

* we should grant the CodePipelineRole to `CodeDeploy:*`
* we should grant the `LambdaCodeDeployRole` the permission related to the S3 bucket. 
