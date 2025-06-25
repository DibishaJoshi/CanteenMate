document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('addonModal');
    const openModalBtn = document.getElementById('addAddonBtn');
    const closeModalBtn = document.querySelector('.close-btn');
    const cancelBtn = document.getElementById('cancelBtn');
    const searchInput = document.querySelector('.search-box input');
    const addonForm = document.getElementById('addonForm');

    // Show modal for adding new addon
    openModalBtn.addEventListener('click', () => {
        addonForm.reset();                      // Reset form fields
        addonForm.action = '/admin/addons/add'; // Set form action to add route
        modal.style.display = 'block';         // Show modal
    });

    // Show modal for editing existing addon
    document.querySelectorAll('.edit-addon-btn').forEach(button => {
        button.addEventListener('click', () => {
            // Populate form fields from button's data attributes
            addonForm.elements['addonName'].value = button.dataset.name || '';
            addonForm.elements['addonPrice'].value = button.dataset.price || '';
            addonForm.elements['addonCategory'].value = button.dataset.category || '';
            addonForm.elements['addonDescription'].value = button.dataset.description || '';

            // Change form action to the edit URL with the addon ID
            addonForm.action = `/admin/addons/edit/${button.dataset.id}`;

            // Show modal
            modal.style.display = 'block';
        });
    });

    // Hide modal function
    function closeModal() {
        modal.style.display = 'none';
    }

    closeModalBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Search functionality to filter addons list
    searchInput.addEventListener('keyup', function () {
        const term = this.value.toLowerCase();
        const rows = document.querySelectorAll('.addons-list tbody tr');

        rows.forEach(row => {
            const name = row.cells[1].textContent.toLowerCase();
            const category = row.cells[3].textContent.toLowerCase();
            if (name.includes(term) || category.includes(term)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });

    console.log("addons.js loaded");
});
