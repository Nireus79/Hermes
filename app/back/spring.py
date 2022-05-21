import os
from licensespring.api import APIClient

# https://docs.licensespring.com/docs/apiclient-usage-examples
spring_api_key = os.environ['spring_api_key']
spring_shared_key = os.environ['spring_shared_key']
spring_license_key = os.environ['spring_license_key']
product = "h1"
api_client = APIClient(api_key=spring_api_key, shared_key=spring_shared_key)


# Activate key based license
def activation():
    activate_key = api_client.activate_license(product=product, license_key=spring_license_key)
    return activate_key


# Check key based license
def check():
    check_key = api_client.check_license(product=product, license_key=spring_license_key)
    return check_key
