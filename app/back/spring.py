from licensespring.api import APIClient

# TODO store credentials
api_key = 'REDACTED'
shared_key = 'REDACTED'

product = "h1"
license_key = 'REDACTED'

api_client = APIClient(api_key=api_key, shared_key=shared_key)

# Activate key based license
activate_key = api_client.activate_license(product=product, license_key=license_key)

# Check key based license
check_key = api_client.check_license(product=product, license_key=license_key)

print(activate_key)

print(check_key)
