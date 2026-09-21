from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import AuditLog
from forecasting.models import AIProcurementAlert
from forecasting.services import generate_all_forecasts
from forecasting.supplier_rhythm import compute_all_rhythms


class Command(BaseCommand):
    help = "Compute forecasts for all ingredients and generate AI procurement alerts for HIGH/MEDIUM risk items. Also computes supplier delivery rhythms. Intended for cron: 0 2 * * * python manage.py compute_forecasts"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Window days for daily usage calc")
        parser.add_argument("--dry-run", action="store_true", help="Don't create, just report")
        parser.add_argument("--include-rhythm", action="store_true", default=True, help="Compute supplier delivery rhythms (default: True)")
        parser.add_argument("--rhythm-only", action="store_true", help="Only compute supplier rhythms, skip consumption forecasts")

    def handle(self, *args, **options):
        days = options["days"]
        dry = options["dry_run"]
        include_rhythm = options["include_rhythm"]
        rhythm_only = options["rhythm_only"]

        rhythm_created = 0
        rhythm_updated = 0
        rhythm_skipped = 0

        # Phase 1: Supplier Rhythm Computation
        if include_rhythm or rhythm_only:
            if dry:
                self.stdout.write("[DRY] Would compute supplier rhythms...")
            else:
                rhythm_created, rhythm_updated, rhythm_skipped = compute_all_rhythms()
                self.stdout.write(f"  Supplier rhythms: {rhythm_created} created, {rhythm_updated} updated, {rhythm_skipped} skipped")

        if rhythm_only:
            if not dry:
                AuditLog.objects.create(
                    action="CRON_RHYTHM",
                    module="Forecasting",
                    details=f"compute_forecasts (rhythm-only) created {rhythm_created} predictions, updated {rhythm_updated}, skipped {rhythm_skipped} at {timezone.now():%Y-%m-%d %H:%M}",
                )
            self.stdout.write(self.style.SUCCESS(f"Rhythm computation complete: {rhythm_created} created, {rhythm_updated} updated, {rhythm_skipped} skipped."))
            return

        # Phase 2: Consumption-based Forecasting (existing)
        rows = generate_all_forecasts(days_window=days)
        created = 0
        skipped = 0
        for r in rows:
            if r["risk"] in {"HIGH", "MEDIUM"} and r["reorder"] > 0:
                exists = AIProcurementAlert.objects.filter(
                    ingredient=r["ingredient"], status=AIProcurementAlert.Status.PENDING
                ).exists()
                if exists:
                    skipped += 1
                    continue
                if dry:
                    self.stdout.write(f"[DRY] Would create alert {r['ingredient'].name} risk {r['risk']} qty {r['reorder']} days {r['days']}")
                else:
                    AIProcurementAlert.objects.create(
                        ingredient=r["ingredient"],
                        suggested_quantity=r["reorder"],
                        predicted_stockout_date=r["stockout_date"],
                        daily_usage=r["daily"],
                        days_until_stockout=r["days"],
                        risk=r["risk"],
                        reason=f"Auto: stockout in {r['days']} days ({r['daily']}/day)",
                    )
                    created += 1

        if not dry:
            AuditLog.objects.create(
                action="CRON_FORECAST",
                module="Forecasting",
                details=f"compute_forecasts created {created} alerts (skipped {skipped} dup), rhythms: {rhythm_created} new/{rhythm_updated} updated at {timezone.now():%Y-%m-%d %H:%M}",
            )

        self.stdout.write(self.style.SUCCESS(
            f"Forecasts computed: {len(rows)} ingredients, {created} new alerts, {skipped} skipped duplicate pending. "
            f"Rhythms: {rhythm_created} created, {rhythm_updated} updated, {rhythm_skipped} skipped."
        ))
