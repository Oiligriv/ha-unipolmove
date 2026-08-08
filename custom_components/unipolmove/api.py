"""Client for the Unipolmove ('www.unipolmove.it') customer area.

Login is a plain username/password form POST with no CAPTCHA (verified
against a real browser capture), so this integration performs the actual
login itself - unlike the ACEA integration, which deliberately does not.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date

import aiohttp

_LOGGER = logging.getLogger(__name__)

from .const import (
    BASE_URL,
    CONTESTO_UTENTE_URL,
    COSTI_AGGREGATI_URL_TEMPLATE,
    ENVIRONMENT_URL,
    FATTURE_URL_TEMPLATE,
    IBM_CLIENT_ID,
    IBM_CLIENT_SECRET,
    IBM_HEADER_SETS,
    LOGIN_PAGE_URL,
    LOGIN_URL,
    USER_AGENT,
)


class UnipolmoveAuthError(Exception):
    """Raised when login fails or the session has expired."""


class UnipolmoveApiError(Exception):
    """Raised on unexpected responses from Unipolmove."""


@dataclass
class Invoice:
    invoice_number: str | None
    invoice_date: date | None
    amount: float | None
    status: str | None
    merchant: str | None
    refund_amount: float | None


@dataclass
class CostiAggregati:
    transiti: float | None
    area_c: float | None
    parcheggi: float | None
    traghetti: float | None
    prenotazione_parcheggi: float | None


@dataclass
class UnipolmoveData:
    invoices: list[Invoice] = field(default_factory=list)
    costi: CostiAggregati | None = None

    @property
    def latest_invoice(self) -> Invoice | None:
        return self.invoices[0] if self.invoices else None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _flatten_invoices(raw: dict) -> list[dict]:
    flat: list[dict] = []
    for anno_entry in raw.get("listaFatture", []):
        for mese_entry in anno_entry.get("fattureFNCAnnoList", []):
            flat.extend(mese_entry.get("fattureFNCMese", {}).get("invoices", []))
    return flat


def _parse_invoices(raw: dict) -> list[Invoice]:
    flat = _flatten_invoices(raw)
    invoices = [
        Invoice(
            invoice_number=inv.get("invoiceNumber"),
            invoice_date=_parse_date(inv.get("invoiceDate")),
            amount=inv.get("invoiceAmount"),
            status=inv.get("paymentStatus"),
            merchant=inv.get("merchantName"),
            refund_amount=inv.get("refundAmount"),
        )
        for inv in flat
    ]
    invoices.sort(key=lambda i: i.invoice_date or date.min, reverse=True)
    return invoices


def _parse_costi(raw: dict) -> CostiAggregati:
    return CostiAggregati(
        transiti=raw.get("importoTransiti"),
        area_c=raw.get("importoAreaC"),
        parcheggi=raw.get("importoParcheggi"),
        traghetti=raw.get("importoTraghetti"),
        prenotazione_parcheggi=raw.get("importoPrenotazioneParcheggi"),
    )


class UnipolmoveApiClient:
    def __init__(self, session, username: str, password: str, contract_id: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._contract_id = contract_id
        self._session_id = uuid.uuid4().hex
        self._ibm_config: dict | None = None

    @property
    def session(self):
        return self._session

    def set_credentials(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    async def _async_ibm_config(self) -> dict:
        """Fetch and cache the web app's own API Connect configuration."""
        if self._ibm_config is not None:
            return self._ibm_config
        try:
            async with self._session.get(
                ENVIRONMENT_URL, headers={"User-Agent": USER_AGENT}
            ) as resp:
                if resp.status != 200:
                    raise UnipolmoveApiError(f"environment.json status {resp.status}")
                # Served as text/plain, so content-type checking has to be off.
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, ValueError, UnipolmoveApiError) as err:
            _LOGGER.warning(
                "Unipolmove: could not read environment.json (%s); falling back to "
                "the built-in telepedaggio-us credentials, so aggregate costs will "
                "not be available",
                err,
            )
            self._ibm_config = {}
        else:
            self._ibm_config = data.get("apiConnect", {})
        return self._ibm_config

    async def _ibm_headers_for(self, url: str) -> dict:
        """Return the client id/secret pair the gateway serving this URL expects.

        Each API Connect gateway has its own subscription, and sending one
        gateway's pair to another is rejected with a 401 even though the session
        cookie is perfectly valid. The web app makes the same choice from the
        URL; IBM_HEADER_SETS mirrors that mapping.
        """
        config = await self._async_ibm_config()
        for prefix, config_key in IBM_HEADER_SETS:
            if prefix in url:
                if block := config.get(config_key):
                    return {
                        "x-ibm-client-id": block["x-ibm-client-id"],
                        "x-ibm-client-secret": block["x-ibm-client-secret"],
                    }
                break
        return {"x-ibm-client-id": IBM_CLIENT_ID, "x-ibm-client-secret": IBM_CLIENT_SECRET}

    def _headers(self, *, api: bool, referer: str = BASE_URL + "/") -> dict:
        # X-UNIPOL-SEQUENCEID is NOT an incrementing per-request counter: a
        # real browser capture shows it hardcoded to "0" on every single
        # call (login, contesto-utente, catalogo, cms, ...), never anything
        # else - confirmed across an entire session including a failed
        # login attempt followed by a successful one.
        headers = {
            "Accept": "application/json",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": USER_AGENT,
            "Origin": BASE_URL,
            "Referer": referer,
            "X-UNIPOL-SESSIONID": self._session_id,
            "X-UNIPOL-REQUESTID": str(uuid.uuid4()),
            "X-UNIPOL-SEQUENCEID": "0",
        }
        # The x-ibm-* pair is added by the callers instead, through
        # _ibm_headers_for(), because which pair is correct depends on the URL.
        return headers

    async def async_login(self) -> None:
        # Warm-up: a real browser always hits the site (and the login page)
        # before ever posting credentials, picking up load-balancer/session
        # cookies (e.g. the F5 "TS..." cookie) along the way. Posting
        # straight to /login with an empty cookie jar/bot-like headers can
        # get silently flagged/shadow-rejected by the BigIP WAF fronting
        # this site even while still returning HTTP 200 - so replicate a
        # real browser as closely as reasonably possible (see _headers()
        # for the User-Agent/Origin/Referer reasoning).
        async with self._session.get(
            LOGIN_PAGE_URL, headers=self._headers(api=False, referer=BASE_URL + "/")
        ):
            pass

        async with self._session.post(
            LOGIN_URL,
            data={"username": self._username, "password": self._password},
            headers=self._headers(api=False, referer=LOGIN_PAGE_URL),
        ) as resp:
            body = await resp.text()
            # Neither the response headers nor the body are logged here: the
            # headers carry the Set-Cookie session token, and debug logs are
            # routinely pasted into bug reports. The body is only quoted below
            # when the login actually failed, where it is an error message.
            _LOGGER.debug("Unipolmove login POST -> status=%s", resp.status)
            if resp.status != 200:
                raise UnipolmoveAuthError(f"Login fallito (status {resp.status}): {body[:200]}")

        headers = self._headers(api=True)
        headers.update(await self._ibm_headers_for(CONTESTO_UTENTE_URL))
        async with self._session.get(CONTESTO_UTENTE_URL, headers=headers) as resp:
            body = await resp.text()
            # This response is the account holder's profile (email, name), and
            # nothing is parsed out of it beyond the presence of "email", so
            # there is no reason to put it in a log file.
            _LOGGER.debug("Unipolmove contesto-utente GET -> status=%s", resp.status)
            if resp.status != 200:
                raise UnipolmoveAuthError(
                    f"Login fallito: credenziali non valide (contesto-utente status {resp.status}: {body[:200]})"
                )
            try:
                data = await resp.json()
            except ValueError as err:
                raise UnipolmoveAuthError("Login fallito: risposta inattesa") from err
            if not data.get("email"):
                raise UnipolmoveAuthError("Login fallito: credenziali non valide (nessuna email in risposta)")

    async def _get_json(self, url: str) -> dict:
        headers = self._headers(api=True)
        headers.update(await self._ibm_headers_for(url))
        async with self._session.get(url, headers=headers) as resp:
            body = await resp.text()
            _LOGGER.debug("Unipolmove GET %s -> status=%s body=%s", url, resp.status, body[:500])
            if resp.status in (401, 403):
                raise UnipolmoveAuthError("Sessione Unipolmove scaduta")
            if resp.status != 200:
                raise UnipolmoveApiError(f"Errore API {resp.status} su {url}: {body[:200]}")
            try:
                return await resp.json()
            except ValueError as err:
                raise UnipolmoveApiError(f"Risposta non valida da {url}") from err

    async def async_get_data(self) -> UnipolmoveData:
        fatture_url = FATTURE_URL_TEMPLATE.format(contract_id=self._contract_id) + "?limite=50"
        costi_url = COSTI_AGGREGATI_URL_TEMPLATE.format(contract_id=self._contract_id)

        fatture_raw = await self._get_json(fatture_url)

        # costiAggregati lives behind a different IBM API Connect gateway
        # (portale-tlpd/servizi-mobilita vs telepedaggio-us) and needs that
        # gateway's own client id/secret, which _ibm_headers_for() now selects.
        # Still optional: if environment.json cannot be read the correct pair is
        # unavailable and this 401s again, and invoices should keep working.
        try:
            costi_raw = await self._get_json(costi_url)
            costi = _parse_costi(costi_raw)
        except (UnipolmoveApiError, UnipolmoveAuthError):
            _LOGGER.warning(
                "Unipolmove: impossibile recuperare i costi aggregati (pedaggi/Area C/parcheggi); "
                "le fatture continuano a funzionare normalmente",
                exc_info=True,
            )
            costi = None

        return UnipolmoveData(
            invoices=_parse_invoices(fatture_raw),
            costi=costi,
        )
