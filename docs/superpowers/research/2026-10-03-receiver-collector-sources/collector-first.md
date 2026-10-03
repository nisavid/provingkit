# First collector and fixture-procedure findings

The source candidate wraps the reviewed Stop projector with a one-shot command, bounded configuration and stdin acquisition, explicit endpoint environment selection, receipt intervals, and completed-file publication. Fourteen command tests and the twenty existing reader/hook tests pass on Node.js 24.21.0. Every result remains unqualified.

The initial fixture has no independently known Code ID. With a null expected ID, the wrapper retains only a matching setup token and observed Code ID as unbound evidence. It never turns the observed ID into its own expected ID. A configured ID remains caller-supplied. A setup response candidate has no notification-acknowledgment meaning.

A stalled fs.read attempt published its timeout record but did not exit until EOF. The final stdin reader wraps fd 0 with the documented net.Socket onread buffer, bounds acquisition to the configured limit plus one overflow byte, and closes the inherited pipe on timeout. The retained test checks process termination as well as the unknown record.

A one-shot claim persists through success and failure, preventing another acquisition on the same output slot. Completed bytes are linked without replacing an existing destination. Interrupted output, occupied destination, and signal cases have synthetic checks; abrupt death may leave a claim or partial file for reviewed cleanup. The filesystem operations have no total deadline or crash-durability claim. Paths and directory ownership are trusted inputs, with no hostile-path, producer-authentication, or live privacy-control acceptance.

The source procedure specifies the proposed hook change, one setup turn, independent UI witness, unbound event/current metadata join, accepted metadata read limits, scope-bound restoration, and phase outcomes. It proposes no app patch or restart. Selected executor, exact account/org directory, actual live launcher environment/command, private-read inputs, and relevant controls remain inputs for preparation and review. The command itself does not identify the receiver engine parent or acquire metadata.

These files were authored from the published baseline and accepted decision. One preliminary runtime-lane transport finding reached the coordinator before this freeze; it did not change the collector code. The runtime lane read no collector work. Its complete first report arrived as this snapshot was being prepared and has not been used to revise these files. Do not describe the coordinator integration as completely blind.

Cross-examination should test first-acquisition binding, event meaning, bounded input and output lifecycle, selected-executor witness, whole-event/file footprint, restoration after concurrency, and whether remaining inputs permit a concrete live proposal. Full account/model/permissions/worktree qualification and notification delivery remain outside this experiment's claim.
