# User authorized immediate diagnostic on 27 October

The user explicitly requested stopping current training and proceeding directly
with the checks. This supersedes the natural-completion resource wait in PROTOCOL.
Training must remain stopped; this diagnostic never resumes it.

Only the identity-checked ICPS driver and this diagnostic's idle waiting process
received SIGINT. The training launcher cleaned up its own scoped Ray processes.
The checkpoint inventory remained at40. Completed steps41/42 and in-flight43 were
not saved. Exit1 denotes this user-requested interruption, not a training defect.

The original queue and all its records remain unchanged. run_after_user_stop.py
uses separate queue metadata/lock files. It requires a confirmation recording the
authorized stop, exact protected run and observed exit code, absent stopped PIDs,
all eight GPUs idle, no Ray processes, disk200GiB, and repeated idle checks.
Seven new CPU guard tests passed. Source SHA checks and the original frozen model
code, cache, four conditions, model checkpoints and output schema are unchanged.

At launch the GPU experiment has not yet completed. The new control file is
USER_STOP_QUEUE_STATE.json and completion remains FINAL_CONTRAST.json. A failed
forward stops the queue, preserving evidence; no blind retry or training restart.
Models, private stop evidence and raw trajectory/value outputs are not published.
