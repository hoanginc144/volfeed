# A GET RESToverHTTP sample demonstrating the generation of signatures and signing of requests.

import os
import base64
import hmac
import time
import json
from dotenv import load_dotenv
import requests
from datetime import datetime
import pytz

load_dotenv()


def sign_request(secret_key, method, path, body):
    """ Sign a request with the given secret key. """
    signing_key = base64.b64decode(secret_key)

    ts = str(int(time.time() * 1000)).encode('utf-8')
    message = b'\n'.join([ts, method.upper(), path, body])
    digest = hmac.digest(signing_key, message, 'sha256')
    sig = base64.b64encode(digest)

    return ts, sig


access_key = os.getenv('PARADIGM_ACCESS_KEY')
secret_key = os.getenv('PARADIGM_SECRET_KEY')
host = 'https://api.prod.paradigm.trade'

# GET /v2/drfq/trade_tape
method = 'GET'
path = '/v2/drfq/trade_tape?venue=DBT&product_codes=DO&page_size=100'

payload = ''

timestamp, signature = sign_request(secret_key=secret_key,
                                    method=method.encode('utf-8'),
                                    path=path.encode('utf-8'),
                                    body=payload.encode('utf-8'),
                                    )

headers = {
    'Paradigm-API-Timestamp': timestamp,
    'Paradigm-API-Signature': signature,
    'Authorization': f'Bearer {access_key}'
}

# Send request
# response = requests.get(
#     host+path,
#     headers=headers,
#     timeout=10
# )

"""Create a while loop to handle pagination, in the response there's a 'next' key that
we will use as param 'cursor' to get the next page. Loop 10 times to get 1000 records,
wait for 1 second before making the next request.
"""

# initial request to get the first page
response = requests.get(
    host+path,
    headers=headers,
    timeout=10
)

# create a list to store response of each page
responses = []

# append the first page response to the list
for item in response.json()['results']:
    responses.append(item)


# loop 10 times to get 1000 records
for i in range(9):
    # check if the response has a 'next' key, if not break the loop
    if 'next' in response.json():
        cursor = response.json()['next']
        path = path+f'&cursor={cursor}'
        timestamp, signature = sign_request(secret_key=secret_key,
                                            method=method.encode('utf-8'),
                                            path=path.encode('utf-8'),
                                            body=payload.encode('utf-8'),
                                            )
        headers = {
            'Paradigm-API-Timestamp': timestamp,
            'Paradigm-API-Signature': signature,
            'Authorization': f'Bearer {access_key}'
        }
        response = requests.get(
            host+path,
            headers=headers,
            timeout=10
        )
        for item in response.json()['results']:
            responses.append(item)
        # print(response.json())
        time.sleep(1)
    else:
        break


# Create a list of dictionary, loop through the response and extract only the relevant fields to append to the list
data = []
for item in responses:
    # check if key 'kind' is 'OPTION', if not skip the record
    if item['kind'] == 'OPTION':
        data.append({
            'id': item['id'],
            'rfq_id': item['rfq_id'],
            'currency': item['quote_currency'],
            'time_of_trade': datetime.fromtimestamp(item['filled_at']/1000, tz=pytz.utc).strftime('%Y-%m-%d %H:%M:%S +0000'),
            'side': item['side'],
            'quantity': float(item['quantity']),
            'price': float(item['price']),
            'mark_price': float(item['mark_price']),
            'strategy_code': item['strategy_code'],
            'strategy_name': item['description'].split()[0],
            # loop through the legs and extract the relevant fields, assign incrementing leg number
            'legs': [{
                'leg_id': i,
                'expiry_date': datetime.strptime(leg['instrument_name'].split('-')[1], '%d%b%y').strftime('%Y-%m-%d 08:00:00 +0000'),
                'strike': int(leg['instrument_name'].split('-')[2]),
                'option_type': leg['instrument_name'].split('-')[3].lower(),
                'direction': leg['side'].lower(),
                'price': float(leg['price']),
                'product_code': leg['product_code'],
                'quantity': float(leg['quantity'])
            }
                for i, leg in enumerate(item['legs'])]
        })
    else:
        continue

# normalize the data by unpacking the legs
# data = [dict(item, **leg) for item in data for leg in item.pop('legs')]

print(json.dumps(data, indent=2))
print(f"Total number of records: {len(data)}")
