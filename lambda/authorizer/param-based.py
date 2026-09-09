def lambda_handler(event, context):
    method_arn = event.get('methodArn')
    
    # 1. Extract query string parameters and request context variables
    query_params = event.get('queryStringParameters') or {}
    partner_id = query_params.get('partnerId')
    
    request_context = event.get('requestContext', {})
    identity = request_context.get('identity', {})
    source_ip = identity.get('sourceIp')
    
    # 2. Define business logic (Usually queried from a DynamoDB table)
    registered_partners = {
        'partner-alpha-882': ['192.168.1.50', '203.0.113.100'],
        'partner-beta-991': ['198.51.100.14']
    }
    
    # 3. Evaluate multi-variable conditions
    if not partner_id or not source_ip:
        return generate_policy('unknown', 'Deny', method_arn)
        
    allowed_ips = registered_partners.get(partner_id)
    
    if allowed_ips and source_ip in allowed_ips:
        # Request has valid partner ID AND originates from their specific IP
        context_data = {'partner_tier': 'enterprise'}
        return generate_policy(partner_id, 'Allow', method_arn, context_data)
    else:
        # Fails either ID check or IP allowlist check
        print(f"Failed auth for IP: {source_ip}, Partner: {partner_id}")
        return generate_policy(partner_id, 'Deny', method_arn)

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