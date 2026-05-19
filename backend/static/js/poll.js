function pollTaskStatus(taskCode) {
  const INTERVAL_MS = 2000;
  const PROCESSING  = ['pending', 'in_progress'];

  const id = setInterval(async () => {
    try {
      const data = await API.get(`/tasks/${taskCode}/`);
      if (!PROCESSING.includes(data.status)) {
        clearInterval(id);
        location.reload();
      }
    } catch (err) {
      console.error('Poll error:', err);
    }
  }, INTERVAL_MS);
}
