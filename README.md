# Arches ID Generator

An Arches application that provides a widget for assigning sequential, monotonic IDs at tile save time. IDs come from a server-side counter, so concurrent users cannot end up with duplicates.

## What it does

When a resource tile is saved, a `pre_save` signal looks at every node in that tile's nodegroup that uses the `id-generator-widget`. For any such node whose value is empty, it:

1. Reads the widget's `sequence_key` and `template` config.
2. Atomically increments the counter for that key (`SELECT … FOR UPDATE`, then `+1`).
3. Renders the new value through the template.
4. Stores it on the tile (in the i18n shape required by the `string` datatype).

If the tile already has a value for the node, the signal leaves it alone, so re-saving an existing resource doesn't burn through new IDs.

## Installation

1. Add the app to your Arches project's requirements / install it:

   ```bash
   pip install -e arches_apps/arches-id-generator
   ```

2. Add it to `INSTALLED_APPS` in your project settings:

   ```python
   INSTALLED_APPS = [
       # ...
       "arches_id_generator",
   ]
   ```

3. Run migrations to create the `id_generator_sequence` table:

   ```bash
   python manage.py migrate arches_id_generator
   ```

4. Register the widget so it appears in the Graph Designer:

   ```bash
   python manage.py widget register --source arches_apps/arches-id-generator/arches_id_generator/widgets/id-generator-widget.json
   ```

   (Use `--overwrite` if you're updating after a `defaultconfig` change.)

5. Build the frontend so the widget JS/template are bundled into Arches' static assets:

   ```bash
   yarn build_development   # or your project's equivalent
   ```

## Using the widget

In the Graph Designer:

1. Open a `string`-datatype node.
2. Choose **id-generator-widget** as its widget.
3. Configure:
   - **Sequence Key** — a slug (lowercase letters, digits, hyphens; must start with a letter; max 128 chars). Nodes that share the same key share the same counter, which is useful when you want one running number across multiple resource models.
   - **Template** — the format string (see tokens below).
   - **Placeholder Text** — what users see in the read-only field before the ID is assigned.
4. Save the card. New resources will receive an ID on first save.

The form input is read-only — IDs are server-generated, never user-typed.

## Template tokens

The template is a Python `str.format`-style string. The following tokens are allowed:

| Token | Meaning | Example output |
|---|---|---|
| `{seq}` | The next sequence number, no padding | `42` |
| `{seq:0N}` | The next sequence number, zero-padded to N digits | `{seq:05}` → `00042` |
| `{YYYY}` | Current calendar year, 4 digits | `2026` |
| `{YY}` | Current calendar year, last 2 digits | `26` |
| `{fiscal_yy}` | Fiscal year (April–March), last 2 digits | `26` (for any date 2026-04 through 2027-03) |
| `{fiscal_yy_next}` | Fiscal year + 1, last 2 digits — useful for `25/26` style spans | `27` |

The fiscal year start is **April** (`_FISCAL_YEAR_START_MONTH = 4` in `services/formats.py`); change it there if you need a different fiscal calendar.

Anything outside `{...}` tokens is treated as literal text. Attribute access (`{seq.__class__}`), indexing (`{seq[0]}`), and `!r` / `!s` conversions are all rejected.

### Template examples

| Template | Example output |
|---|---|
| `{seq:05}` | `00042` |
| `MN-{seq:06}` | `MN-000042` |
| `{YYYY}-{seq:04}` | `2026-0042` |
| `{fiscal_yy}/{fiscal_yy_next}-{seq:03}` | `26/27-042` |

## Resetting a sequence

Use the bundled management command instead of editing the database directly. It takes a row-level lock so it's safe to run against a live system.

```bash
# List every sequence and its current counter
python manage.py reset_id_sequence --list

# Reset to 0 — the next ID will be 1
python manage.py reset_id_sequence monument-number

# Skip the counter forward (e.g. to leave a gap, or migrate from another system)
python manage.py reset_id_sequence monument-number --to 5000

# Lower the counter — refused unless --force is passed,
# because it can produce duplicate IDs against existing tiles
python manage.py reset_id_sequence monument-number --to 100 --force
```

Arguments:

- `key` — the `sequence_key` to update. Required unless `--list` is passed.
- `--to N` — set `last_issued` to `N`. The next generated ID will be `N + 1`. Defaults to `0`.
- `--force` — allow lowering the counter below its current value. Without this flag, the command refuses to lower the counter, since the next save would hand out a number an existing resource already has.
- `--list` — print all sequences and exit.

### Safety note

Lowering a counter while resources already exist that use those IDs **will** produce duplicates. The widget does not enforce uniqueness across resources. Reasonable times to lower a counter:

- Fresh / dev / staging environments.
- After deleting all resources that consumed the higher numbers.
- Never on production with live data — raise the counter to skip ahead instead.

## How it fits together

| Piece | Path |
|---|---|
| Widget definition (JSON) | `arches_id_generator/widgets/id-generator-widget.json` |
| Widget Knockout viewmodel | `arches_id_generator/media/js/views/components/widgets/id-generator-widget.js` |
| Widget template | `arches_id_generator/templates/views/components/widgets/id-generator-widget.htm` |
| Counter model | `arches_id_generator/models.py` (`IdSequence`, table `id_generator_sequence`) |
| Generator service | `arches_id_generator/services/generator.py` |
| Template renderer | `arches_id_generator/services/formats.py` |
| Tile pre_save signal | `arches_id_generator/signals.py` |
| Reset command | `arches_id_generator/management/commands/reset_id_sequence.py` |
| Widget UUID constant | `arches_id_generator/constants.py` |

## Tests

```bash
python -m pytest arches_apps/arches-id-generator/tests
```
