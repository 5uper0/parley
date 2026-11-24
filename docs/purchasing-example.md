# Carrying a Parley decision into a purchasing system

An outside developer, Takao Sato, built this example. It is his work, not part of the Parley core, and we have not audited his code. The write-up is in [Discussion 92](https://github.com/5uper0/parley/discussions/92).

## What it shows

Parley's [procurement recipe](../examples/demo/recipe_procurement.json) picks Vendor A. The example then ties that decision to an order:

- The buying agent signs a purchase instruction that includes the hash of the Parley record.
- [VATE v0.7.0](https://github.com/Poke-nushi/Verifiable-Agent-Trust-Envelope/blob/v0.7.0/reference/caller-authority/README.md), a verifier draft Sato maintains, rechecks the agent's authority just before checkout.

The agent may buy from both Vendor A and Vendor B. A ZIP in the discussion replays four cases on synthetic purchase data:

| Case | Result |
| --- | --- |
| Order from A, tied to the original Parley record | Recorded |
| Order from B | Held back |
| Order from A citing a different Parley record that also selected A | Held back |
| Order from A after the grant was revoked | Stopped, though supplier and record still matched |

## What it does not show

- Parley does not check purchase authority. VATE does that part.
- The cases use synthetic data. No real purchase ran.
- One outside developer ran it once. It is not yet a team using Parley for a decision of its own.

## Run the quickstart first

The example starts from a Parley record. [The five-minute path](five-minute-path.md) produces one.
