# cleanup_all.py
from herbalapp.models import IncomeRecord, SponsorIncome, BonusRecord, Member

def run_cleanup():
    root = Member.objects.get(id=74)

    # --- IncomeRecord Cleanup ---
    records = IncomeRecord.objects.filter(member=root, type="binary_engine").order_by("created_at")
    print(f"Total IncomeRecords before cleanup: {records.count()}")
    if records.exists():
        latest = records.last()
        IncomeRecord.objects.filter(member=root, type="binary_engine").exclude(id=latest.id).delete()
        print(f"✅ IncomeRecord cleanup done. Kept id={latest.id}, amount={latest.amount}")
    print(f"Total IncomeRecords after cleanup: {IncomeRecord.objects.filter(member=root, type='binary_engine').count()}")

    # --- SponsorIncome Cleanup ---
    sponsor_records = SponsorIncome.objects.filter(sponsor=root).order_by("date")
    print(f"\nTotal SponsorIncome before cleanup: {sponsor_records.count()}")
    if sponsor_records.exists():
        latest = sponsor_records.last()
        SponsorIncome.objects.filter(sponsor=root).exclude(id=latest.id).delete()
        print(f"✅ SponsorIncome cleanup done. Kept id={latest.id}, amount={latest.amount}")
    print(f"Total SponsorIncome after cleanup: {SponsorIncome.objects.filter(sponsor=root).count()}")

    # --- BonusRecord Cleanup ---
    bonus_records = BonusRecord.objects.filter(member=root).order_by("created_at")
    print(f"\nTotal BonusRecord before cleanup: {bonus_records.count()}")
    if bonus_records.exists():
        latest = bonus_records.last()
        BonusRecord.objects.filter(member=root).exclude(id=latest.id).delete()
        print(f"✅ BonusRecord cleanup done. Kept id={latest.id}, amount={latest.amount}")
    print(f"Total BonusRecord after cleanup: {BonusRecord.objects.filter(member=root).count()}")

    print("\n✅ All-in-one cleanup complete. Latest authoritative records only retained.")

# Run cleanup
if __name__ == "__main__":
    run_cleanup()

