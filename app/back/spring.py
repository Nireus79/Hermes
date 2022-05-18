import base64
import hashlib
import hmac
import time
from wsgiref.handlers import format_date_time

import subprocess

import requests

API_URL = 'https://api.licensespring.com'
activation_URL = 'https://api.licensespring.com/api/v4/activate_license'

hardware_id = str(subprocess.check_output('wmic csproduct get uuid'), 'utf-8').split('\n')[1].strip()
# Can be found in `Account Settings` -> `Settings` -> `Keys`

# TODO store credentials
shared_key = 'REDACTED'
uuid = 'REDACTED'

product_short_code = 'h1'
license_key = 'REDACTED'


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


def authentication():
    response = requests.get(
        url='{}{}'.format(API_URL, '/api/v4/check_license/'),
        params={'product': product_short_code, 'hardware_id': hardware_id, 'license_key': license_key},
        headers={
            'Date': date_header,
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
    )
    return response.json()


print(authentication())
