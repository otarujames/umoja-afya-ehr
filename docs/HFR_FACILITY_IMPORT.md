# Tanzania HFR Facility Import

Umoja Afya seeds a review network for immediate Docker evaluation. A current complete national master facility list must come from an approved Ministry HFR export rather than a static application list.

## Import

```bash
python scripts/import_hfr_facilities.py approved-hfr-export.csv \
  --base-url http://localhost:8000/api/v1 \
  --username <authorized-username> \
  --password <your-password>
```

Supported formats: CSV, JSON and YAML.

The importer recognizes common HFR headings such as Facility Code, Facility Name, Facility Type, Region, Council, Ownership Category and Ownership Authority. By default, it imports public/government facilities only. Use `--include-private` when a use-or-connect onboarding dataset is authorized.

## Effects

- Inserts or updates by system code/HFR code.
- Preserves HFR code, region, council, ownership, hierarchy and source system.
- Writes an import audit event.
- Grants imported facility contexts to active system-administrator accounts.
- Makes facilities searchable in Change Context.

## Governance

Use only an approved, current master-facility export. Retain the request/approval, file checksum, import report and reconciliation evidence as implementation records.
