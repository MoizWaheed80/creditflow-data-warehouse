# CreditFlow Seed Data: Known Issues (intentionally injected)

These records were deliberately seeded as dirty data to give the Bronze-to-Silver
transformation layer real problems to catch and document.

## Duplicates (6)
- {'original_id': 72, 'duplicate_id': 181, 'date': '2026-09-02', 'amount': 2375.68}
- {'original_id': 13, 'duplicate_id': 182, 'date': '2026-05-14', 'amount': 4214.12}
- {'original_id': 38, 'duplicate_id': 183, 'date': '2026-07-30', 'amount': 2285.15}
- {'original_id': 49, 'duplicate_id': 184, 'date': '2026-08-12', 'amount': 4455.26}
- {'original_id': 123, 'duplicate_id': 185, 'date': '2026-08-26', 'amount': 3978.8}
- {'original_id': 142, 'duplicate_id': 186, 'date': '2026-04-15', 'amount': 715.44}

## Outliers (5)
- {'id': 187, 'amount': 75000.0}
- {'id': 188, 'amount': 68000.0}
- {'id': 189, 'amount': 1.0}
- {'id': 190, 'amount': 3.5}
- {'id': 191, 'amount': 62000.0}

## Draft Only (4)
- {'id': 192}
- {'id': 193}
- {'id': 194}
- {'id': 195}

## Vague Description (3)
- {'id': 196, 'description': 'TBD'}
- {'id': 197, 'description': 'asdf test'}
- {'id': 198, 'description': 'asdf test'}

## Future Dated (1)
- {'id': 199, 'date': '2026-09-30'}

## Near Duplicate Vendor (3)
- {'id': 200, 'vendor_id': 18}
- {'id': 201, 'vendor_id': 17}
- {'id': 202, 'vendor_id': 18}

