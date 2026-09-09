import base64

def generate_policy(principal_id, effect, resource):
    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource
            }]
        }
    }

def lambda_handler(event, context):
    token = event.get('authorizationToken', '')
    
    # Ensure the token exists and uses the Basic scheme
    if not token.startswith('Basic '):
        return generate_policy('unauthorized', 'Deny', event['methodArn'])
        
    try:
        # Extract and decode the base64 string
        encoded_credentials = token.split(' ')[1]
        decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
        username, password = decoded_credentials.split(':', 1)
        
        # Validate credentials (ideally against Secrets Manager or a database)
        if username == 'admin' and password == 'supersecret':
            return generate_policy(username, 'Allow', event['methodArn'])
        else:
            return generate_policy('unauthorized', 'Deny', event['methodArn'])
            
    except Exception:
        # Return Deny if the header is malformed
        return generate_policy('unauthorized', 'Deny', event['methodArn'])