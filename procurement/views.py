from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import role_required
from accounts.models import Profile
from audit.services import log_action
from inventory.models import Ingredient, StockTransaction

from .forms import ProcurementForm
from .models import ProcurementRequest

from urllib.parse import quote
from inventory.models import StockTransaction as InvStockTx
from .services import generate_po_email, generate_po_viber, clean_phone_for_viber


MANAGEMENT = (
    Profile.Role.DEVELOPER,
    Profile.Role.OWNER,
    Profile.Role.MANAGER,
)


@role_required(*MANAGEMENT)
def procurement_list(request):
    status_filter = request.GET.get("status", "").upper()
    valid_statuses = {s.value for s in ProcurementRequest.Status}

    base_qs = ProcurementRequest.objects.select_related(
        "ingredient", "supplier", "requested_by", "approved_by"
    )

    counts = {
        "all": base_qs.count(),
        "pending": base_qs.filter(status=ProcurementRequest.Status.PENDING).count(),
        "approved": base_qs.filter(status=ProcurementRequest.Status.APPROVED).count(),
        "ordered": base_qs.filter(status=ProcurementRequest.Status.ORDERED).count(),
        "delivered": base_qs.filter(status=ProcurementRequest.Status.DELIVERED).count(),
    }

    filtered_qs = base_qs
    if status_filter in valid_statuses:
        filtered_qs = base_qs.filter(status=status_filter)
    else:
        status_filter = "ALL"

    ctx = {
        "requests": filtered_qs[:300],
        "active_status": status_filter,
        "counts": counts,
        "pending": counts["pending"],
        "approved": counts["approved"],
        "ordered": counts["ordered"],
        "delivered": counts["delivered"],
    }

    if request.headers.get("HX-Request"):
        return render(request, "procurement/_list_table.html", ctx)

    params = request.GET.copy()
    params["tab"] = "procurement"
    return redirect(f"{reverse('forecasting:forecast')}?{params.urlencode()}")


@role_required(*MANAGEMENT)
def create_request(request):
    initial = {}
    ing_id = request.GET.get("ingredient")
    qty = request.GET.get("qty")
    supplier_id = request.GET.get("supplier")
    reason = request.GET.get("reason")
    priority = request.GET.get("priority")
    if ing_id:
        initial["ingredient"] = ing_id
    if qty:
        initial["requested_quantity"] = qty
    if supplier_id:
        initial["supplier"] = supplier_id
    if reason:
        initial["reason"] = reason
    if priority in dict(ProcurementRequest.Priority.choices):
        initial["priority"] = priority
    # Auto-fill supplier from ingredient's supplier_fk if not supplied
    if ing_id and not request.POST.get("supplier"):
        try:
            ing = Ingredient.objects.select_related("supplier_fk").get(pk=ing_id)
            if ing.supplier_fk:
                initial["supplier"] = ing.supplier_fk
        except Ingredient.DoesNotExist:
            pass

    form = ProcurementForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.requested_by = request.user
        # If supplier blank but ingredient has linked supplier, auto-assign
        if not obj.supplier and obj.ingredient and getattr(obj.ingredient, "supplier_fk", None):
            obj.supplier = obj.ingredient.supplier_fk
        obj.save()

        log_action(
            request.user,
            "CREATE",
            "Procurement",
            obj.pk,
            f"Procurement request created for {obj.ingredient.name} qty {obj.requested_quantity}.",
        )

        messages.success(request, "Procurement request created.")
        return redirect("procurement")

    return render(request, "procurement/procurement.html", {"form": form})


@role_required(*MANAGEMENT)
def approve(request, pk):
    obj = get_object_or_404(ProcurementRequest, pk=pk)
    obj.status = ProcurementRequest.Status.APPROVED
    obj.approved_by = request.user
    obj.save(update_fields=["status", "approved_by", "updated_at"])

    log_action(request.user, "APPROVE", "Procurement", obj.pk, "Request approved.")
    messages.success(request, "Procurement request approved.")

    return redirect("procurement")


@role_required(*MANAGEMENT)
def reject(request, pk):
    obj = get_object_or_404(ProcurementRequest, pk=pk)
    obj.status = ProcurementRequest.Status.REJECTED
    obj.approved_by = request.user
    obj.save(update_fields=["status", "approved_by", "updated_at"])

    log_action(request.user, "REJECT", "Procurement", obj.pk, "Request rejected.")
    messages.success(request, "Procurement request rejected.")

    return redirect("procurement")


@role_required(*MANAGEMENT)
def mark_ordered(request, pk):
    obj = get_object_or_404(ProcurementRequest, pk=pk)
    if obj.status not in [ProcurementRequest.Status.APPROVED, ProcurementRequest.Status.PENDING]:
        messages.error(request, f"Cannot mark as ordered from status {obj.get_status_display()}.")
        return redirect("procurement")
    obj.status = ProcurementRequest.Status.ORDERED
    obj.approved_by = obj.approved_by or request.user
    obj.save(update_fields=["status", "approved_by", "updated_at"])
    log_action(request.user, "ORDERED", "Procurement", obj.pk, f"Request marked ordered: {obj.ingredient.name} qty {obj.requested_quantity}.")
    messages.success(request, f"Request PR-{obj.pk:04d} marked as Ordered.")
    return redirect("procurement")


@role_required(*MANAGEMENT)
def mark_delivered(request, pk):
    obj = get_object_or_404(ProcurementRequest.objects.select_related("ingredient", "supplier"), pk=pk)
    if obj.status not in [ProcurementRequest.Status.ORDERED, ProcurementRequest.Status.APPROVED]:
        messages.error(request, f"Cannot mark as delivered from status {obj.get_status_display()}. Approve/Order first.")
        return redirect("procurement")

    # Delivered quantity defaults to requested if not set
    delivered_qty = obj.delivered_quantity if obj.delivered_quantity is not None else obj.requested_quantity
    try:
        delivered_qty = Decimal(delivered_qty)
    except Exception:
        messages.error(request, "Invalid delivered quantity.")
        return redirect("procurement")

    if request.method == "POST":
        # Allow override via POST
        posted_qty = request.POST.get("delivered_quantity")
        if posted_qty:
            try:
                delivered_qty = Decimal(posted_qty)
            except Exception:
                messages.error(request, "Invalid delivered quantity input.")
                return redirect("procurement")

    with transaction.atomic():
        ingredient = Ingredient.objects.select_for_update().get(pk=obj.ingredient_id)
        previous = ingredient.quantity
        ingredient.quantity = ingredient.quantity + delivered_qty
        ingredient.save(update_fields=["quantity", "updated_at"])

        StockTransaction.objects.create(
            ingredient=ingredient,
            user=request.user,
            transaction_type=StockTransaction.Type.ADDED,
            quantity=delivered_qty,
            previous_stock=previous,
            remaining_stock=ingredient.quantity,
            reason=StockTransaction.Reason.NORMAL_USAGE,
            notes=f"Procurement PR-{obj.pk:04d} Delivered",
        )

        from django.utils import timezone
        obj.status = ProcurementRequest.Status.DELIVERED
        obj.delivered_quantity = delivered_qty
        obj.actual_delivery_date = timezone.now().date()
        if not obj.expected_delivery_date and obj.expected_date:
            obj.expected_delivery_date = obj.expected_date
        obj.approved_by = obj.approved_by or request.user
        obj.save(update_fields=["status", "delivered_quantity", "actual_delivery_date", "expected_delivery_date", "approved_by", "updated_at"])

        supplier = obj.supplier or getattr(ingredient, "supplier_fk", None)
        if supplier:
            from inventory.models import InboundShipment
            InboundShipment.objects.create(
                supplier=supplier,
                ingredient=ingredient,
                procurement_request=obj,
                quantity_received=delivered_qty,
                received_at=timezone.now(),
                unit_cost=obj.unit_price if obj.unit_price and obj.unit_price > 0 else (ingredient.unit_cost or None),
                notes=f"Delivered via PR-{obj.pk:04d}",
            )

        log_action(
            request.user,
            "DELIVERED",
            "Procurement",
            obj.pk,
            f"PR-{obj.pk:04d} delivered: {ingredient.name} +{delivered_qty} {ingredient.unit} ({previous} -> {ingredient.quantity}).",
        )

    messages.success(request, f"PR-{obj.pk:04d} delivered: {ingredient.name} restocked +{delivered_qty} {ingredient.unit}.")
    return redirect("procurement")


@role_required(*MANAGEMENT)
def po_email_draft(request, pk):
    obj = get_object_or_404(
        ProcurementRequest.objects.select_related("ingredient", "supplier", "requested_by"),
        pk=pk,
    )
    supplier = obj.supplier or getattr(obj.ingredient, "supplier_fk", None)

    # Handle inline actions from the dispatch view
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_phone" and supplier:
            new_phone = request.POST.get("phone", "").strip()
            supplier.phone = new_phone
            supplier.save(update_fields=["phone", "updated_at"])
            log_action(request.user, "UPDATE", "Suppliers", supplier.pk, f"Updated Viber contact for {supplier.company_name} to {new_phone}")
            messages.success(request, f"Updated Viber contact for {supplier.company_name} to {new_phone}.")
            return redirect("procurement_email", pk=pk)
        elif action == "mark_ordered":
            if obj.status in [ProcurementRequest.Status.PENDING, ProcurementRequest.Status.APPROVED]:
                obj.status = ProcurementRequest.Status.ORDERED
                obj.approved_by = obj.approved_by or request.user
                obj.save(update_fields=["status", "approved_by", "updated_at"])
                log_action(request.user, "ORDERED", "Procurement", obj.pk, f"Dispatched via PO Dispatch Hub: {obj.ingredient.name} qty {obj.requested_quantity}")
                messages.success(request, f"PR-{obj.pk:04d} marked as ORDERED.")
                return redirect("procurement_email", pk=pk)

    subject, body = generate_po_email(obj)
    viber_message = generate_po_viber(obj)

    phone = getattr(supplier, "phone", "") if supplier else ""
    viber_digits = clean_phone_for_viber(phone)
    viber_chat_url = f"viber://chat?number=%2B{viber_digits}" if viber_digits else ""
    viber_forward_url = f"viber://forward?text={quote(viber_message)}"

    context = {
        "obj": obj,
        "supplier": supplier,
        "subject": subject,
        "body": body,
        "viber_message": viber_message,
        "supplier_phone": phone,
        "viber_digits": viber_digits,
        "viber_chat_url": viber_chat_url,
        "viber_forward_url": viber_forward_url,
    }
    return render(request, "procurement/email_draft.html", context)

