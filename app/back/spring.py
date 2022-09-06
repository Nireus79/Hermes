import os
from licensespring.api import APIClient

# https://docs.licensespring.com/docs/apiclient-usage-examples
API_KEY_SPRING = os.environ['API_KEY_SPRING']
SHARED_KEY_SPRING = os.environ['SHARED_KEY_SPRING']
LICENCE_KEY_SPRING = os.environ['LICENCE_KEY_SPRING']
product = "h1"
api_client = APIClient(api_key=API_KEY_SPRING, shared_key=SHARED_KEY_SPRING)


# Activate key based license
def activation():
    activate_key = api_client.activate_license(product=product, license_key=LICENCE_KEY_SPRING)
    return activate_key


# Check key based license
def check():
    check_key = api_client.check_license(product=product, license_key=LICENCE_KEY_SPRING)
    return check_key


print(activation())
