from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from herbalapp.models import Member, IncomeRecord, SponsorIncome
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day

class Command(BaseCommand):
    help = "Run MLM engine and sponsor mirror credits per business rules"

    @transaction.atomic
    def handle(self, *args, **options):
        run_date = timezone.now().date()

        for member in Member.objects.all():
            # --- Count today's joins under left/right ---
            left_joins_today = Member.objects.filter(
                placement=member, side="left", joined_date=run_date
            ).count()
            right_joins_today = Member.objects.filter(
                placement=member, side="right", joined_date=run_date
            ).count()

            # --- Load carry forward from yesterday ---
            last = IncomeRecord.objects.filter(
                member=member, type="binary_engine"
            ).order_by("-created_at").first()
            if last:
                left_cf_before = last.left_cf_after or 0
                right_cf_before = last.right_cf_after or 0
            else:
                left_cf_before = 0
                right_cf_before = 0

            # --- Run binary engine ---
            result = calculate_member_binary_income_for_day(
                left_joins_today=left_joins_today,
                right_joins_today=right_joins_today,
                left_cf_before=left_cf_before,
                right_cf_before=right_cf_before,
                binary_eligible=member.binary_eligible,
                member=member,
                run_date=run_date
            )
            self.stdout.write(self.style.SUCCESS(f"{member.member_id} → {result}"))

            # --- Sponsor mirror already handled inside engine ---
            # If you want extra logging:
            if result["child_total_for_sponsor"] > 0:
                self.stdout.write(self.style.WARNING(
                    f"Sponsor mirror credited for {member.member_id}: {result['child_total_for_sponsor']}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Sponsor not credited: recipient not eligible for {member.member_id}"
                ))

