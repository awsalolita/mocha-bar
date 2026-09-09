import jwt # Requires 'PyJWT' library

def lambda_handler(event, context):
    # 1. Extract token from the event
    token = event.get('authorizationToken', '')
    
    # Strip 'Bearer ' prefix if present
    if token.startswith('Bearer '):
        token = token.split(' ')[1]
        
    method_arn = event.get('methodArn')
    
    try:
        # 2. Decode and verify the JWT 
        # In production, fetch the public key/secret from AWS Secrets Manager or JWKS endpoint
        secret_key = "your-256-bit-secret" 
        decoded_payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        
        user_id = decoded_payload.get('sub')
        user_role = decoded_payload.get('role', 'user')
        
        # 3. Generate Allow policy and pass decoded role to backend
        auth_context = {'role': user_role}
        return generate_policy(user_id, 'Allow', method_arn, auth_context)
        
    except jwt.ExpiredSignatureError:
        print("Token has expired")
        return generate_policy('unauthorized', 'Deny', method_arn)
    except jwt.InvalidTokenError:
        print("Invalid token")
        return generate_policy('unauthorized', 'Deny', method_arn)

def generate_policy(principal_id, effect, resource, context_data=None):
    auth_response = {'principalId': principal_id}
    
    if effect and resource:
        auth_response['policyDocument'] = {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource
            }]
        }
        
    if context_data:
        auth_response['context'] = context_data
        
    return auth_response