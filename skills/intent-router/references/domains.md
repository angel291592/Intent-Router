# Outside code

The three passes and the sufficiency predicate are domain-independent. Only the probe surfaces
change, and "objective answer" always means the same thing: *whatever this environment gives you
access to*. Load this file when the request is not about a codebase.

The judgement to keep: in a code workspace most unknowns are lookups. In a conversation-only
setting most are not, and the run degrades toward asking. That is still better than guessing, but
the win is smaller, and saying so is more useful than pretending otherwise.

## Multi-role assistants and routing registries

The request is "help me with this", and the real question is which specialist, tool or workflow
should take it.

| unknown | probe surface |
|---|---|
| which candidate role fits | the candidate registry and its descriptions |
| what the user actually brought | attachment metadata: file types, counts, sizes, names |
| what has been tried already | conversation or ticket history for this user |
| which constraints already apply | the user's profile, tier, locale, saved preferences |

Typical question worth asking: two candidates genuinely overlap and the difference matters to the
outcome — "is this a response to an office action, or a landscape analysis of the same patents?"

Typical question **not** worth asking: which of two candidates handles a case that the registry
already disambiguates. Consult the registry.

### Negative criteria are mandatory

A candidate that only declares what it is for will absorb neighbouring requests. Every entry in a
routing registry declares both directions:

```
route to me when:      <the cases this candidate owns>
do not route to me when: <a neighbouring case> -> <the candidate that owns it>
```

One-directional descriptions are what every comparable router ships, and they are why overlapping
roles bleed into each other. Sharpening a description does not fix the overlap; naming the
neighbour does. Treat the "do not route to me when" clause as a required field of registration,
not documentation.

### Ambiguous predicates lower confidence — they do not license a pick

When the request's verb is a placeholder — "sort this out", "deal with it", "handle this" — and
more than one candidate could plausibly claim it, that is an `ask`-kind unknown about scope, and
`confidence` stays low. Picking the most likely candidate and proceeding is the exact behaviour
this skill replaces.

## Support and service triage

The request is a customer problem, and the decisions are about entitlement and remedy.

| unknown | probe surface |
|---|---|
| what happened | ticket history, event log, order or shipment records |
| what the account is entitled to | plan, contract terms, warranty window, prior goodwill credits |
| what has already been offered | earlier tickets and their resolutions |
| what policy allows | the policy document in force, with its effective date |

Typical question worth asking: refund or replacement, when both are permitted and the customer's
preference decides — and when issuing one forecloses the other.

Typical question **not** worth asking: whether the purchase is inside the warranty window. That
is a record, not an opinion.

Irreversibility matters more here than in code: a refund issued, a subscription cancelled, or a
record deleted cannot be walked back. Mark those constraints `irreversible: true`, and never
accept a delegated answer for them.

## Research and analysis assistants

The request is "look into X", and the decisions are about scope, depth and sourcing.

| unknown | probe surface |
|---|---|
| what is already known | prior notes, previous reports, cached retrievals |
| which sources count | the source list or allow-list already in use |
| how deep to go | the format and length of prior deliverables |
| what the deadline implies | the calendar or task record, if exposed |

Typical question worth asking: depth versus breadth when both are defensible and the deliverable
changes shape — "a two-page brief on the three leading options, or a full comparison of all
eleven?"

Typical question **not** worth asking: whether a source has already been read. Consult the notes.

## Operations and data work

| unknown | probe surface |
|---|---|
| current state | the schema, the dashboard, the last run's output |
| what changed recently | change log, deployment history, incident records |
| what the job is allowed to touch | permissions, retention policy, environment boundaries |

Typical question worth asking: whether a backfill may rewrite historical rows. That is
irreversible and usually not written down anywhere.

## A domain not listed here: derive its probe surfaces

The six surfaces in the main instructions are the code instance of a general procedure. To work a
domain that has no table above, ask four questions of it — each maps onto the code surfaces and
onto the parse categories:

1. **System of record** — what actually happened here, and which system holds the authoritative
   record of it? (the code surfaces' manifests and entry points; maps to `scope` and
   `data_compatibility`)
2. **Policy in force** — what is allowed and what is forbidden, and what version or effective date
   does that policy carry? (maps to `non_goals_constraints` and `approach`)
3. **Prior handling** — how was this handled last time, and was it ever reversed or rejected?
   (the code domain's version history; maps to `approach`)
4. **Inventory** — where is the authoritative list of the objects this request can act on? (the
   code domain's route and command definitions; maps to `scope`)

A domain table is nothing more than these four questions answered with concrete places. Write the
places down, and the domain compiles like code does.

## Irreversibility outside code

Outside code, irreversible actions are the norm rather than the exception: money has moved, a
message or a commitment has already reached a third party, quota or capacity has been consumed,
data or records have been deleted, an external system has already placed an order or scheduled
work. Mark such constraints `irreversible: true` — which means `ask-protocol.md`'s rule against
accepting a delegated answer for irreversible decisions fires far more often here than it does in
a codebase.

## What stays the same in every domain

1. The iron law: if an objective answer exists and you can reach it, look it up.
2. The predicate: `unknown` empty, and no inferred constraint that is irreversible.
3. Two halt causes, never merged: `underspecified` is the requester's next move, `degraded` is an
   operations signal.
4. Evidence on everything probed or inferred. Outside the filesystem use the two reserved
   namespaces: `record:<system>/<id>` for a record in a system of record,
   `doc:<slug>#<section>` for a document section that has no path. No file check can verify
   either form, so fabricating one is worse than fabricating a path — point only at records or
   sections you actually read.
5. The emitted artifact is the same `IntentSpec`, with the same fields, so downstream consumers do
   not need to know which domain produced it.
