from licensespring.api import APIClient
# https://docs.licensespring.com/docs/apiclient-usage-examples

# TODO store credentials
api_key = 'REDACTED'
shared_key = 'REDACTED'

product = "h1"
license_key = 'REDACTED'

api_client = APIClient(api_key=api_key, shared_key=shared_key)


# Activate key based license
def activation():
    activate_key = api_client.activate_license(product=product, license_key=license_key)
    return activate_key


# Check key based license
def check():
    check_key = api_client.check_license(product=product, license_key=license_key)
    return check_key
