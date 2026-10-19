# Example: sync Clearfacts into Odoo from a script or Odoo shell.
#
#   cd /path/to/odoo
#   python odoo-bin shell -d yourdb
#
# Then:
#
#   from clearfacts import ClearfactsClient
#   cf = ClearfactsClient(token="...")
#   for admin in cf.administrations():
#       print(admin.name, admin.vat_number)
#
# Or use the Odoo UI: Accounting > Configuration > Clearfacts > Sync now.

from clearfacts import ClearfactsClient


def main():
    import os
    token = os.environ.get("CLEARFACTS_TOKEN")
    if not token:
        raise SystemExit("Set CLEARFACTS_TOKEN to your 80-char personal access token.")
    cf = ClearfactsClient(token=token)
    print(cf.test_token())
    for admin in cf.administrations():
        print("-", admin.name, admin.company_number)
        for j in cf.journals(admin.company_number):
            print("   journal", j.id, j.name)


if __name__ == "__main__":
    main()
