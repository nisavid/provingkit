# Pull-request body with literal regions

Field: Pull-request body.

Create a body with a one-paragraph `## Summary`, then a `## Evidence` section that carries the following supplied regions without changing their internal bytes or line structure: a fenced shell block, a GFM table, a raw HTML preformatted block, and a machine-owned control marker. Add one closing prose paragraph after them explaining that the values are fixture evidence rather than a deployment claim.

Supplied fenced block:

````text
```sh
printf '%s\n' alpha
printf '%s\n' beta
```
````

Supplied table:

```text
| Check | Result |
| --- | --- |
| source | passed |
| behavior | pending |
```

Supplied raw and preformatted region:

```text
<pre data-owner="fixture">
line one
  line two
</pre>
```

Supplied control marker:

```text
<!-- mergecraft-control:retain-exactly -->
```

Use LF and no terminal newline. Do not create or update a pull request.
