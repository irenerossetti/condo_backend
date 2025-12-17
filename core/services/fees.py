from __future__ import annotations
from django.db import transaction
from django.db.models import Sum
from core.models import Unit, ExpenseType, Fee, Payment


@transaction.atomic
def issue_fees(period: str, expense_type_id: int | None = None, amount: float | None = None) -> int:
    # ... (esta función no cambia)
    if not period or len(period) != 7 or period[4] != "-":
        raise ValueError("period debe ser 'YYYY-MM'")

    types = ExpenseType.objects.filter(active=True)
    if expense_type_id:
        types = types.filter(id=expense_type_id)

    created = 0
    for et in types:
        default_amount = float(et.amount_default or 0)
        for u in Unit.objects.only("id"):
            fee, was_created = Fee.objects.get_or_create(
                unit=u,
                expense_type=et,
                period=period,
                defaults={"amount": float(amount if amount is not None else default_amount)},
            )
            if not was_created and amount is not None and float(fee.amount) != float(amount):
                fee.amount = float(amount)
                fee.save(update_fields=["amount"])
            if was_created:
                created += 1
    return created


@transaction.atomic
def register_payment(fee_id: int, amount: float, method: str | None = None, note: str | None = None) -> dict:
    if amount is None:
        raise ValueError("amount es requerido")

    fee = Fee.objects.select_for_update().get(id=fee_id)
    Payment.objects.create(
        fee=fee,
        amount=float(amount),
        method=(method or "manual"),
        note=(note or "Pago manual"),
    )
    total_paid = Payment.objects.filter(fee=fee).aggregate(s=Sum("amount"))["s"] or 0

    # --- LÍNEA CORREGIDA ---
    # El valor que queremos para el estado es simplemente el string "PAID".
    # La línea anterior era innecesariamente compleja y tenía el error de mayúsculas.
    target_paid_value = "PAID"

    if float(total_paid) >= float(fee.amount) and fee.status != target_paid_value:
        fee.status = target_paid_value
        fee.save(update_fields=["status"])

    return {
        "fee_id": fee.id,
        "period": fee.period,
        "amount": float(fee.amount),
        "paid": float(total_paid),
        "status": fee.status,
    }