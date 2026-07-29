"""Constants for the Unipolmove integration.

Unipolmove (Telepass-style toll device by UnipolSai/Utech) logs in via a
plain username/password form POST with no CAPTCHA (verified from a real HAR
capture of www.unipolmove.it) - unlike ACEA, this can be fully automated: the
integration performs the real login itself.

The x-ibm-client-id/secret headers below are NOT a per-user secret: they are
a static IBM API Connect client identifier embedded in the public web app's
own JS bundle (sent by every visitor's browser, extracted here the same way
from normal browser network traffic), used by the gateway to identify "this
is the official web client" rather than to authenticate a specific person.
"""

DOMAIN = "unipolmove"

BASE_URL = "https://www.unipolmove.it"
LOGIN_URL = f"{BASE_URL}/login"
CONTESTO_UTENTE_URL = f"{BASE_URL}/api/us/prv/tpd/telepedaggio-us/vendita/v1/contesto-utente"
FATTURE_URL_TEMPLATE = (
    f"{BASE_URL}/api/us/prv/tpd/telepedaggio-us/post-vendita/v3/contratti/{{contract_id}}/fatture"
)
COSTI_AGGREGATI_URL_TEMPLATE = (
    f"{BASE_URL}/api/ut/prv/unipolmove/portale-tlpd/servizi-mobilita/v1/contratti/{{contract_id}}/costiAggregati"
)

IBM_CLIENT_ID = "035c8aa2-51fd-4f44-8d87-9535a1d4f8b6"
IBM_CLIENT_SECRET = "Y1oO6hC0oQ5fC3wL5bL6qB5oE8jN5mD0dL1jC5pC0iW5jR7mL6"

# aiohttp's default User-Agent identifies itself as a Python library, which
# BigIP (the WAF actually fronting this site - see the "Server: BigIP"
# response header) can silently flag/shadow-reject even while still
# returning HTTP 200. A realistic desktop Chrome UA avoids that.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)
LOGIN_PAGE_URL = f"{BASE_URL}/app/login"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_CONTRACT_ID = "contract_id"

UPDATE_INTERVAL_HOURS = 12
