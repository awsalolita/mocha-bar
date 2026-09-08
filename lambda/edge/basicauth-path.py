import base64

def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request.get('headers', {})
    
    # Get the requested path (URI)
    uri = request.get('uri', '')

    # Only apply auth if the path starts with /admin
    if uri.startswith('/admin'):
        auth_user = 'saleh'
        auth_pass = 'password'

        auth_string = f"{auth_user}:{auth_pass}"
        encoded_auth_string = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        expected_header = f"Basic {encoded_auth_string}"

        auth_header = headers.get('authorization')

        if not auth_header or auth_header[0]['value'] != expected_header:
            return {
                'status': '401',
                'statusDescription': 'Unauthorized',
                'body': 'Unauthorized',
                'headers': {
                    'www-authenticate': [
                        {
                            'key': 'WWW-Authenticate',
                            'value': 'Basic realm="Restricted Area"'
                        }
                    ]
                }
            }
            
    # If the path is not /admin, or if authentication passed, allow the request
    return request