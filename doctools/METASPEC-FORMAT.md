# The MNX metaspec format

This document describes the two files that define the MNX specification:

* **`mnx-metaspec.json`** — the type system (every object, attribute and
allowed value in MNX), plus metadata for the documentation website.

* **`mnx-examples.json`** — metadata about the example documents and the
MusicXML comparisons.

These two files are the source of truth. Everything in the top-level
`docs/` directory is generated from them, including `docs/mnx-schema.json`.

## Why not just use JSON Schema?

`docs/mnx-schema.json` is a real JSON Schema, generated from
`mnx-metaspec.json`. But JSON Schema alone can't serve as our source of
truth, because it's missing a few features we need:

* **Descriptions of individual allowed values.** JSON Schema's `enum` is a
bare list of values, without a way to document them.

* **A separate display name and URL slug** for each object.

* **Some shortcuts to avoid redundancy**, like MNX's global attributes
(`id`, `_c`, `_x`) that are available on nearly every object. Technically
this is doable in JSON Schema, but in a verbose way.

The metaspec also encodes some things at a higher level of abstraction
than JSON Schema would, purely for the convenience of whoever's editing
it — see "Attributes" below, where an array of notes is written
`{"items": ["note"]}` rather than as a separate named type.

## Conventions used in both files

**Prose is written as an array of lines.** JSON has no multi-line string
syntax, so any field holding human-readable text is a list of strings that
get joined with newlines:

```json
"description": [
    "<p>The first paragraph.</p>",
    "",
    "<p>The second paragraph.</p>"
]
```

An empty array means "no text". Prose fields may contain raw HTML, which is
passed through to the generated pages unescaped.

**Objects are referenced by slug.** Slugs are the identifiers used
throughout both files, and they determine documentation URLs. For example,
the object with slug `note-value` is documented at
`/mnx-reference/objects/note-value/`.

## `mnx-metaspec.json`

The top level looks like this:

```json
{
    "version": 28,
    "format": {"name": "MNX", "slug": "mnx"},
    "site": { ... },
    "objects": { ... },
    "pageCollections": [ ... ]
}
```

* `version` — the MNX version, which appears in the generated JSON
Schema's `$id`. A number or a string.
* `format.name`, `format.slug` — used in page titles and URLs.

### `site`

General configuration for the generated website:

```json
"site": {
    "siteName": "MNX specification",
    "formatName": "MNX",
    "sidebarHtml": [
        "<ul>",
        "<li><a href=\"/\">Home</a></li>",
        "</ul>"
    ]
}
```

`sidebarHtml` is raw HTML for the left sidebar of every page. Its links are
rewritten to be relative when the static site is generated, so write them
as absolute paths.

### `objects`

A dictionary mapping slug to object definition. This is the bulk of the
file and the bulk of the specification.

Every definition has a `kind`, which determines which other fields apply:

| `kind` | Represents | Type-specific fields |
| --- | --- | --- |
| `dict` | A JSON object with known keys | `properties` |
| `string` | A JSON string | `values`, `pattern` |
| `integer` | A JSON number with no fractional part (generated as `integer`) | `values` |
| `float` | A JSON number that may have a fractional part (generated as `number`) | `values` |
| `boolean` | A JSON boolean | — |
| `array` | A JSON array | `items` |
| `keyedDict` | A JSON object with user-defined keys | `values` |

Fields common to all kinds:

* `kind` (required) — one of the above.
* `title` — the human-readable name shown in the docs. Defaults to the
slug. Use this when the display name differs from the slug, e.g. slug
`key` with title `key signature`.
* `description` — prose describing the object, shown on its docs page.
* `role` — see "Special objects" below.
* `extraJSONSchema` — see "Extra JSON Schema data" below.

Objects of kind `array` and `keyedDict` don't get their own documentation
page; they're described inline wherever they're used.

### Attributes

An object of kind `dict` lists its attributes in `properties`, keyed by the
attribute name as it appears in an MNX document:

```json
"event": {
    "kind": "dict",
    "description": ["<p>The event object represents…</p>"],
    "properties": {
        "duration": {
            "type": "note-value",
            "required": true,
            "description": ["The duration of this event."]
        },
        "notes": { "items": ["note"] },
        "type": {
            "const": "event",
            "description": ["Optional. Used to disambiguate…"]
        }
    }
}
```

Each attribute gives its type in exactly one of three ways:

* **`type`** — the slug of another object. The common case.

* **`items`** — a list of slugs, meaning "an array of these". Write
`{"items": ["note"]}` for an array of notes. If the list has more than one
entry, the array may hold any of those types, and they must be
distinguishable by their attribute names alone (see "Ambiguity" below).
This saves defining a separate named type for every array in the format.

* **`const`** — a literal string that this attribute must equal. Used for
the `type` discriminator attributes.

Other attribute fields:

* `required` — `true` if the attribute must be present. Omit for optional
attributes.
* `description` — prose describing this attribute, shown in the object's
attribute table.
* `extraJSONSchema` — see "Extra JSON Schema data" below.

Note that descriptions live on the *attribute*, not on the type it points
at. The same attribute name means different things in different objects —
`staff` has several different descriptions across the format — so the prose
can't be attached to the shared type.

### Global attributes

Most objects of kind `dict` also accept the global attributes, which are
defined once (see "Special objects"). To exempt an object, set:

```json
"globalAttributes": false
```

This is rare; only a handful of objects do it.

### Other properties

A `dict` object only accepts the attributes it defines (plus the global
attributes, if it uses them); the generated JSON Schema rejects anything
else. To accept arbitrary other properties, set:

```json
"allowOtherProperties": true
```

This is for objects whose contents are deliberately open-ended, such as
`vendor-dict`. The global attributes object (see "Special objects") is
always left open, as it's only ever combined into other objects.

### Allowed values

Objects of kind `string`, `integer` and `float` may enumerate their allowed
values in `values`, mapping each value to its description:

```json
"stem-direction": {
    "kind": "string",
    "values": {
        "up": ["The stem points up."],
        "down": ["The stem points down."]
    }
}
```

Use an empty array for a value that needs no description. For the numeric
kinds, the keys are still JSON strings (JSON keys are required to be) but
must be parseable as numbers: as integers for `kind: "integer"`, and as
integers or decimals for `kind: "float"`. For `kind: "string"`, the empty
string is a legal value.

Values are listed in the generated JSON Schema in the order written here,
so keep them in a sensible order.

Objects of kind `string` may instead (or additionally) constrain their
value with `pattern`, a regular expression. Include `^` and `$`:

```json
"id": { "kind": "string", "pattern": "^[\\x21-\\x7E]{1,256}$" }
```

### Arrays and user-keyed dictionaries

Most arrays are written inline with `items` on the attribute that uses
them. Define a *named* array — kind `array`, with its own `items` — only
when the array is used by more than one attribute, or needs its own
description:

```json
"sequence-content": {
    "kind": "array",
    "items": ["event", "grace", "tuplet", "space", "multi-note-tremolo"]
},
"fraction": {
    "kind": "array",
    "items": ["integer-unsigned"],
    "extraJSONSchema": {"minItems": 2, "maxItems": 2},
    "description": ["<p>A two-element array representing a fraction…</p>"]
}
```

An object of kind `keyedDict` is a JSON object whose keys are chosen by the
document author rather than by the specification. Its `values` field names
the type of every value:

```json
"event-lyric-lines": { "kind": "keyedDict", "values": "event-lyric-line" }
```

### Extra JSON Schema data

Any object can define an `extraJSONSchema` dictionary, whose contents will
be passed through verbatim into that object's JSON Schema definition.

```json
"positive-integer": {
    "title": "positive integer",
    "kind": "integer",
    "extraJSONSchema": {"minimum": 1}
}
```

An individual attribute can define one too, in which case it applies to
that one use of the type rather than to every use of it:

```json
"multi-note-tremolo": {
    "kind": "dict",
    "properties": {
        "beams": {
            "type": "positive-integer",
            "required": true,
            "extraJSONSchema": {"maximum": 8},
            "description": ["The number of beams to use…"]
        }
    }
}
```

This is a simple hook for adding extra JSON Schema validation that the
metaspec system doesn't natively support.

The contents are merged in after the generated keywords, so a key that the
generator produces itself — `type`, `enum`, `pattern`, `$ref` and so on —
would override it. `validate_metaspec` warns when that happens.

Note that `extraJSONSchema` affects only the generated JSON Schema, not the
documentation pages, so anything encoded here should also be stated in the
`description` of the object or attribute.

### Special objects

Two objects have a `role`, which marks their structural purpose:

```json
"root": {
    "role": "root",
    "title": "__root__",
    "kind": "dict",
    "properties": { ... }
},
"global-attrs": {
    "role": "globalAttributes",
    "title": "__globalattrs__",
    "kind": "dict",
    "globalAttributes": false,
    "properties": { ... }
}
```

* `role: "root"` — describes a whole MNX document. Exactly one object must
have this.
* `role: "globalAttributes"` — its properties are the attributes available
on every `dict` object that doesn't set `globalAttributes: false`. Exactly
one object must have this.

### Ambiguity

When an attribute permits several types — `{"items": ["event", "grace",
"tuplet"]}` — the documentation generator has to work out which type
describes each value it finds in an example document. It does this by
looking at the value's keys: a type matches if every key in the value is
one of that type's attributes.

This means the permitted types of a single array must stay distinguishable
by their attribute names. If they don't, `validate_metaspec` will report
the example document it couldn't resolve. Adding a `const` discriminator
attribute (conventionally named `type`) is the usual fix.

### `pageCollections`

Hand-written prose pages, grouped into collections. Each collection gets an
index page listing its pages:

```json
"pageCollections": [
    {
        "title": "Infrastructure",
        "url": "/infrastructure/",
        "pages": [
            {
                "title": "Notational concepts",
                "url": "/infrastructure/notational-concepts/",
                "contentFile": "notational-concepts.html"
            }
        ]
    }
]
```

* `url` — must start and end with a slash.
* `contentFile` — a file in `doctools/content/`, containing the page body
as raw HTML (no `<html>` wrapper; it's inserted into the site template).
Pages appear in the order listed.

## `mnx-examples.json`

Metadata about the example documents. The examples themselves stay as
individual files on disk, under `doctools/media/`.

```json
{
    "comparisonFormats": [
        { "name": "MusicXML", "slug": "musicxml" }
    ],
    "examples": [
        {
            "slug": "hello-world",
            "name": "“Hello world”",
            "blurb": ["This basic MNX document contains a single middle C…"],
            "documentPath": "examples/json/hello-world.json",
            "imagePath": "examples/hello-world.png",
            "featured": true,
            "comparisons": [
                {
                    "format": "musicxml",
                    "position": 1,
                    "documentPath": "examples/musicxml/hello-world.xml",
                    "preamble": []
                }
            ]
        }
    ]
}
```

* `slug` — determines the URL, `/mnx-reference/examples/<slug>/`.
* `name` — the display name.
* `blurb` — prose shown above the example.
* `documentPath` — the MNX document, relative to `doctools/media/`.
* `imagePath` — a rendered image of the notation, relative to
`doctools/media/`. Optional.
* `featured` — `true` to list the example on the reference homepage.
* `comparisons` — optional side-by-side comparisons with another format,
shown at `/comparisons/<format slug>/`.
  * `format` — a slug from `comparisonFormats`.
  * `position` — sort order within the comparison page.
  * `documentPath` — the other format's document, relative to
  `doctools/media/`.
  * `preamble` — prose shown above the comparison. Each line becomes its
  own paragraph.

Examples are listed alphabetically by name in the generated docs
regardless of their order here, so the order in this file doesn't matter.

Which objects each example uses is worked out by reading the example
documents at build time, so there's nothing to maintain by hand. Adding an
example automatically adds it to the "Examples" section of every relevant
object page.

## Editing workflow

```
# 1. Edit mnx-metaspec.json, mnx-examples.json, or content/*.html.

# 2. Check your changes are structurally sound.
python manage.py validate_metaspec

# 3. Check every example still validates against the generated schema.
python manage.py validate_json

# 4. Preview in a browser at http://127.0.0.1:8000/.
python manage.py runserver

# 5. Regenerate the static site.
python manage.py makesite ../docs/
```
