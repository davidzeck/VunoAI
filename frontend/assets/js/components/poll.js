import { api } from "../api.js";
import { POLL_INTERVAL_MS, PROCESSING_STATUSES } from "../config.js";

/**
 * Polls a task until it leaves pending/in_progress state.
 * Calls onDone(task) when finished, onError(err) on failure.
 * Returns a stop() function to cancel polling.
 */
export function pollTask(taskCode, { onDone, onError } = {}) {
  const id = setInterval(async () => {
    try {
      const task = await api.tasks.get(taskCode);
      // Stop when: status leaves processing (failed/rejected), OR steps arrive
      // (steps arriving = AI pipeline finished; task stays in_progress for ops to fulfil)
      const pipelineDone = !PROCESSING_STATUSES.includes(task.status) || task.steps?.length > 0;
      if (pipelineDone) {
        clearInterval(id);
        onDone?.(task);
      }
    } catch (err) {
      clearInterval(id);
      onError?.(err);
    }
  }, POLL_INTERVAL_MS);

  return () => clearInterval(id);
}
