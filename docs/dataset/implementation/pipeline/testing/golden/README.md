# Golden records

One versioned JSON file per golden task. The format, versioning, and comparison
rules are in [`../golden-records.md`](../golden-records.md).

Do not edit a record to match a changed constructor. A diff is a reviewed claim
that the expected construction changed, and a failing record is a regression
until the construction contract is changed deliberately.
