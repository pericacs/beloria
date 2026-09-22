"""Provider boundary. No real provider, prices or recurring rules are configured."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Checkout:
    reference: str
    amount_cents: int
    currency: str
    url: str


@dataclass(frozen=True)
class VerifiedPayment:
    event_id: str
    reference: str
    amount_cents: int
    currency: str
    paid_at: datetime
    valid_until: datetime


class PaymentProvider(Protocol):
    name: str
    def create_checkout(self, business_id: int, request_key: str) -> Checkout:
        """Must use provider idempotency and configured real pricing."""
    def verify_payment(self, body: bytes, signature: str) -> VerifiedPayment:
        """Verify signature AND settled status with provider. Never trust browser return."""


def get_provider() -> PaymentProvider | None:
    # Integrators must implement this boundary and configure price/period/provider.
    # There is deliberately no demo provider or payment activation switch.
    return None
