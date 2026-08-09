# Formal model for authority across forkable agent executions

**Status:** research proposal, not a proved result and not yet the thesis of the current IntentCap paper.

**Purpose:** define a substantially different contribution from the current source-composition checker. The current paper asks **where an agent's authority may come from**. This model asks **what happens to authority when an adaptive agent forks, checkpoints, restores, delegates, aborts, and joins executions**.

The central position is:

> An agent may copy computation, but authority may be shared across branches only when their protected effects cannot become durable together.

The non-obvious part is not that rollback leaves some external resources unchanged. It is that a capability for a forkable agent cannot be modeled only as a permission set stored in a restorable process state, nor is “always split linear tokens at fork” an adequate replacement. A capability is constrained by the **commit compatibility** of the execution graph: which descendants' effects may coexist in one durable history. Mutually exclusive speculative branches may reserve the same bounded authority; concurrent or mergeable branches must be jointly accounted. Fork, restore, selection, and merge change this compatibility relation and are therefore authorization events.

This gives a sharper principle than “forking an agent must not fork its authority”:

> Fork does not decide whether authority is shared or split. The topology of possible durable outcomes does.

This document proposes the semantic object, transition system, security properties, theorem program, and smallest useful validation plan. Proposed theorems are deliberately labeled as such until mechanized.

## 1. Why this is a different research problem

The existing IntentCap model gives a branch an active lease and checks an event with

\[
\mathsf{check\_and\_consume}(e,\ell,p,\sigma)
  \rightarrow \mathsf{allow}(\sigma') \mid \mathsf{deny}.
\]

That model is meaningful on one serialized execution. It leaves several questions undefined once the runtime can copy or revisit execution state:

1. If a checkpoint contains an unused one-shot lease, may every restored branch use it?
2. If a branch consumed a budget and is then rewound, which state remembers the consumption?
3. If two speculative branches may need the same capability but only one will be selected, must the runtime guess at fork time which branch receives it?
4. If two subagents run in parallel, is their parent's budget copied, shared, or split?
5. If authority is revoked after a checkpoint, can restoring that checkpoint revive it?
6. If branches join, may unioning their local capability sets amplify authority or erase obligations?
7. If an external call may have succeeded but its response was lost, may abort or restore release the authority used for the call?

These are not merely filesystem or database rollback questions. Files and databases are examples of reversible local state. The security issue is a mismatch among three classes of state:

- **reconstructable state**, such as prompts, model memory, process memory, files in a copy-on-write sandbox, plans, and staged tool calls;
- **durable effects**, such as messages, payments, deployments, disclosed secrets, remote API mutations, human decisions, and actions observed by another principal; and
- **authority state**, such as approvals, quotas, revocation epochs, delegated budgets, reservations, and liabilities created by an attempted or completed effect.

A workspace snapshot may legitimately copy the first class. It cannot make the other two classes cease to exist. The model therefore applies more broadly to adaptive forkable computations, while agents make the problem acute because they routinely re-plan, re-synthesize calls after restore, fork subagents or best-of-\(N\) trajectories, and merge natural-language results.

## 2. Target contribution and non-contributions

### 2.1 Target contribution

The paper-level contribution should be a semantics of **execution-wide authority conservation** with five parts:

1. A capability denotes scoped authority plus a consumable resource, not just a set of allowed calls.
2. The runtime declares a downward-closed family of branch sets whose effects may become durable together.
3. Reconstructable branch state is separated from an append-only authority ledger and durable effect history.
4. Mutually exclusive alternatives use additive accounting; co-committable children use multiplicative accounting. Restore and merge may change one relation into the other.
5. Revocation, delegation, abort, selection, and join preserve the resulting topology-sensitive conservation invariant.

The strongest theorem opportunity is not ordinary anti-rollback. It is a characterization and impossibility pair: safe speculative sharing is exactly sharing among branches that cannot become jointly durable, and a monitor that cannot observe the branch-resolution topology cannot be both sound and maximally permissive. A simpler result about non-restorable authority state remains a useful foundation.

### 2.2 What must not be claimed as the novelty

The following ingredients are established techniques and are not contributions by themselves:

- capabilities, attenuation, revocation, or one-shot tokens;
- linear or affine resource accounting;
- partial commutative monoids and separation logic;
- append-only logs, write-ahead logging, idempotency keys, or transactional outboxes;
- checkpoint rollback protection;
- effect staging or compensation;
- provenance tracking or commit-time freshness checks.

The proposed delta is commit-compatibility-sensitive authority: one semantics that distinguishes legitimate speculative sharing from malicious cloning, admits late-bound exploration without pre-partitioning scarce authority, and treats a topology-changing restore or merge as an authorization decision. The resource algebra and durable ledger are proof and implementation machinery, not the novelty.

## 3. Threat model and semantic boundary

The agent, its model, tools that provide context, and branch scheduler may be adversarial. They may:

- request arbitrary operations and arguments;
- fork, restore, abort, or join at inconvenient times;
- retain and replay old checkpoints;
- retry a call with a fresh request identifier or a semantically modified payload;
- crash after an external effect but before its acknowledgement;
- delegate to compromised children; and
- merge untrusted branch outputs into later plans.

The trusted computing base contains:

- a small runtime implementing the transition rules below;
- an append-only, linearizable authority ledger;
- an effect adapter that records a durable claim before dispatch; and
- the mechanism that binds a claim identifier and effect digest to an outbound call.

The basic safety theorem does **not** assume that an external service offers transactions or idempotency. Without such support, an uncertain dispatched call remains charged and cannot be retried under fresh authority automatically. Idempotent retry under the same claim is an optional liveness improvement, not a safety assumption.

The model protects authorization integrity. It does not prove that an authorized effect is morally correct, that compensation exactly reverses harm, that the LLM interprets user intent correctly, or that a Byzantine external service executes the requested operation faithfully.

## 4. Semantic domains

### 4.1 Effects and histories

Let \(e\in\mathcal E\) be an effect descriptor. It contains at least an operation, object, arguments, target principal or service, and a semantic effect class. A policy may distinguish two byte-different requests as the same class of authority consumption. Authorization must therefore not depend only on a client-generated request identifier.

Execution is an append-only directed acyclic graph \(H\), not a single trace. A branch has a stable identity \(b\), an epoch \(\eta_b\), and one or more parents. Ordinary steps add a node with one parent; a join adds a node with multiple parents. A restored branch is a new descendant whose reconstructable state comes from an older checkpoint. It is never the erasure of nodes that already occurred.

We write \(x\prec_H y\) when event \(x\) causally precedes event \(y\). The durable projection \(\mathsf{dur}(H)\) contains claims, revocations, dispatched effects, acknowledgements, and unresolved outcomes. Restore may change the active branch projection but never removes an event from \(\mathsf{dur}(H)\).

### 4.2 Commit compatibility

At configuration \(\Sigma\), let \(\mathcal F_\Sigma\subseteq\mathcal P(\mathcal B)\) be a downward-closed family of **admissible durable frontiers**. A set \(C\in\mathcal F_\Sigma\) means that the tentative protected effects of every branch in \(C\) are permitted to survive together in one future durable history.

Two branch epochs are:

- **compatible**, written \(b_1\parallel_\Sigma b_2\), when some \(C\in\mathcal F_\Sigma\) contains both; or
- **conflicting**, written \(b_1\mathrel{\#_\Sigma}b_2\), when no admissible durable frontier contains both.

Compatibility is semantic, not merely ancestry. Children of a speculative choose-one fork conflict even though they run at the same time. Children spawned to perform independent work are compatible. A replacing restore conflicts with and permanently disables the old continuation; a restore that leaves the old continuation eligible to commit is a parallel fork. A join makes the selected parent results jointly durable and can therefore enlarge the compatibility family.

The family is part of the trusted branch-resolution contract. A transition that enlarges it must recheck authority. Declaring two branches conflicting and later retaining both without this check is authority amplification.

### 4.3 Authority as an event structure

A flat operation predicate cannot express “perform approval before publication,” “pay or dispute, but not both,” or “two independent children may each send one result.” A root grant therefore denotes a finite labeled event structure

\[
\mathcal A_g=
\langle U_g,\leq_g,\#_g,\lambda_g,\omega_g\rangle.
\]

- \(U_g\) is a set of unique authority-use events. Reusing the same event is a double spend.
- \(u\leq_g v\) means authority event \(u\) must precede \(v\).
- \(u\#_g v\) means the two authority uses are mutually exclusive.
- \(\lambda_g(u,e,w,H)\) decides whether concrete effect \(e\) and current witness \(w\) may instantiate \(u\).
- \(\omega_g(u,e)\) is the set of obligations incurred when \(u\) is exercised by \(e\).

A finite set \(X\subseteq U_g\) is a valid authority configuration when it is causally closed and conflict free:

\[
X\in\mathsf{Conf}(\mathcal A_g)
\quad\Longleftrightarrow\quad
(\forall v\in X.\,\downarrow v\subseteq X)
\land
(\forall u,v\in X.\,\neg(u\#_g v)).
\]

A quota of \(q\) identical uses is represented by \(q\) independent authority events with the same label predicate. A required sequence is represented by \(\leq_g\). Exclusive alternatives are represented by \(\#_g\). Independent parallel rights are unordered and non-conflicting. Persistent unbounded read permission is outside the finite core and is modeled as a duplicable fact guarded by the same non-rollbackable revocation epoch.

A root grant is

\[
g=\langle \mathit{id},\mathcal A_g,t_g,d_g,\nu_g\rangle,
\]

where \(t_g\) is its validity interval, \(d_g\) bounds delegation depth, and \(\nu_g\) is its revocation epoch. An allocation handle \(h\) owns a slice of unexercised events from \(\mathcal A_g\), possibly with narrower label predicates, more causal prerequisites, more conflicts, a shorter lifetime, or stronger obligations. Copying the serialized name of \(h\) does not copy event ownership. The live meaning of \(h\) is resolved in the authority ledger.

Let \(X_g\) contain authority events already exercised in a way that no branch resolution can erase. Let \(R_{b,g}\) be the tentative authority events reserved by branch \(b\) for commit-gated effects. The core embedding invariant is

\[
\forall C\in\mathcal F_\Sigma.\quad
X_g\cup\bigcup_{b\in C}R_{b,g}
\in\mathsf{Conf}(\mathcal A_g),
\tag{1}
\]

with an injective effect-to-authority-event mapping inside every such union. Conflicting branches may tentatively map their effects to the same unused authority event because they cannot coexist in a durable outcome. Compatible branches may not.

Valid authority configurations induce the partial resource composition

\[
X\odot Y=X\cup Y
\]

exactly when \(X\cap Y=\varnothing\) and \(X\cup Y\in\mathsf{Conf}(\mathcal A_g)\). This is the separation algebra used by delegation and join. The algebra is derived proof machinery; the proposed contribution is the embedding of possible durable execution frontiers into authority configurations.

For a scalar budget, Equation (1) reduces to

\[
\mathsf{used}_g+
\max_{C\in\mathcal F_\Sigma}
\sum_{b\in C}\mathsf{reserved}_{b,g}
\leq \mathsf{budget}_g.
\tag{2}
\]

Thus two conflicting branches may each tentatively reserve the same one-shot event, while compatible branches need distinct events. Every exercised event through a descendant handle is recorded at that handle and every allocation ancestor up to its root grant. This prevents delegation or branching from hiding resource consumption.

### 4.4 Choice and concurrency

For disjoint authority structures \(\mathcal A\) and \(\mathcal B\), define two standard compositions:

- \(\mathcal A\oplus\mathcal B\) adds conflict between every event from opposite sides, representing an exclusive future; and
- \(\mathcal A\otimes\mathcal B\) preserves both sides without cross-conflict, representing co-durable concurrency.

If \(\|\mathcal A\|\) is the largest cardinality of one of its valid configurations, then

\[
\|\mathcal A\oplus\mathcal B\|
=\max(\|\mathcal A\|,\|\mathcal B\|),
\qquad
\|\mathcal A\otimes\mathcal B\|
=\|\mathcal A\|+\|\mathcal B\|.
\]

A naive state clone silently treats one authority structure as \(\mathcal A\otimes\mathcal A\). A choose-one exploration needs additive conflict instead. The proposal does not claim these operators as new mathematics; it uses them to give fork, restore, and merge precise authority meaning. A topology-changing operation that turns \(\oplus\) into \(\otimes\) must pass the same admission check as a fresh grant.

### 4.5 Effect timing

Authority cannot be shared merely because branches are intended to be alternatives. It depends on when the protected effect becomes observable:

- A **commit-gated effect** remains local or in a trusted outbox until branch resolution. It contributes to \(R_{b,g}\) and may share capacity with conflicting branches.
- An **issue-time effect** becomes externally observable when invoked, such as reading a remote secret, revealing a query to a service, or sending a non-transactional request. Its authority event moves immediately to \(X_g\), even if its branch later loses.
- A **compensable effect** also moves its authority event to \(X_g\) when issued. Abort may create or preserve a compensation obligation, but compensation does not retroactively make the authority unused.

This distinction prevents a losing branch from laundering a disclosure or external mutation through `abort`. It also states precisely what an effect-gating runtime must provide before tentative authority sharing is sound.

### 4.6 State separation

A configuration is

\[
\Sigma=\langle H,\mathcal F,L,D,B,C\rangle.
\]

- \(H\) is the append-only execution graph.
- \(\mathcal F\) is the current family of admissible durable frontiers.
- \(L\) is the authoritative ledger of grants, allocation ownership, epochs, revocations, reservations, claims, and incurred obligations.
- \(D\) is the durable external-effect history, including acknowledged and uncertain dispatches.
- \(B\) maps each live branch to reconstructable local state.
- \(C\) maps checkpoint identifiers to snapshots of reconstructable state.

A branch-local state is

\[
B(b)=\langle q_b,K_b,S_b,O_b,\eta_b,\mathit{status}_b\rangle.
\]

- \(q_b\) is its reversible workspace and process state;
- \(K_b\) is branch-local knowledge with provenance;
- \(S_b\) is a set of staged, not-yet-durable effects;
- \(O_b\) is a set of offers naming authority that may later be allocated;
- \(\eta_b\) is the live branch epoch; and
- status is live, selected, quiescent, aborted, or tombstoned.

Crucially, \(B(b)\) does not contain an authoritative mutable balance. A checkpoint may serialize handle and offer identifiers for reconstruction, but their ownership, remaining capacity, and validity are read from \(L\) when used.

### 4.7 Claim states

A claim \(c\) is bound to a handle, one authority-use event \(u\), a branch epoch, an effect digest, and a fresh claim identifier. Its durable state is one of

\[
\mathsf{reserved}\rightarrow
\mathsf{dispatched}\rightarrow
\mathsf{acknowledged},
\]

with \(\mathsf{uncertain}\) reachable after a crash following dispatch. A commit-gated reservation remains topology-conditional only while the trusted runtime proves that no external issue occurred. At dispatch its event moves from \(R_{b,g}\) to globally exercised \(X_g\). A reservation may be released only if the runtime proves that dispatch never occurred. Dispatched, acknowledged, and uncertain claims remain exercised. A retry is permitted only under the same claim and effect binding; if the sink does not honor idempotency, the runtime must reconcile or request fresh human authority rather than manufacture a new claim.

## 5. Operational semantics

The rules below specify the security-relevant conditions. Ordinary local computation changes only \(q_b\), \(K_b\), or \(S_b\) and is omitted.

### 5.1 Issue and attenuate

`Issue` creates a fresh root grant and allocation handle owned by a live branch. Only a trusted issuer may perform this transition.

`Attenuate` creates \(h'\) from \(h\) only if

\[
\mathsf{Beh}(h')\subseteq\mathsf{Beh}(h),\qquad
t_{h'}\subseteq t_h,\qquad
d_{h'}<d_h.
\]

A checkable sufficient condition is that attenuation introduces no new authority events, narrows \(\lambda\), may add causality or conflict but never remove an inherited constraint, and may strengthen but not erase obligations. Independently consumable authority-event ownership is transferred to \(h'\), never copied. A derived exercise is recorded along the entire allocation ancestry.

### 5.2 Stage, reserve, dispatch, and acknowledge

`Stage` adds a proposed effect to \(S_b\). It creates no durable effect and consumes no authority.

`Reserve` for staged effect \(e\) through handle \(h\) succeeds only if:

1. branch \((b,\eta_b)\) is live and owns \(h\), or holds a contender view authorized by a live choice coordinator;
2. every allocation ancestor is live and unrevoked;
3. there is an authority event \(u\) in the handle slice such that \(\lambda_h(u,e,w,H)\) holds;
4. the witness is fresh, causally prior, effect-bound, and eligible if the scope requires those properties; and
5. adding \(u\) to the branch's tentative reservation preserves Equation (1) for every admissible durable frontier and every allocation ancestor.

The transition atomically appends a branch-conditional reserved claim to \(L\) before any external dispatch. Conflicting branches may reserve against the same capacity; compatible branches are jointly charged.

`Dispatch` first verifies that the effect is eligible to become durable under the current branch-resolution contract, moves its authority event from the conditional reservation into \(X_g\), appends the obligations \(\omega_g(u,e)\), and durably marks the claim dispatched. It then sends the effect carrying the claim identifier and effect digest. `Acknowledge` records the external receipt. If execution crashes between these steps, recovery yields an uncertain, still-exercised claim.

An issue-time effect performs this global charge at issue, not at later branch selection. A commit-gated effect may stay conditional only inside the trusted staging boundary.

This protocol enforces authorization conservation, not magical exactly-once delivery. It deliberately chooses a possible lost opportunity over a duplicated irreversible effect.

### 5.3 Checkpoint

`Checkpoint(b)` stores

\[
C(k)=\langle q_b,K_b,S_b,O_b,\eta_b,\mathsf{frontier}(H),\mathsf{topology\_view}(\mathcal F)\rangle.
\]

The history frontier and topology view are audit metadata, not commands to roll back the current topology. The checkpoint excludes mutable copies of \(L\), \(D\), and \(\mathcal F\). References in the snapshot are revalidated against the current ledger and an explicit restore mode.

### 5.4 Restore dichotomy

`RestoreReplace(k,b)` is an atomic lineage operation:

1. quiesce and tombstone the replaced live branch and the descendants being replaced;
2. create a fresh branch \(b'\) with a fresh epoch;
3. reconstruct \(q,K,S,O\) from \(C(k)\);
4. transfer only authority handles that are still owned, unspent, unrevoked, and eligible under current \(L\); and
5. retain all durable claims, effects, revocations, obligations, and uncertain outcomes that occurred after \(k\).

Old descendants cannot race the replacement because their epochs no longer pass `Reserve`. The restored continuation conflicts with the disabled continuation. Restoring a checkpoint is therefore a new history event, not time travel for authority.

`RestoreFork(k,b)` leaves the old continuation commit-eligible. It is not rollback in the authority semantics: it is a fork. The old and new continuations are compatible unless the runtime installs an enforceable choose-one resolution contract. Their reservations must therefore be jointly accounted under Equation (1).

The runtime may classify restore as choice only after the old continuation has irreversibly lost commit eligibility. A UI label such as “rewind” or “retry” is not evidence of mutual exclusion.

### 5.5 Speculative fork

`ForkSpec(b,n)` creates mutually exclusive alternative branches intended for best-of-\(n\), search, or rollback exploration.

- The branch-resolution contract adds pairwise conflict among the children: no admissible durable frontier contains more than one.
- Each child may compute locally, stage commit-gated effects, and hold tentative reservations satisfying Equation (1).
- Because the children conflict, their tentative charges combine by maximum rather than sum in the scalar instance.
- `Select(group,b_i)` tombstones the losing branch epochs, cancels their undispatched reservations, and makes the selected child's staged effects eligible for dispatch.

Persistent read authority may be available to every child, subject to the same current revocation epoch and confidentiality policy. Consumable or one-shot authority is not cloned.

An escrow with offers is one correct implementation of this rule, but it is not the abstract semantics: the essential fact is conflict in \(\mathcal F\). Topology-conditional reservation gives every candidate a guarantee that it can commit if selected, while avoiding both unsafe cloning and premature guessing about which branch will need a scarce capability.

Issue-time or compensable effects from speculative children move their events into \(X_g\) immediately and therefore accumulate globally even when the branches conflict. Speculation never makes already-observed effects mutually exclusive.

### 5.6 Parallel fork and delegation

`ForkParallel(b,S_0,S_1,\ldots,S_n)` is used when children may all create durable effects. It requires a disjoint, valid decomposition of the parent's residual authority-event slice

\[
S_0\odot S_1\odot\cdots\odot S_n
\preceq \mathsf{remaining}(h).
\]

The topology adds a frontier containing all parallel children, so their tentative reservations must compose. The parent retains \(S_0\); child \(i\) receives a fresh attenuated handle carrying \(S_i\). Each child scope is no wider than the parent scope. `Delegate` is the same event-ownership transfer with an additional principal change and strictly smaller delegation depth.

If the programmer cannot decide whether children are alternatives or concurrent effectors, the runtime must default to speculative staging or request an explicit allocation. Treating both modes as ordinary process fork is unsafe.

### 5.7 Revoke

`Revoke(h)` changes the current epoch or status in \(L\). Reservation checks use the ledger's current epoch, not a value restored from local memory. Revocation therefore invalidates all offers and serialized references in current descendants and old checkpoints. Already dispatched or uncertain effects remain in history; revocation is not retroactive erasure.

### 5.8 Abort

`Abort(b)` tombstones the branch epoch and discards reversible state and undispatched staged effects. It may release a reservation only with durable evidence that dispatch never occurred. It cannot erase acknowledged or uncertain effects, consumption, revocation, audit facts, or obligations incurred before abort.

### 5.9 Join

`Join(b_1,b_2)` is defined only when both parents are quiescent and their reversible states have an explicit compatibility relation.

- The proposed join computes the enlarged durable-frontier family induced by retaining both parents' results.
- The join is authorized only if Equation (1) holds under that enlarged family for every root grant and allocation ancestor.
- Knowledge is merged with provenance retained.
- Staged effects are merged only after conflict checking.
- Conflicting tentative reservations that were safe under maximum accounting may now have to be canceled, narrowed, or covered by fresh authority before the parents become jointly durable.
- Unused authority-event slices may be recombined with \(\odot\) only after both parent epochs are tombstoned and neither has a dispatched or uncertain claim using the slice.
- Aliases to the same handle are deduplicated, not counted twice.
- Incurred obligations are accumulated, never intersected away.

The join result cannot obtain a grant, scope, epoch, or capacity that was not live in a parent or explicitly issued by a trusted authority during the join. Thus merge is an authority admission operation, not merely a workspace three-way merge.

## 6. Security definitions

All properties quantify over every scheduler and every finite reachable configuration, not just over one selected agent trajectory.

### 6.1 Durable-frontier authority conservation

Every possible durable execution frontier must embed into the grant's authority structure:

\[
\forall g.\ \forall C\in\mathcal F_\Sigma.\quad
X_g\cup\bigcup_{b\in C}R_{b,g}
\in\mathsf{Conf}(\mathcal A_g).
\]

The concrete effect-to-authority-event mapping is injective within each embedded configuration and satisfies every label predicate. For a one-shot grant this implies that at most one compatible claim may cross the durable dispatch boundary, regardless of request identifiers, restore count, branch count, or delegation depth. Conflicting, not-yet-durable alternatives may tentatively name the same event.

### 6.2 Topology integrity

The runtime may enlarge \(\mathcal F\) only through a checked transition that re-establishes durable-frontier conservation. In particular, it cannot declare branches mutually exclusive to admit overlapping reservations and later retain or merge them as compatible without canceling reservations or obtaining additional authority.

### 6.3 No authority resurrection

If grant or handle \(h\) is fully consumed or revoked at durable event \(x\), no later event \(y\) with \(x\prec_H y\) may reserve a fresh claim through \(h\), including an event in a branch restored from a checkpoint preceding \(x\).

### 6.4 Lineage confinement

Every claim has one live branch epoch, one authority-event mapping, and one allocation path to a trusted root grant. Its label predicate implies every ancestor predicate, and exercising it updates every ancestor view. No fork, restore, delegation, or join transition creates an allocation path without a corresponding transfer, contender view, or topology event in \(L\).

### 6.5 Revocation closure

After revocation, all current and future descendants using the revoked allocation epoch fail reservation. This includes descendants created by later restoring an older snapshot.

### 6.6 Abort containment

Aborting a branch may reduce reversible state and available authority. It cannot reduce the durable set of dispatched or uncertain effects, consumed authority, revocations, or incurred obligations.

### 6.7 Join non-amplification

If \(b=\mathsf{Join}(b_1,b_2)\), the enlarged durable-frontier family still embeds in every \(\mathcal A_g\). Joining two conflicting reservations for the same authority event does not turn them into two exercises; the join must drop one, acquire another event, or fail. Outstanding obligations from both inputs remain outstanding.

### 6.8 Commit attribution

Every durable dispatch is associated with exactly one prior claim whose authority event, effect digest, branch epoch, and current grant epoch match the dispatch. Endpoint success without such a claim is not an authorized completion.

## 7. Proposed theorem program

None of the following should appear as proved in a paper until a proof artifact exists.

### Theorem 1: topology-sensitive conservation is inductive

**Statement.** Starting from a well-formed ledger, every transition in Section 5 preserves global authority conservation.

**Proof skeleton.** Induct over the transition relation. Local steps, checkpoint, acknowledge, revoke, and provenance-only state changes leave the embedding unchanged. `Reserve` checks configuration validity for every frontier it affects. A speculative fork refines frontiers into conflicting alternatives; a parallel fork adds co-durable frontiers only after a valid separation. Selection removes losing alternatives before moving the winner's exercised events into \(X_g\). Replacing restore disables the old continuation; fork-like restore adds compatible frontiers and rechecks them. Join explicitly checks the enlarged frontier family. Issue-time dispatch moves an event into \(X_g\), which appears in every frontier. The mechanized proof must include ancestor allocation views, topology updates, and uncertain dispatches.

### Corollary 1.1: no double spend across restore

For a one-event grant, no schedule of checkpoint, fork, crash, restore, delegation, join, and retry produces two compatible durable dispatches mapped to that event. A dispatched effect from a losing branch is already in \(X_g\) and is not erased by selection.

### Theorem 2: safe speculative sharing characterization

**Statement.** Consider a one-shot authority event \(u\) and a set of branches \(S\) whose commit-gated effects all tentatively reserve \(u\). Sharing is safe exactly when no admissible durable frontier contains two members of \(S\), and the staging boundary prevents any member from exercising \(u\) before branch resolution.

**Proof sketch.** Sufficiency follows because every frontier contains at most one copy of \(u\), so its embedded configuration is injective. For necessity, if some frontier contains two reserving branches, selecting that frontier requires two concrete effects to map to one unique authority event. If either effect can escape before resolution, both appear globally even if the branches later conflict. The general form replaces “one event” with validity of the union in \(\mathsf{Conf}(\mathcal A_g)\).

### Theorem 3: safe merge criterion

**Statement.** A join that retains effects or reservations from parent support \(J\) is authority-safe if and only if the enlarged family \(\mathcal F'\) induced by the join satisfies Equation (1) for every grant, all joined claims have live epochs and valid labels, and the join preserves the union of incurred obligations.

**Proof sketch.** Sufficiency is immediate from the definition of conservation and obligation persistence. For necessity, any invalid authority configuration in a new frontier is a realizable jointly durable history that violates the grant; a stale epoch is resurrection; and a missing obligation is an abort-through-merge. For finite structures this is a decidable admission test. Complexity for symbolic or recursive structures remains open.

### Theorem 4: restore dichotomy

**Statement.** Restoring a checkpoint may use additive choice accounting only if every old continuation excluded from the new branch's frontiers has irreversibly lost commit eligibility. Otherwise the restore is authority-equivalent to a parallel fork and must use multiplicative accounting.

**Proof sketch.** If the old continuation remains eligible, a schedule exists in which it and the restored continuation both reach durable effects, so a frontier containing both must be admitted. Conversely, tombstoning the old epochs and fencing their dispatches makes the continuations conflicting; already dispatched effects remain in \(X_g\).

### Theorem 5: a topology-oblivious monitor cannot be sound and maximally permissive

**Statement.** A monitor that observes identical branch-local checkpoint state but not whether sibling continuations conflict or are compatible cannot both (a) reject every authority-amplifying schedule and (b) admit every safe choose-one speculative execution.

**Proof sketch.** Construct two executions with identical child-local states and a one-shot event. In the first, a trusted selector makes the children mutually exclusive; both may safely hold tentative reservations. In the second, both children may commit and must be separately accounted. A topology-oblivious monitor makes the same allocation decision in both. Sharing is unsafe in the second; unconditional splitting or choosing one child rejects a valid late-bound outcome in the first. A topology signal or equivalent coordination is therefore necessary for sound maximal permissiveness.

This is the lead impossibility result. It distinguishes the proposal from ordinary “keep a counter outside the snapshot” defenses.

### Theorem 6: late-bound speculation strictly dominates early partition

**Statement.** There is a two-branch task with one consumable authority event in which cloning is unsafe, every irrevocable fork-time partition loses a valid execution for some later observation, and topology-conditional reservation admits every valid selected execution while preserving conservation.

**Witness task.** The environment reveals after fork whether branch \(b_0\) or \(b_1\) produced the valid solution. Exactly that branch should use a one-shot publication event. At fork time the runtime cannot know the result. Giving the event to both as ordinary ownership permits two publications; giving it to only one strands authority when the other wins; conflicting tentative reservations let either candidate commit after selection.

### Theorem 7: rollback-local enforcement is impossible

**Statement.** Consider a runtime where a checkpoint restores every state component consulted by authorization, authorization depends only on that restorable state and the request, a protected effect may persist outside the snapshot, and a capability permits one such effect but not two. No such runtime can enforce the one-effect bound under arbitrary restore.

**Proof sketch.** Checkpoint a state containing the unused event, exercise a durable effect, restore, and exercise a freshly synthesized in-scope effect. The second authorization view is indistinguishable from the first while the first effect remains. Therefore a sound implementation needs non-restorable authority state, a trusted staging boundary, sink-side stable idempotency, or some combination. This result is foundational but not novel by itself.

### Theorem 8: delegation and parallel composition preserve subtree bounds

**Statement.** If each delegation or parallel fork transfers a valid authority-event slice and every descendant exercise is reflected through its allocation ancestry, then every admissible aggregate history of a descendant subtree embeds into the ancestor's event structure.

**Proof sketch.** Structural induction over the allocation tree using the partial composition \(\odot\) and behavioral inclusion of attenuated structures.

### Theorem 9: revocation closes over historical snapshots

**Statement.** If every reservation validates the current ledger epoch and restore never rolls back \(L\), then revoking handle epoch \(\nu\) prevents every later descendant, including descendants reconstructed from checkpoints containing \(\nu\), from reserving through that epoch.

**Proof sketch.** Epoch validity is a durable monotone predicate. Restore reproduces only a stale serialized reference, not the old ledger epoch.

### Proposed Theorem 10: counterfactual least authority for finite adaptive plans

For the finite plan language

\[
P::=\mathsf{stop}\mid e;P\mid P\mathbin{\Box}Q\mid P\parallel Q,
\]

compile sequence to causality, choice to conflict, and parallel composition to disjoint non-conflicting events. The target result is that the compiled authority structure admits exactly the plan's valid resolved effect histories and is minimal under behavioral inclusion among structures that do so. This would connect the lifecycle semantics back to least privilege without reverting to the current paper's natural-language intent compiler. Data-dependent recursion and synthesis from natural language remain out of scope for the first proof.

### Optional theorem: refinement to a reference monitor

An implementation with atomic ledger compare-and-swap and write-ahead dispatch should refine the abstract `Reserve`/`Dispatch` machine with respect to conservation and no resurrection. This is useful only after the abstract semantics is stable; it should not replace the semantic contribution with implementation detail.

## 8. Minimal counterexamples the model must generate

Each example should be executable against a naive snapshot semantics and rejected or contained by the proposed semantics.

1. **Fresh-ID replay:** checkpoint before a payment, pay once, restore, re-plan a semantically equivalent payment with a new request ID, and pay again.
2. **Authority resurrection:** checkpoint after receiving one-use approval, consume it, restore, and use it for a second in-scope mutation.
3. **Parallel budget cloning:** fork two children from a parent with a ten-dollar budget; each spends ten dollars.
4. **Post-checkpoint revocation:** checkpoint a valid grant, revoke it, restore the checkpoint, and attempt the old action.
5. **Abort after lost acknowledgement:** dispatch a message, lose the response, abort, restore, and send again under a fresh claim.
6. **Delegation laundering:** parent transfers its entire unit to a child but retains a checkpoint that appears to contain the unit.
7. **Join duplication:** fork or restore two branches holding the same serialized handle and union their capability lists at merge.
8. **Obligation loss:** a branch performs an irreversible effect that incurs an audit or notification obligation, then aborts before recording it locally.
9. **Safe late binding:** two speculative branches both need a possible one-shot publication right; the valid branch is learned only after computation.
10. **Restore with a live original:** a UI calls an operation “restore,” but the pre-restore worker remains able to commit; additive accounting falsely treats the two continuations as alternatives.
11. **Choice-to-merge amplification:** two branches safely reserve the same event while conflicting, then a merge retains both staged effects without rechecking the enlarged durable frontier.
12. **Losing-branch disclosure:** two speculative branches query different remote services before selection; aborting the loser cannot undo the disclosed query or secret read, so both issue-time effects consume authority.
13. **Exclusive protocol violation:** a grant authorizes “pay” or “dispute” through conflicting authority events; individually valid branches commit both and their aggregate history is invalid.

The counterexamples should be derived from the semantics rather than assembled only as prompt attacks. The model should enumerate short violating schedules for deliberately weakened rules.

## 9. Why agents are a first-class instance

The formal problem is broader than LLM agents, and the paper should say so. Its agent-specific force comes from the conjunction below:

- **semantic retry:** after restore, a model may synthesize a different request for the same intended effect, defeating byte-identical replay assumptions;
- **adaptive authority demand:** the operation, target, and budget needed by a branch may be discovered only after tool observations;
- **cheap branching:** best-of-\(N\), tree search, rollout generation, subagents, and copy-on-write sandboxes make branch fan-out routine rather than exceptional;
- **heterogeneous state:** model context, memory, files, processes, credentials, remote services, approvals, and human interactions do not share one rollback domain;
- **delegated execution:** children may act concurrently rather than merely compute pure values;
- **semantic merge:** agents routinely combine natural-language conclusions from multiple branches, so join must preserve provenance and cannot treat capability sets as ordinary data; and
- **long-lived authority:** approvals or standing delegation may outlive a single prompt while remaining revocable and bounded.

The contribution should therefore be phrased as a semantic foundation for forkable, adaptive agents, not as the claim that ordinary workspaces never had external resources.

## 10. Relationship to the current AgentCap paper

The two models compose, but they should remain distinct papers unless later evidence proves a single clean theorem story.

| Question | Current IntentCap | Proposed model |
|---|---|---|
| Main problem | Which context source may contribute each authority-bearing decision field? | How is already-issued authority conserved over branching and revisable execution? |
| Unit | task-scoped proof-carrying lease | authority event structure plus an embedding of possible durable branch frontiers |
| Main adversary | untrusted context influencing tool, sink, argument, policy, or delegation decisions | fork, restore, crash, retry, delegation, and join duplicating or reviving authority |
| State model | serialized checker state for a run | reconstructable branch state plus non-restorable ledger and durable effect history |
| Main property | field ownership, monotonic narrowing, provenance-aware checking | every jointly durable descendant set is a valid authority configuration |
| Natural theorem | accepted decisions have valid source proofs | topology-sensitive conservation plus necessary-and-sufficient fork/merge admission |

Composition is simple: IntentCap may be one trusted issuer of a scoped root grant \(g\). The new model governs the lifecycle of that grant after issuance. Source ownership is not needed to prove conservation, and conservation does not prove source correctness. Keeping this boundary prevents the formal paper from inheriting the current paper's crowded intent/provenance novelty claim.

## 11. Closest-work pressure and preliminary differentiation

This is a preliminary map, not a novelty verdict. Full-text claim comparison is still required.

| Work | Occupied claim | Proposed remaining delta |
|---|---|---|
| [Consumable Credentials](https://www.cs.cmu.edu/~fp/papers/ndss07.pdf) | Linear access-control credentials, globally bounded use, an online ratifier, and atomic consumption. It explicitly observes that global consumption cannot be enforced by local proof checking. | Occupies one-shot authority plus global ledger. The remaining question is conditional sharing indexed by branch compatibility and safe topology change. |
| [Capstone](https://www.usenix.org/system/files/usenixsecurity23-yu-jason.pdf) | Alias-free linear capabilities, move rather than copy, split/limited merge, and hierarchical revocable delegation. | Occupies linear capability transfer and revocation. It does not model mutually exclusive speculative futures, checkpoints, or durable external histories. |
| [DisLog](https://iris-project.org/pdfs/2024-popl-dislog.pdf) and separation/resource logics | Task trees, computation graphs, fork/join reasoning, and authoritative resource algebras. | Mathematical substrate, not a novelty baseline to rename. The proposed result must concern authority embeddings and dynamic commit compatibility. |
| [Memoir](https://www.microsoft.com/en-us/research/publication/memoir-practical-state-continuity-for-protected-modules/), [ROTE](https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/matetic), and [LCM](https://arxiv.org/abs/1701.00981) | State continuity, rollback/clone protection, monotone history, and fork detection or fork-linearizability. | Occupy anti-rollback and clone detection. They generally prevent or isolate forks rather than authorize intentional choice, concurrency, and later join. |
| [ACRFence](https://arxiv.org/abs/2603.20625) | Identifies semantic action replay and authority resurrection after agent restore; proposes an effect log and replay-or-fork mitigation. | Leaves the authority semantics of explicit fork, live-original restore, conditional sharing, and merge undefined. |
| [Fork, Explore, Commit](https://arxiv.org/abs/2602.08199) and [Atomix](https://arxiv.org/abs/2602.14849) | Branch contexts, first-commit-wins or progress-aware transactional effects, abort, and effect gating for agent speculation. | Occupy much of branch transaction machinery. The remaining delta is topology-sensitive authority accounting, especially merge and authorization events rather than effects alone. |
| [Ghost Tool Calls](https://arxiv.org/abs/2606.02483) | Shows that calls from losing speculative branches disclose information at issue time and cannot be undone by abort. | Forces the model's issue-time/commit-gated distinction; the distinction itself is not ours to claim. |
| [Cordon](https://arxiv.org/abs/2606.17573) | Task-level semantic transactions bind lineage, reversible local state, staged effects, delegated authority, and audit before commit. | Authority embeddings over a branching history, conditional sharing, restore/merge admission, and characterization results rather than a transaction runtime alone. |
| [DART](https://arxiv.org/abs/2605.23311) | Formalizes when local rollback preserves already committed downstream work. | Bounds the authority available to every branch and restore; complementary to recoverability of dependency boundaries. |
| [Commit-Time Authorization](https://arxiv.org/abs/2607.10487) | Requires a fresh, causally prior, effect-bound, eligible witness at durable commit. | Supplies conditions inside \(\lambda_g\); it does not account the same authority event across compatible descendants. |
| [Agent libOS](https://arxiv.org/abs/2606.03895) | Implements explicit capabilities, hierarchical budgets, process lineage, checkpoint restore/fork/commit, append-only history, and primitive-level enforcement. | Very high novelty pressure. The formal paper must show a property, counterexample class, and semantic distinction not already specified or enforced there, especially escrowed speculative authority and the necessity/permissiveness results. |
| [Iron/Iris resource reasoning](https://iris-project.org/iron/) | Provides resource and obligation reasoning for forked concurrent computations. | Proof machinery. It raises the bar: resource algebra alone is not novel; the operational problem and characterization must carry the contribution. |

The generic story “linear capability plus global ledger across restore” is already occupied. The defensible frontier is narrower but more interesting: authority is admitted against the family of jointly durable descendant sets; additive choice and multiplicative concurrency may change dynamically; and merge or live-original restore must reauthorize that topology change. The most dangerous same-claim combination is Agent libOS + ACRFence + Cordon/Atomix + classic consumable credentials. If full-text comparison finds an equivalent compatibility-indexed invariant or safe-merge characterization, this direction must be reconstructed rather than marketed with narrower wording.

## 12. Mechanization plan

The theory should be developed before a large runtime.

### 12.1 Small executable semantics

Implement the transition system in a proof assistant with finite examples:

- branch and checkpoint identifiers;
- finite authority event structures and valid configurations;
- downward-closed durable-frontier families and topology changes;
- allocation ancestry and branch epochs;
- claim lifecycle;
- speculative and parallel fork;
- replace-restore, revoke, abort, and join.

Lean 4 is a practical starting point for an inductive transition system and machine-checked invariants. Rocq with Iris becomes attractive only if the paper needs higher-order concurrency reasoning beyond the abstract state machine. Choosing Iris solely to make the work appear more formal would add proof burden without scientific value.

### 12.2 Proof order

1. Define finite event structures, their valid configurations, and behavioral inclusion.
2. Define admissible durable frontiers and prove their basic closure properties.
3. Define well-formed ledgers, allocation ancestry, epochs, and effect-event embeddings.
4. Prove per-transition preservation of well-formedness and Equation (1).
5. Prove the safe-sharing characterization and safe-merge criterion.
6. Prove the restore dichotomy and topology-oblivious impossibility.
7. Derive no double spend, delegation confinement, revocation closure, and no resurrection.
8. Formalize the rollback-local impossibility and late-binding separation example.
9. Attempt the finite-plan exactness/minimality theorem.
10. Only then prove refinement of a concrete ledger protocol.

### 12.3 Counterexample oracle

Provide weakened semantics in which one premise at a time is removed:

- ledger included in checkpoint;
- restore preserves the old branch epoch;
- speculative and parallel forks are given the same compatibility topology;
- a topology-changing join skips Equation (1);
- a parallel fork maps compatible reservations to the same authority event;
- delegated exercises do not update ancestor event views;
- abort releases uncertain claims;
- issue-time effects remain conditional until branch selection; and
- join unions serialized handles.

A bounded schedule explorer should automatically find the short traces in Section 8. This is both a debugging tool for the proof and a compact artifact showing why each rule exists.

## 13. Minimal empirical validation

Experiments are supporting evidence, not the main contribution, but omitting them would leave two reviewer objections unanswered: whether real agent runtimes exhibit the modeled operations, and whether the semantics can be enforced without destroying useful branching.

### RQ1: Are the violations real and semantically distinct?

Reproduce a small, fixed matrix on at most two real checkpoint-capable agent frameworks:

- fresh-ID action replay;
- single-use authority resurrection;
- revocation followed by old-checkpoint restore;
- parallel budget cloning;
- replace-restore versus live-original restore;
- choose-one fork followed by a join; and
- losing-branch issue-time disclosure;
- lost acknowledgement followed by retry.

Use real framework checkpoint/restore APIs and local deterministic effect sinks. Ten to twenty carefully controlled schedules are more valuable than a large prompt benchmark.

### RQ2: Does the reference monitor enforce the proved rules?

Replay every bounded counterexample through the implementation and compare:

- naive snapshot-local capability state;
- **clone-all**, which gives every child the parent's local capability view;
- **split-all**, which partitions bounded authority across every fork;
- append-only global consumption without branch compatibility; and
- the full topology-aware event/epoch/uncertain-claim monitor.

The decisive metrics are invalid durable-frontier embeddings and safe executions falsely rejected, not model refusal or endpoint success. Clone-all should be unsafe, split-all should be safe but unnecessarily restrictive, and the topology-aware policy should preserve both conservation and late-bound exploration.

### RQ3: Does late binding preserve useful speculation?

Use a small best-of-\(N\) or tree-search workload where the winning branch is learned after computation and one durable publish capability is available. Measure:

- accepted selected executions;
- unsafe commits;
- authority stranded by early partition;
- ledger operations and latency; and
- staged work discarded at selection.

This experiment directly validates the systems significance of Theorems 2, 5, and 6.

### RQ4: What is the enforcement cost?

Measure checkpoint, fork, restore, reserve, and join latency plus ledger contention under increasing branch fan-out. This may be a microbenchmark. It should establish feasibility, not compete with checkpoint-performance systems such as DeltaBox or Crab.

## 14. Submission-shaped paper plan

A theory-heavy CSF paper could use this structure:

1. **Introduction:** forkable agents make execution possibilities copyable; whether authority may be shared depends on which effects may become durable together. State the topology-oblivious impossibility and late-binding advantage.
2. **Counterexamples and system model:** derive the problem from real checkpoint/restore behavior and distinguish speculative alternatives, parallel children, live-original restore, issue-time effects, and topology-changing merge.
3. **Authority over branching executions:** define authority event structures, admissible durable frontiers, embeddings, allocation ancestry, ledger state, claims, branches, and checkpoints.
4. **Operational semantics:** issue, stage, reserve, dispatch, checkpoint, the two fork modes, replace-restore, revoke, abort, delegate, and join.
5. **Security properties and proofs:** conservation, safe-sharing and safe-merge characterizations, restore dichotomy, topology-oblivious and rollback-local impossibilities, no resurrection, delegation confinement, and late-binding permissiveness.
6. **Mechanization:** trusted assumptions, proof size, executable counterexamples, and refinement boundary.
7. **Reference monitor:** the minimum implementation that corresponds to the semantics.
8. **Validation:** real framework counterexamples, late-binding workload, and microbenchmarks.
9. **Related work:** rollback protection, capability/resource logics, agent checkpointing, semantic transactions, commit-time authorization, and agent runtimes.
10. **Discussion:** external services without idempotency, irreversible effects, persistent read authority, provenance at join, and generality beyond agents.

The paper should lead with the theorem-level position, not with a branded runtime. The system artifact exists to demonstrate that the semantics is implementable.

## 15. Falsifiers and kill criteria

The direction should be stopped or substantially reconstructed if any of the following is true:

1. Closest work already defines authority admission against jointly durable branch sets over restore, speculation, concurrency, and merge, with comparable characterization or impossibility results.
2. The model reduces to a direct instantiation of a standard linear type system without an agent-specific semantic distinction or new theorem.
3. The compatibility-indexed invariant or late-binding theorem becomes a direct corollary of a standard transaction, event-structure, or capability abstraction without an agent lifecycle result.
4. Real checkpoint-capable agent runtimes do not permit the relevant combinations of restore, persistent effect, and branch authority.
5. Enforcing the semantics requires serializing all speculative computation rather than only durable claims.
6. Join can be removed without changing any claim, counterexample, or proof; if so, it should be cut rather than retained as decorative breadth.
7. The paper cannot define the exact guarantee under lost acknowledgement without assuming impossible atomicity with arbitrary remote services.

## 16. Decisions still needed

1. **Authority language:** start with finite labeled event structures; treat scalar budgets as an instance. Add recursion or a more general resource algebra only if a load-bearing theorem requires it.
2. **Speculative effects:** decide whether all irreversible effects must wait for selection or whether some branches may atomically race for shared claims. The former has cleaner semantics; the latter may offer more concurrency but changes the meaning of speculation.
3. **Join scope:** keep authority join in the core; keep provenance-safe knowledge merge as a composition hook to IntentCap unless it yields an independent theorem.
4. **Obligations:** retain only the minimal rule that abort and join cannot erase liabilities from dispatched effects. A full obligation logic is a separate paper unless required by a counterexample.
5. **Proof assistant:** choose Lean for a compact transition-system proof unless existing project expertise strongly favors Rocq/Iris.
6. **Relationship to ACRFence:** use its attacks and framework evidence as motivation, but replace its heuristic mitigation story with the formal execution-wide authority model only after the novelty audit and theorem feasibility gate pass.

## 17. Immediate next actions

1. Read the complete Consumable Credentials, Capstone, DisLog, Memoir/ROTE/LCM, ACRFence, Fork-Explore-Commit, Atomix, Agent libOS, Cordon, DART, Ghost Tool Calls, and Commit-Time Authorization papers and write a name-free closest-claim matrix.
2. Encode a finite event-structure and durable-frontier version of the state machine and automatically recover the counterexamples in Section 8.
3. Prove Equation (1) on paper for every transition; remove any transition whose proof requires an unstated oracle.
4. Mechanize Theorems 1--6 before building a full reference monitor.
5. Reuse the existing `agent-check-restore-safety` repository as the theory project's empirical seed, after reconciling its `main` and Overleaf histories.
6. Keep the current IntentCap paper unchanged until there is explicit evidence that this model should replace, rather than merely compose with, it.
