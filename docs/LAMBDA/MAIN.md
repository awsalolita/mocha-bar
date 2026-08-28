```bash
# Publish a version of your function

aws lambda publish-version \
  --function-name my-function \
  --description "Version 1 - initial release"

# Create an alias pointing to that version
aws lambda create-alias \
  --function-name my-function \
  --name live \
  --function-version 1

```

