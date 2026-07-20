# Dogfood #02, early lease exit (anonymized retrospective replay)

> **Evidence level:** a real, fully anonymized rental dispute; the tenant side was ratified
> retrospectively, the landlord side is inferred from the record. This is stronger than a synthetic
> scenario but is **not** bilateral dogfood: the landlord has not reviewed or ratified the encoded
> position or result. Presented as a de-identified case study, not tied to any named party.

## What happened

On a 12-month lease, the tenant's income supporting the rent ended and they asked to leave early with
one to two months' notice. The landlord treated the fixed term as payable while also showing the
property to an interested replacement. The deposit equalled two months of rent and utility advances.
With no agreed early-exit option, the tenant stayed those two months to consume the deposit; a later
settlement added utilities, cleaning, and damage, part of which an insurer covered.

Fully anonymized: all names, addresses, exact amounts, contact details, and account data are excluded,
and nothing here identifies any real party. No claim is made that the replacement ultimately moved in.

## Positions encoded

### Tenant, ratified

Hard red lines:

- no separate penalty merely for ending the lease early;
- no rent or penalty for a period also paid by a replacement tenant;
- damage is charged only with invoices;
- insurance payments reduce the tenant's balance.

Soft priorities: recover as much deposit as possible, leave quickly, avoid additional debt, and get
a transparent final settlement. Private information included available cash and maximum ability to
pay. The fallback was to stay for two months and consume the deposit, not because that was preferred,
but because no deposit-return exit was offered.

### Landlord, inferred, not ratified

Hard red lines inferred from the correspondence: at least one month of rent coverage and payment of
documented property costs. Soft preferences: more continuous rent coverage and a ready replacement.

## Options tested

1. One-month notice, a replacement tenant, and deposit return after documented costs.
2. The observed fallback: remain for two months and consume the deposit.
3. Re-let immediately while also retaining an early-exit penalty.
4. Walk away immediately with the full deposit and no protection against vacancy or damage.

Run it:

```bash
.venv/bin/python examples/demo/proofcard.py examples/demo/recipe_early_lease_exit.json /tmp/lease-exit.html
```

## Retrospective value signal

The tenant ratified option 1 in conversation on 2026-07-14:

> Parley would have been better if it helped us agree on my early exit with the deposit returned
> after real costs, while the landlord moved a new tenant in immediately. The property would not
> have sat empty, the landlord would not have lost income, and I would not have stayed two extra
> months solely to consume the deposit.

## Honest boundary

This replay shows that the mechanism can identify a mutually feasible alternative that the original
negotiation did not surface. It does **not** prove the landlord would accept it. Bilateral validation
requires the landlord, or an independent landlord facing the same decision, to encode their own
private sheet and ratify or reject the result.
