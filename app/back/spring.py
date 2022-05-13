import base64
import hashlib
import hmac
import time
from wsgiref.handlers import format_date_time

import requests

API_URL = 'https://api.licensespring.com'

# Can be found in `Account Settings` -> `Settings` -> `Keys`
shared_key = '_your_shared_key_goes_here_'
uuid = '_your_uuid_key_goes_here_'


def sign(secret_key, datestamp):
    msg = 'licenseSpring\ndate: %s' % datestamp
    hashed = hmac.new(bytes(secret_key, 'utf-8'), msg.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(hashed).decode()


# Generate headers
date_header = format_date_time(time.time())

signing_key = sign(shared_key, date_header)

auth_header = ','.join([
    'algorithm="hmac-sha256"',
    'headers="date"',
    'signature="%s"' % signing_key,
    'apiKey="%s"' % uuid
])

# Send request
product_short_code = '_your_product_short_code_goes_here_'
hardware_id = '_your_hardware_id_goes_here_'
license_key = '_your_license_key_goes_here_'

response = requests.get(
    url='{}{}'.format(API_URL, '/api/v4/check_license/'),
    params={'product': product_short_code, 'hardware_id': hardware_id, 'license_key': license_key},
    headers={
        'Date': date_header,
        'Authorization': auth_header,
        'Content-Type': 'application/json'
    }
)

print(response.json())
