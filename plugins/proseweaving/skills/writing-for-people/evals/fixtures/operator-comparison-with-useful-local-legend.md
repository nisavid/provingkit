# Request

Ivan asks for a compact private chat table comparing the two workflow labels printed by a diagnostic console. Keep those labels so he can match each of the repeated result rows to that console, and define them locally. The full workflow names are long, and repeating each full name in six rows would take more space than a two-entry legend.

# Source facts

Q7 means queue service restoration after interruption.
R2 means replay completion verification after restoration.

The six console observations are:

| Attempt | Workflow | Result |
| --- | --- | --- |
| 1 | Q7 | completed |
| 1 | R2 | pending |
| 2 | Q7 | completed |
| 2 | R2 | completed |
| 3 | Q7 | completed |
| 3 | R2 | pending |

These are diagnostic observations only. Ivan has not chosen a recovery action. The source legend is available here; a message containing the table alone would not include it.
