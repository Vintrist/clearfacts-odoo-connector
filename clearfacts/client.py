import base64
import json
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from . import config
from .models import (
    Accountant, Administration, ArchiveCategories, Associate, AssociateGroup,
    BusinessPartner, CompanyStatistic, Document, FileUploadResult, Journal,
)


class ClearfactsAuthError(Exception):
    pass


class ClearfactsAPIError(Exception):
    def __init__(self, message: str, errors: Optional[list] = None):
        super().__init__(message)
        self.errors = errors or []


class _OIDCHandler(BaseHTTPRequestHandler):
    """Catches the authorization-code redirect on localhost."""

    code: Optional[str] = None

    def do_GET(self):  # type: ignore[override]
        qs = parse_qs(urlparse(self.path).query)
        _OIDCHandler.code = (qs.get("code") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Authorization received.</h1><p>You can close this tab.</p>")

    def log_message(self, fmt, *args):  # type: ignore[override]
        return


class ClearfactsClient:
    """Thin, typed wrapper around the Clearfacts GraphQL API.

    Auth: pass a personal access token, or use from_oidc() for the
    authorization-code flow. Both produce an 80-char bearer token.
    """

    def __init__(
        self,
        token: str,
        graphql_url: str = config.GRAPHQL_URL,
        timeout: int = config.DEFAULT_TIMEOUT,
    ):
        if not token or len(token) < 10:
            raise ValueError("token is required")
        self.token = token
        self.graphql_url = graphql_url
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
        )

    # —— factories ——

    @staticmethod
    def from_oidc(
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8765/callback",
        scopes: Optional[list[str]] = None,
        open_browser: bool = True,
    ) -> "ClearfactsClient":
        """Run the authorization-code flow and return an authenticated client."""
        scopes = scopes or [
            "openid", "email", "profile", "read_administrations", "journal_read",
            "contact_read", "upload_document", "archive", "accountant", "statistics",
        ]
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
        }
        auth_url = f"{config.OIDC_AUTHORIZE}?{urlencode(params)}"
        if open_browser:
            webbrowser.open(auth_url)
        print(f"Open this URL if the browser did not launch:\n{auth_url}\n")

        host, port = "localhost", int(urlparse(redirect_uri).port or 8765)
        server = HTTPServer((host, port), _OIDCHandler)
        server.handle_request()
        code = _OIDCHandler.code
        if not code:
            raise ClearfactsAuthError("No authorization code received")

        resp = requests.post(
            config.OIDC_TOKEN,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=config.DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            raise ClearfactsAuthError(f"Token exchange failed: {resp.status_code} {resp.text}")
        body = resp.json()
        access = body.get("access_token")
        if not access:
            raise ClearfactsAuthError(f"No access_token in response: {body}")
        return ClearfactsClient(token=access)

    # —— transport ——

    def _gql(self, query: str, variables: Optional[dict] = None) -> dict:
        payload: dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables
        resp = self._session.post(
            self.graphql_url,
            json=payload,
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise ClearfactsAPIError(f"HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        if data.get("errors"):
            msgs = "; ".join(e.get("message", "?") for e in data["errors"])
            raise ClearfactsAPIError(msgs, data["errors"])
        return data.get("data") or {}

    def _gql_form(self, query: str, variables: dict, file_field: tuple[str, bytes, str]) -> dict:
        """multipart/form-data variant used by file-upload mutations."""
        filename, content, mtype = file_field
        resp = self._session.post(
            self.graphql_url,
            data={"query": query, "variables": json.dumps(variables)},
            files={"file": (filename, content, mtype)},
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise ClearfactsAPIError(f"HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        if data.get("errors"):
            msgs = "; ".join(e.get("message", "?") for e in data["errors"])
            raise ClearfactsAPIError(msgs, data["errors"])
        return data.get("data") or {}

    # —— queries ——

    def accountant(self) -> Accountant:
        data = self._gql(
            """query { accountant {
                name, companyNumber, email,
                address { streetAddress, country { iso2, name } }
            } }"""
        )
        return Accountant.from_dict(data["accountant"])

    def associates(self) -> list[Associate]:
        data = self._gql("query { associates { id, email } }")
        return [Associate.from_dict(a) for a in data.get("associates") or []]

    def associate_groups(self) -> list[AssociateGroup]:
        data = self._gql("query { associateGroups { id, name } }")
        return [AssociateGroup.from_dict(g) for g in data.get("associateGroups") or []]

    def administrations(self) -> list[Administration]:
        data = self._gql(
            """query { administrations {
                name, companyNumber, accountManager,
                emails { type, emailAddress },
                address { streetAddress, country { iso2, name } }
            } }"""
        )
        return [Administration.from_dict(a) for a in data.get("administrations") or []]

    def administration(self, company_number: str) -> Administration:
        data = self._gql(
            """query ($cn: String!) { administration(companyNumber: $cn) {
                name, companyNumber, accountManager,
                emails { type, emailAddress },
                address { streetAddress, country { iso2, name } }
            } }""",
            {"cn": company_number},
        )
        return Administration.from_dict(data["administration"])

    def journals(self, company_number: str) -> list[Journal]:
        data = self._gql(
            """query ($cn: String!) { journals(companyNumber: $cn) {
                id, name, creditNote
            } }""",
            {"cn": company_number},
        )
        return [Journal.from_dict(j) for j in data.get("journals") or []]

    def customers(self, company_number: str, page_size: int = 100):
        """Yield pages of BusinessPartner (max 100 per page)."""
        offset = 0
        while True:
            data = self._gql(
                """query ($cn: String!, $off: Int) { customers(
                    companyNumber: $cn, offset: $off
                ) { id, name } }""",
                {"cn": company_number, "off": offset},
            )
            page = [BusinessPartner.from_dict(c) for c in data.get("customers") or []]
            if not page:
                break
            yield page
            if len(page) < page_size:
                break
            offset += page_size

    def document(self, document_id: str) -> Document:
        data = self._gql(
            """query ($id: ID!) { document(id: $id) {
                date, ... on InvoiceDocument { type, paymentState }
            } }""",
            {"id": document_id},
        )
        d = data["document"]
        d["id"] = document_id
        return Document.from_dict(d)

    def archive_categories(self, vat_number: str) -> ArchiveCategories:
        data = self._gql(
            """query ($vat: String!) { archiveCategories(vatnumber: $vat) {
                various { id, name }, permanent { id, name }
            } }""",
            {"vat": vat_number},
        )
        return ArchiveCategories.from_dict(data["archiveCategories"])

    def company_statistics(
        self, stat_type: str, start_period: str, end_period: str
    ) -> list[CompanyStatistic]:
        """stat_type: 'AIR' or 'processing'. Periods like '2025-01-01'."""
        data = self._gql(
            """query ($t: String!, $s: String!, $e: String!) {
                getCompanyStatistics(
                    type: $t, startPeriod: $s, endPeriod: $e
                ) { companyNumber, items { period, value } }
            }""",
            {"t": stat_type, "s": start_period, "e": end_period},
        )
        return [CompanyStatistic.from_dict(s) for s in data.get("getCompanyStatistics") or []]

    # —— mutations ——

    def upload_file(
        self,
        vat_number: str,
        filename: str,
        invoice_type: str,
        file_path: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        content_type: str = "application/pdf",
    ) -> FileUploadResult:
        """Upload an invoice/purchase document to an administration inbox.

        invoice_type: 'PURCHASE' or 'SALE'. File: PDF, JPEG or XML
        (Peppol Billing 3.0 / UBL.BE / legacy E-FFF).
        """
        if file_bytes is None:
            if not file_path:
                raise ValueError("provide file_path or file_bytes")
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            if content_type == "application/pdf" and file_path.lower().endswith(".jpg"):
                content_type = "image/jpeg"
        data = self._gql_form(
            "mutation ($vat: String!, $fn: String!, $it: InvoiceTypeArgument!) {"
            " uploadFile(vatnumber: $vat, filename: $fn, invoicetype: $it)"
            " { uuid, amountOfPages } }",
            {"vat": vat_number, "fn": filename, "it": invoice_type},
            (filename, file_bytes, content_type),
        )
        return FileUploadResult.from_dict(data["uploadFile"])

    def upload_archive_file(
        self,
        vat_number: str,
        filename: str,
        archive_type: str,
        category_id: str,
        file_path: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        content_type: str = "application/pdf",
    ) -> FileUploadResult:
        """Upload to the Various or Permanent archive. archive_type: 'VARIOUS' or 'PERMANENT'."""
        if file_bytes is None:
            if not file_path:
                raise ValueError("provide file_path or file_bytes")
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        data = self._gql_form(
            "mutation ($vat: String!, $fn: String!, $t: VariousType!, $cat: String!) {"
            " uploadArchiveFile(vatnumber: $vat, filename: $fn, type: $t, category: $cat)"
            " { uuid, amountOfPages } }",
            {"vat": vat_number, "fn": filename, "t": archive_type, "cat": category_id},
            (filename, file_bytes, content_type),
        )
        return FileUploadResult.from_dict(data["uploadArchiveFile"])

    def add_associate(
        self,
        first_name: str,
        last_name: str,
        email: str,
        associate_type: str = "ADMIN",
        group_ids: Optional[list[str]] = None,
        active: bool = True,
        language: str = "nl_BE",
        send_activation_mail: bool = False,
    ) -> Associate:
        variables = {
            "associate": {
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "type": associate_type,
                "associateGroups": [{"id": g} for g in (group_ids or [])],
                "active": active,
                "language": language,
                "sendActivationMail": send_activation_mail,
            }
        }
        data = self._gql_form(
            "mutation ($associate: AddAssociateArgument!) {"
            " addAssociate(associate: $associate) {"
            " id, plainPassword, associateGroups { id, name } } }",
            variables,
            ("", b"", "application/octet-stream"),
        )
        return Associate.from_dict(data["addAssociate"])

    def edit_associate(self, associate_id: str, **fields: Any) -> Associate:
        """Edit an associate. Accepts firstName, lastName, email, active, language, ..."""
        data = self._gql(
            "mutation ($id: ID!, $associate: EditAssociateArgument!) {"
            " editAssociate(id: $id, associate: $associate) { id, firstName } }",
            {"id": associate_id, "associate": fields},
        )
        return Associate.from_dict(data["editAssociate"])

    def update_app_info(
        self,
        vat_number: str,
        image_url: Optional[str] = None,
        email_address: Optional[str] = None,
        badge_text: Optional[str] = None,
        badge_text_color: Optional[str] = None,
        badge_color: Optional[str] = None,
        icon_type: Optional[str] = None,
        icon_color: Optional[str] = None,
    ) -> dict:
        data = self._gql_form(
            "mutation ($vat: String!, $img: String, $em: String, $bt: String,"
            " $btc: String, $bc: String, $it: String, $ic: String) {"
            " updateAppInfo(vatnumber: $vat, imageUrl: $img, emailaddress: $em,"
            " badge: { text: $bt, textColor: $btc, color: $bc },"
            " icon: { type: $it, color: $ic })"
            " { vatnumber, imageUrl, emailaddress, icon { type, color },"
            " badge { text, textColor, color } } }",
            {
                "vat": vat_number, "img": image_url, "em": email_address,
                "bt": badge_text, "btc": badge_text_color, "bc": badge_color,
                "it": icon_type, "ic": icon_color,
            },
            ("", b"", "application/octet-stream"),
        )
        return data["updateAppInfo"]

    # —— helpers ——

    def test_token(self) -> dict:
        """Hit /userinfo to verify the token. Returns sub/username/email."""
        resp = self._session.get(config.OIDC_USERINFO, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
