const triggers = document.querySelectorAll('.accordion-trigger');
triggers.forEach(trigger => {
  trigger.addEventListener('click', () => {
    const idx = trigger.dataset.index;
    const panel = document.getElementById('panel-' + idx);
    const isOpen = trigger.classList.contains('open');

    // Close all
    triggers.forEach(t => t.classList.remove('open'));
    document.querySelectorAll('.accordion-panel').forEach(p => p.classList.remove('open'));

    // Toggle clicked
    if (!isOpen) {
      trigger.classList.add('open');
      panel.classList.add('open');
    }
  });
});
