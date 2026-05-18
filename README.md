# Arches ID Generator

An Arches application that assigns server-generated identifiers to resource nodes,
using a template string. IDs can be:

- **Sequential**, drawn from an atomic counter shared by any number of nodes (per scope key).
- **UUID** (uuid4 or time-ordered uuid7).
- **Random** alphanumeric strings or integers (with retry-on-collision against existing values).
- **Composite** — any mix of the above, plus date tokens like fiscal year.

Generation can fire at **tile save** (the default — the ID appears the moment
the user saves the card) or be deferred to **resource lifecycle activation**
(the ID is stamped when the resource transitions to a published/active state,
not before).

The backend mirrors the `ConceptIdentifierCounter` pattern from arches-lingo,
so both packages share the same allocation semantics.

## How it works

The package ships:

- An `IdSequence` model and atomic allocator (`SELECT … FOR UPDATE` + increment).
- A `secrets`-backed generator module for UUIDs and random values.
- A template renderer that resolves `{seq}`, `{uuid}`, `{rand:N}`, date tokens, etc.
- An Arches `BaseFunction` (`IdGeneratorFunction`) that hooks into Arches'
  tile-save and lifecycle-state-change callbacks.
- A small `post_save` signal on `CardXNodeXWidget` that **auto-attaches the
  Function to any graph that uses the widget**, so the widget remains zero-
  config from the user's point of view.

When the widget is configured `generate_on: tile_save` (default), the Function's
`save` callback stamps the ID into the tile before persistence. When configured
`generate_on: resource_activation`, the Function's `on_update_lifecycle_state`
callback fires only when the resource enters a configured activation state
(`active` or `published` by default).

If the tile already has a value (typed by a user or set programmatically),
the generator leaves it alone. This works in both modes — manual overrides
are always honoured.

## Installation

1. Install the app:

   ```bash
   pip install -e arches_apps/arches-id-generator
   ```

2. Add it to `INSTALLED_APPS`:

   ```python
   INSTALLED_APPS = [
       # ...
       "arches_id_generator",
   ]
   ```

3. Wire its URLs (only required if you want the REST seeding API):

   ```python
   # urls.py
   urlpatterns += [path("", include("arches_id_generator.urls"))]
   ```

4. Run migrations to create the sequence table and register the Function:

   ```bash
   python manage.py migrate arches_id_generator
   ```

5. Register the string widget (the **number** widget is registered
   automatically by migration `0003_register_number_widget`):

   ```bash
   python manage.py widget register \
       --source arches_apps/arches-id-generator/arches_id_generator/widgets/id-generator-widget.json
   ```

   (Use `--overwrite` after a `defaultconfig` change. After editing
   `number-id-generator-widget.json`'s `defaultconfig`, re-run the migration
   or `widget register --overwrite` for that file, since the migration is
   idempotent but only runs once.)

6. Build the frontend:

   ```bash
   yarn build_development
   ```

## Configuring the widget

In the Graph Designer:

1. Open a `string`-datatype node.
2. Choose **id-generator-widget** as its widget.
3. Configure:
   - **Sequence Key** — slug (lowercase letters / digits / hyphens, starts with a letter, max 128 chars). Nodes sharing a key share a counter — useful for one running number across multiple resource models.
   - **Template** — see tokens below.
   - **Generate On** — `Tile save` (default) or `Resource activation`.
   - **Placeholder Text** — what users see before the ID is assigned.
   - **Auto-populate** — see [Auto-populate](#auto-populate).
4. Save the card.

For a **number**-datatype node, choose **number-id-generator-widget** instead.
It's the same machinery with a reduced config (no template/padding — a number
stores `42`, not `0042`):

- **Sequence Key**, **Generate On**, **Placeholder Text**, **Auto-populate** —
  as above. A sequence key shared with a string `{seq}` template stays in step.
- **Start Number** — the first value a brand-new sequence issues (e.g. `3000`);
  minimum `1`. Ignored once the sequence has been used.

The form input is always read-only — the value is server-generated.

The first time you save a `CardXNodeXWidget` row for this widget on a graph,
a signal ensures `IdGeneratorFunction` is attached to that graph. No manual
function-binding step required.

Different nodes on the same graph may use **different sequence keys, templates,
and trigger modes** — every binding is processed independently.

## Template tokens

| Token | Meaning | Example output |
|---|---|---|
| `{seq}` | Next sequence number, no padding | `42` |
| `{seq:0N}` | Next sequence number, zero-padded to N digits — `{seq:05}` → `00042` | `00042` |
| `{uuid}` | uuid4 | `3f0c…` |
| `{uuid7}` | Time-ordered uuid7 (falls back to uuid4 without `uuid_extensions`) | `0192c…` |
| `{rand:N}` | Random alphanumeric string of length N (default alphabet excludes `0`, `O`, `1`, `I`, `L`) | `K7Q9XB` |
| `{randint:N}` | Random integer with N digits | `47391` |
| `{YYYY}` / `{YY}` | Calendar year, 4 or 2 digits | `2026` / `26` |
| `{fiscal_yy}` | Fiscal year (April–March by default), 2 digits | `26` (April 2026 through March 2027) |
| `{fiscal_yy_next}` | Fiscal year + 1, 2 digits (for `25/26`-style spans) | `27` |

A template with no tokens is rejected — nothing would be generated.

### Uniqueness

For random/non-deterministic templates (`{rand:N}`, `{randint:N}`), the renderer
wraps the whole template in a retry loop: if the **full rendered ID** already
exists for the node, it rerolls. Templates containing `{seq}`, `{uuid}`, or
`{uuid7}` skip this check — sequence allocation and UUIDs are already
collision-free, and running the check on them would be wasted work (and prone
to false positives against fragments that appear elsewhere in the column).

If retries are exhausted (default 10), a `CollisionError` is raised — usually
a sign the random fragment is too short for the volume of data, and the
template should be widened.

### Configuration

| Setting | Default | Purpose |
|---|---|---|
| `ARCHES_ID_GENERATOR_FISCAL_YEAR_START_MONTH` | `4` | Month a fiscal year begins (1–12). |
| `ARCHES_ID_GENERATOR_ACTIVATION_STATE_NAMES` | `["active", "published"]` | Lifecycle state names that trigger `resource_activation` generation. Case-insensitive. |

### Template examples

| Template | Example output |
|---|---|
| `{seq:05}` | `00042` |
| `MN-{seq:06}` | `MN-000042` |
| `{YYYY}-{seq:04}` | `2026-0042` |
| `{fiscal_yy}/{fiscal_yy_next}-{seq:03}` | `26/27-042` |
| `{uuid}` | `3f0c87a4-2eef-4c0e-8c5e-...` |
| `ART-{rand:6}` | `ART-K7Q9XB` |
| `{seq:04}-{rand:4}` | `0042-K7Q9` |

## Generate On modes

### Tile save (default)

When a tile is saved, the Function's `save` callback iterates over every
`CardXNodeXWidget` row for that nodegroup whose widget is the id-generator.
For each binding in `tile_save` mode with an empty value, it renders the
template and stamps the result in.

### Resource activation

The Function's `on_update_lifecycle_state` callback fires when the resource's
lifecycle state changes. If the new state's name is in the configured
activation list (default: `active`, `published`), every binding on the graph
in `resource_activation` mode has its template rendered and stamped into the
relevant tile(s), unless they already have a value.

Drafts that are abandoned therefore never burn an ID, which is the main
reason to choose this mode over tile-save.

## Auto-populate

The widget config has an **Auto-populate** checkbox (orthogonal to the
generate-on choice). When enabled, the Function's `post_save` callback
fabricates the widget's tile the first time *any* card on the resource is
saved — even if the user never opens the card the widget lives on. This is
useful when the SRN card is hidden from data-entry users but the ID still
needs to exist before the resource is referenced elsewhere.

Auto-populate only fabricates tiles for **top-level cardinality-1 nodegroups**.
On unsupported shapes it logs a warning and skips the binding; the widget
continues to work for manual saves of the card.

| Nodegroup shape | Save populate (widget on its own card) | Auto-populate (fabricate tile) |
|---|---|---|
| Top-level, cardinality 1 | ✅ | ✅ |
| Top-level, cardinality n | ✅ on each manual save | ❌ |
| Child nodegroup, cardinality 1 | ✅ | ❌ |
| Child nodegroup, cardinality n | ✅ on each manual save | ❌ |

## REST API

If you've wired `arches_id_generator.urls`, the package exposes:

- `GET /api/id-sequence/<key>` — current state of a sequence.
- `POST /api/id-sequence/<key>` with body `{"start_number": N}` — create or
  seed a sequence. **Refuses to edit a sequence that has already been used**
  (`start_number != next_number`).

Endpoint requires authentication (`LoginRequiredMixin`). Subclass
`IdSequenceView` for stricter permissions.

## Resetting a sequence

```bash
# List every sequence and its current state
python manage.py reset_id_sequence --list

# Set next_number to 1 — the next ID will be 1
python manage.py reset_id_sequence monument-number

# Skip the counter forward
python manage.py reset_id_sequence monument-number --to 5000

# Lower the counter — refused unless --force is passed
python manage.py reset_id_sequence monument-number --to 100 --force
```

Arguments:

- `key` — the `sequence_key` to update. Required unless `--list` is passed.
- `--to N` — set `next_number` to `N`. The next generated ID will be `N`. Defaults to `1`.
- `--force` — allow lowering the counter below its current value.
- `--list` — print all sequences and exit.

### Safety note

Lowering a counter while resources already exist that use those IDs **will**
produce duplicates. Reasonable times to lower a counter:

- Fresh / dev / staging environments.
- After deleting all resources that consumed the higher numbers.
- Never on production with live data — raise the counter to skip ahead instead.

## How it fits together

| Piece | Path |
|---|---|
| Widget definition (JSON) | `arches_id_generator/widgets/id-generator-widget.json` |
| Widget Knockout viewmodel | `arches_id_generator/media/js/views/components/widgets/id-generator-widget.js` |
| Widget template | `arches_id_generator/templates/views/components/widgets/id-generator-widget.htm` |
| Sequence model | `arches_id_generator/models.py` (`IdSequence`, table `id_generator_sequence`) |
| Atomic allocator | `arches_id_generator/utils/allocator.py` |
| Stateless generators (UUID / random) | `arches_id_generator/generators.py` |
| Uniqueness wrapper | `arches_id_generator/utils/uniqueness.py` |
| Template renderer | `arches_id_generator/template.py` |
| Key validation | `arches_id_generator/utils/validation.py` |
| Generator service (validation + render) | `arches_id_generator/services/generator.py` |
| Arches Function | `arches_id_generator/functions/id_generator_function.py` |
| Auto-attach signal | `arches_id_generator/signals.py` |
| REST API | `arches_id_generator/views/api.py`, `arches_id_generator/urls.py` |
| Reset command | `arches_id_generator/management/commands/reset_id_sequence.py` |
| Constants (widget id, function id) | `arches_id_generator/constants.py` |

## Tests

```bash
python -m pytest arches_apps/arches-id-generator/tests
```
