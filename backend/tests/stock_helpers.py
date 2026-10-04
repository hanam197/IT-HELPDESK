"""Submit the signed template for stock tests that issue to a named person."""
import json as json_module
from pathlib import Path

TEMPLATE = (Path(__file__).resolve().parents[2] / '[Template]BBBANGIAONHANTHIEtBI.pdf').read_bytes()
INFO = {'sender_name': 'IT Administrator', 'sender_department': 'IT Helpdesk',
        'recipient_department': 'Operations', 'place': 'Văn phòng', 'purpose': 'Cấp mới', 'city': 'TP.HCM'}

def post_stock(client, json):
    if json.get('transaction_type') == 'ISSUE' and json.get('recipient_user_id'):
        return client.post('/api/inventory/issue-with-handover',
                           data={'payload': json_module.dumps(json), 'handover_info': json_module.dumps(INFO)},
                           files={'file': ('signed.pdf', TEMPLATE, 'application/pdf')})
    return client.post('/api/inventory/transactions', json=json)
