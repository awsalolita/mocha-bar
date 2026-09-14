import json
import boto3

sm_client = boto3.client('secretsmanager')

def lambda_handler(event, context):
    arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    # Validate version stage
    metadata = sm_client.describe_secret(SecretId=arn)
    if not metadata['RotationEnabled']:
        raise ValueError(f"Secret {arn} is not enabled for rotation.")
    
    versions = metadata['VersionIdsToStages']
    if token not in versions:
        raise ValueError(f"Secret version {token} has no stage for rotation of secret {arn}.")
    
    if "AWSCURRENT" in versions[token]:
        return # Already rotated
    elif "AWSPENDING" not in versions[token]:
        raise ValueError(f"Secret version {token} not set as AWSPENDING for {arn}.")

    # Execute corresponding step
    if step == "createSecret":
        create_secret(arn, token)
    elif step == "setSecret":
        set_secret(arn, token)
    elif step == "testSecret":
        test_secret(arn, token)
    elif step == "finishSecret":
        finish_secret(arn, token)
    else:
        raise ValueError(f"Invalid step: {step}")

def create_secret(arn, token):
    try:
        sm_client.get_secret_value(SecretId=arn, VersionId=token, VersionStage="AWSPENDING")
    except sm_client.exceptions.ResourceNotFoundException:
        # Generate new credentials (e.g., call secretsmanager.get_random_password)
        new_password = sm_client.get_random_password(ExcludePunctuation=True)['RandomPassword']
        current_dict = json.loads(sm_client.get_secret_value(SecretId=arn, VersionStage="AWSCURRENT")['SecretString'])
        
        current_dict['password'] = new_password
        sm_client.put_secret_value(
            SecretId=arn,
            ClientRequestToken=token,
            SecretString=json.dumps(current_dict),
            VersionStages=['AWSPENDING']
        )

def set_secret(arn, token):
    pending_dict = json.loads(sm_client.get_secret_value(SecretId=arn, VersionId=token, VersionStage="AWSPENDING")['SecretString'])
    # Connect to the target resource (DB/Service) and update the user's password
    # Example: ALTER USER username WITH PASSWORD 'pending_dict["password"]'

def test_secret(arn, token):
    pending_dict = json.loads(sm_client.get_secret_value(SecretId=arn, VersionId=token, VersionStage="AWSPENDING")['SecretString'])
    # Attempt a test connection/login using pending credentials to confirm they work

def finish_secret(arn, token):
    metadata = sm_client.describe_secret(SecretId=arn)
    current_version = None
    for version, stages in metadata['VersionIdsToStages'].items():
        if "AWSCURRENT" in stages:
            if version == token:
                return # Already current
            current_version = version
            break

    # Finalize by moving AWSCURRENT to the pending token
    sm_client.update_secret_version_stage(
        SecretId=arn,
        VersionStage="AWSCURRENT",
        MoveToVersionId=token,
        RemoveFromVersionId=current_version
    )