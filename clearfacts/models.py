from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Country:
    iso2: str
    name: str

    @staticmethod
    def from_dict(d: dict) -> "Country":
        return Country(iso2=d.get("iso2", ""), name=d.get("name", ""))


@dataclass
class Address:
    street_address: str
    country: Country

    @staticmethod
    def from_dict(d: Optional[dict]) -> Optional["Address"]:
        if not d:
            return None
        return Address(
            street_address=d.get("streetAddress", ""),
            country=Country.from_dict(d.get("country") or {}),
        )


@dataclass
class Accountant:
    name: str
    company_number: str
    email: str
    address: Optional[Address] = None

    @staticmethod
    def from_dict(d: dict) -> "Accountant":
        return Accountant(
            name=d.get("name", ""),
            company_number=d.get("companyNumber", ""),
            email=d.get("email", ""),
            address=Address.from_dict(d.get("address")),
        )


@dataclass
class Email:
    type: str
    email_address: str

    @staticmethod
    def from_dict(d: dict) -> "Email":
        return Email(type=d.get("type", ""), email_address=d.get("emailAddress", ""))


@dataclass
class Administration:
    name: str
    company_number: str
    account_manager: str
    emails: list[Email] = field(default_factory=list)
    address: Optional[Address] = None

    @property
    def vat_number(self) -> str:
        """Company number without a possible BE prefix."""
        cn = self.company_number
        return cn[2:] if cn.upper().startswith("BE") else cn

    @staticmethod
    def from_dict(d: dict) -> "Administration":
        return Administration(
            name=d.get("name", ""),
            company_number=d.get("companyNumber", ""),
            account_manager=d.get("accountManager", ""),
            emails=[Email.from_dict(e) for e in (d.get("emails") or [])],
            address=Address.from_dict(d.get("address")),
        )


@dataclass
class Associate:
    id: str
    email: str
    first_name: str = ""
    last_name: str = ""
    active: bool = True
    language: str = ""
    associate_groups: list["AssociateGroup"] = field(default_factory=list)
    plain_password: str = ""

    @staticmethod
    def from_dict(d: dict) -> "Associate":
        return Associate(
            id=d.get("id", ""),
            email=d.get("email", ""),
            first_name=d.get("firstName", ""),
            last_name=d.get("lastName", ""),
            active=bool(d.get("active", True)),
            language=d.get("language", ""),
            associate_groups=[
                AssociateGroup.from_dict(g) for g in (d.get("associateGroups") or [])
            ],
            plain_password=d.get("plainPassword", ""),
        )


@dataclass
class AssociateGroup:
    id: str
    name: str

    @staticmethod
    def from_dict(d: dict) -> "AssociateGroup":
        return AssociateGroup(id=d.get("id", ""), name=d.get("name", ""))


@dataclass
class Journal:
    id: str
    name: str
    credit_note: bool

    @staticmethod
    def from_dict(d: dict) -> "Journal":
        return Journal(
            id=d.get("id", ""),
            name=d.get("name", ""),
            credit_note=bool(d.get("creditNote", False)),
        )


@dataclass
class BusinessPartner:
    id: str
    name: str

    @staticmethod
    def from_dict(d: dict) -> "BusinessPartner":
        return BusinessPartner(id=d.get("id", ""), name=d.get("name", ""))


@dataclass
class FileUploadResult:
    uuid: str
    amount_of_pages: int

    @staticmethod
    def from_dict(d: dict) -> "FileUploadResult":
        return FileUploadResult(
            uuid=d.get("uuid", ""),
            amount_of_pages=int(d.get("amountOfPages") or 0),
        )


@dataclass
class Category:
    id: str
    name: str

    @staticmethod
    def from_dict(d: dict) -> "Category":
        return Category(id=d.get("id", ""), name=d.get("name", ""))


@dataclass
class ArchiveCategories:
    various: list[Category] = field(default_factory=list)
    permanent: list[Category] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "ArchiveCategories":
        return ArchiveCategories(
            various=[Category.from_dict(c) for c in (d.get("various") or [])],
            permanent=[Category.from_dict(c) for c in (d.get("permanent") or [])],
        )


@dataclass
class StatisticItem:
    period: str
    value: int

    @staticmethod
    def from_dict(d: dict) -> "StatisticItem":
        return StatisticItem(period=d.get("period", ""), value=int(d.get("value") or 0))


@dataclass
class CompanyStatistic:
    company_number: str
    items: list[StatisticItem] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "CompanyStatistic":
        return CompanyStatistic(
            company_number=d.get("companyNumber", ""),
            items=[StatisticItem.from_dict(i) for i in (d.get("items") or [])],
        )


@dataclass
class Document:
    id: str
    date: str
    doc_type: str = ""
    payment_state: str = ""

    @staticmethod
    def from_dict(d: dict) -> "Document":
        return Document(
            id=d.get("id", ""),
            date=d.get("date", ""),
            doc_type=d.get("type", ""),
            payment_state=d.get("paymentState", ""),
        )
