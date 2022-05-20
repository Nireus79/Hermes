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
    # {'license_signature':
    # 'REDACTEDREDACTED',
    # 'validity_period': None,
    # 'product_features': [],
    # 'license_type': 'perpetual',
    # 'license_key': 'REDACTED',
    # 'is_trial': False,
    # 'maintenance_period': None,
    # 'custom_fields': [],
    # 'max_activations': 1,
    # 'times_activated': 1,
    # 'customer': {'email': 'hermes_algotrading@proton.me',
    # 'company_name': None,
    # 'reference': '',
    # 'phone': '',
    # 'first_name': 'Themis',
    # 'last_name': 'Angelopoulos',
    # 'customer_account': None},
    # 'allow_overages': False,
    # 'max_overages': 0,
    # 'prevent_vm': False,
    # 'is_floating_cloud': False,
    # 'is_floating': False,
    # 'floating_timeout': 120,
    # 'transfer_count': 0,
    # 'max_transfers': 0,
    # 'start_date': None,
    # 'product_details': {'product_id': 1586066454419926,
    # 'product_name': 'Hermes',
    # 'short_code': 'h1',
    # 'authorization_method': 'license-key'}}
    activate_key = api_client.activate_license(product=product, license_key=license_key)
    return activate_key


# Check key based license
def check():
    # {'license_enabled': True, 'license_active': True, 'license_type': 'perpetual', 'license_key':
    # 'REDACTED', 'is_trial': False, 'product_features': [], 'order_store_id':
    # '837438ff74d2496aaf6eeee51d4dd8b1', 'maintenance_period': None, 'validity_period': None, 'custom_fields': [],
    # 'max_activations': 1, 'times_activated': 1, 'start_date': None, 'customer': {'email':
    # 'hermes_algotrading@proton.me', 'company_name': None, 'reference': '', 'phone': '', 'first_name': 'Themis',
    # 'last_name': 'Angelopoulos', 'customer_account': None}, 'allow_overages': False, 'max_overages': 0,
    # 'prevent_vm': False, 'is_floating_cloud': False, 'is_floating': False, 'floating_timeout': 120,
    # 'transfer_count': 0, 'product_details': {'product_id': 1586066454419926, 'product_name': 'Hermes',
    # 'short_code': 'h1', 'authorization_method': 'license-key'}, 'is_expired': False, 'is_borrowed': False,
    # 'borrowed_until': None, 'version': '', 'installation_file': '', 'release_date': '', 'hash_md5': '',
    # 'requires_version': '', 'environment': '', 'eula_link': '', 'release_notes_link': '', 'size': '', 'channel':
    # '', 'license_signature':
    # 'REDACTED
    # REDACTED'}
    check_key = api_client.check_license(product=product, license_key=license_key)
    return check_key


# r = {'license_enabled': True, 'license_active': True, 'license_type': 'perpetual', 'license_key':
# 'REDACTED', 'is_trial': False, 'product_features': [], 'order_store_id':
# '837438ff74d2496aaf6eeee51d4dd8b1', 'maintenance_period': None, 'validity_period': None, 'custom_fields': [],
# 'max_activations': 1, 'times_activated': 1, 'start_date': None, 'customer': {'email':
# 'hermes_algotrading@proton.me', 'company_name': None, 'reference': '', 'phone': '', 'first_name': 'Themis',
# 'last_name': 'Angelopoulos', 'customer_account': None}, 'allow_overages': False, 'max_overages': 0, 'prevent_vm':
# False, 'is_floating_cloud': False, 'is_floating': False, 'floating_timeout': 120, 'transfer_count': 0,
# 'product_details': {'product_id': 1586066454419926, 'product_name': 'Hermes', 'short_code': 'h1',
# 'authorization_method': 'license-key'}, 'is_expired': False, 'is_borrowed': False, 'borrowed_until': None,
# 'version': '', 'installation_file': '', 'release_date': '', 'hash_md5': '', 'requires_version': '', 'environment':
# '', 'eula_link': '', 'release_notes_link': '', 'size': '', 'channel': '', 'license_signature':
# 'REDACTED
# REDACTED'}
#
# print(r['license_active'])
