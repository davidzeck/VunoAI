document.addEventListener('DOMContentLoaded', () => {
  const filterForm = document.getElementById('filter-form');
  if (!filterForm) return;

  filterForm.querySelectorAll('select').forEach(select => {
    select.addEventListener('change', () => filterForm.submit());
  });
});
