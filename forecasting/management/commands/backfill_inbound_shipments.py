from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from inventory.models import InboundShipment, StockTransaction
from procurement.models import ProcurementRequest
from suppliers.models import Supplier


class Command(BaseCommand):
    help = "Backfill InboundShipment from historical data sources (ProcurementRequest + StockTransaction)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would be created without saving")
        parser.add_argument("--clear", action="store_true", help="Delete all existing InboundShipment records first")
        parser.add_argument("--source", choices=["all", "delivered", "ordered", "stock"], default="all", help="Limit to specific source")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        clear = options["clear"]
        source = options["source"]

        if clear:
            if dry_run:
                self.stdout.write("[DRY RUN] Would delete all InboundShipment records")
            else:
                deleted, _ = InboundShipment.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} existing InboundShipment records"))

        total_created = 0
        total_skipped = 0

        # Source 1: ProcurementRequest DELIVERED with actual_delivery_date
        if source in ("all", "delivered"):
            created, skipped = self._backfill_from_delivered_pr(dry_run)
            total_created += created
            total_skipped += skipped

        # Source 2: ProcurementRequest ORDERED with expected_delivery_date
        if source in ("all", "ordered"):
            created, skipped = self._backfill_from_ordered_pr(dry_run)
            total_created += created
            total_skipped += skipped

        # Source 3: StockTransaction ADDED with supplier_fk
        if source in ("all", "stock"):
            created, skipped = self._backfill_from_stock_transactions(dry_run)
            total_created += created
            total_skipped += skipped

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would create {total_created} InboundShipment records, skip {total_skipped} duplicates"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Backfill complete: {total_created} created, {total_skipped} skipped"))

    def _backfill_from_delivered_pr(self, dry_run):
        """Priority 1: DELIVERED PRs with actual_delivery_date"""
        qs = ProcurementRequest.objects.filter(
            status=ProcurementRequest.Status.DELIVERED,
            actual_delivery_date__isnull=False,
            supplier__isnull=False,
        ).select_related("supplier", "ingredient")

        return self._process_pr_queryset(qs, "DELIVERED+actual", dry_run)

    def _backfill_from_ordered_pr(self, dry_run):
        """Priority 2: ORDERED PRs with expected_delivery_date (no actual)"""
        qs = ProcurementRequest.objects.filter(
            status=ProcurementRequest.Status.ORDERED,
            expected_delivery_date__isnull=False,
            supplier__isnull=False,
        ).exclude(
            # Exclude if already has actual_delivery_date (would be in source 1)
            actual_delivery_date__isnull=False,
        ).select_related("supplier", "ingredient")

        return self._process_pr_queryset(qs, "ORDERED+expected", dry_run)

    def _process_pr_queryset(self, qs, source_label, dry_run):
        created = 0
        skipped = 0

        for pr in qs.iterator():
            supplier = pr.supplier
            ingredient = pr.ingredient
            received_at = pr.actual_delivery_date or pr.expected_delivery_date
            if not received_at:
                continue

            # Use delivered_quantity if available, else requested_quantity
            qty = pr.delivered_quantity or pr.requested_quantity
            unit_cost = pr.unit_price if pr.unit_price > 0 else None

            # Convert date to timezone-aware datetime at midnight
            received_dt = timezone.make_aware(datetime.combine(received_at, datetime.min.time()))

            # Deduplication key: supplier + ingredient + date + quantity
            exists = InboundShipment.objects.filter(
                supplier=supplier,
                ingredient=ingredient,
                received_at__date=received_at,
                quantity_received=qty,
            ).exists()

            if exists:
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"  [DRY] {source_label}: {supplier} -> {ingredient} qty={qty} on {received_at}")
            else:
                InboundShipment.objects.create(
                    supplier=supplier,
                    ingredient=ingredient,
                    procurement_request=pr,
                    quantity_received=qty,
                    received_at=received_dt,
                    unit_cost=unit_cost,
                    notes=f"Backfilled from {source_label} PR-{pr.pk:04d}",
                )
                created += 1

        self.stdout.write(f"  {source_label}: {created} created, {skipped} skipped")
        return created, skipped

    def _backfill_from_stock_transactions(self, dry_run):
        """Priority 3: StockTransaction ADDED with ingredient.supplier_fk"""
        qs = StockTransaction.objects.filter(
            transaction_type=StockTransaction.Type.ADDED,
            ingredient__supplier_fk__isnull=False,
        ).select_related("ingredient__supplier_fk", "ingredient")

        created = 0
        skipped = 0

        for tx in qs.iterator():
            supplier = tx.ingredient.supplier_fk
            ingredient = tx.ingredient
            received_at = tx.created_at
            qty = tx.quantity
            unit_cost = None  # Not available in StockTransaction

            # Deduplication key
            exists = InboundShipment.objects.filter(
                supplier=supplier,
                ingredient=ingredient,
                received_at__date=received_at.date(),
                quantity_received=qty,
            ).exists()

            if exists:
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"  [DRY] STOCK_TX: {supplier} -> {ingredient} qty={qty} on {received_at.date()}")
            else:
                InboundShipment.objects.create(
                    supplier=supplier,
                    ingredient=ingredient,
                    procurement_request=None,
                    quantity_received=qty,
                    received_at=received_at,
                    unit_cost=unit_cost,
                    notes=f"Backfilled from StockTransaction #{tx.pk}",
                )
                created += 1

        self.stdout.write(f"  STOCK_TX: {created} created, {skipped} skipped")
        return created, skipped