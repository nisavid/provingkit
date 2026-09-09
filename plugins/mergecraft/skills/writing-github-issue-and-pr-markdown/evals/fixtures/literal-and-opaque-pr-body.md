# Pull-request body with literal regions

Field: Pull-request body.

Caller handoff: author a creation template with a `## Changes` section containing this exact link: [Changes](https://github.com/example/fixture/pull/__PUBLISHING_REVIEWABLE_PRS_PR_NUMBER__/changes). The operation contract reserves this literal token for the assigned PR number. Return the token unchanged. The separately authorized creation operation will replace only that token with the assigned decimal number, validate the complete rendered body, and hand those final bytes to its posting step. All other template bytes remain unchanged; this request authorizes no GitHub operation.

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
