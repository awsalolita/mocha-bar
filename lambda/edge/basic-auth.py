import base64

USERNAME = "saleh"
PASSWORD = "Saleh123"

def lambda_handler(event, context):
    # Get the request and headers from the CloudFront event
    request = event['Records'][0]['cf']['request']
    headers = request.get('headers', {})
    # Configure your authentication credentials
    auth_user = USERNAME
    auth_pass = PASSWORD
    # Construct the Base64 encoded Basic Auth string
    auth_string = f"{auth_user}:{auth_pass}"
    encoded_auth_string = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    expected_header = f"Basic {encoded_auth_string}"

    # Extract the authorization header if it exists
    auth_header = headers.get('authorization')

    # Check if the header is missing or incorrect
    if not auth_header or auth_header[0]['value'] != expected_header:
        # Return 401 Unauthorized response
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
        
    # Continue request processing if authentication passed
    return request