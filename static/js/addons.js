document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('addonModal');
    const openModalBtn = document.getElementById('addAddonBtn');
    const closeModalBtn = document.querySelector('.close-btn');
    const cancelBtn = document.getElementById('cancelBtn');
    const searchInput = document.querySelector('.search-box input');
    const addonForm = document.getElementById('addonForm');

    // Show modal
    openModalBtn.addEventListener('click', () => {
        addonForm.reset(); // Reset all input fields
        modal.style.display = 'block';
    });

    // Hide modal
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

    // Search functionality
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

    // Optional: Form submission handler
    addonForm.addEventListener('submit', function (e) {
        e.preventDefault();
        // Example: you can log the form data or send it to server via fetch
        const name = document.getElementById('addonName').value;
        const price = document.getElementById('addonPrice').value;
        const category = document.getElementById('addonCategory').value;
        const description = document.getElementById('addonDescription').value;
        const image = document.getElementById('addonImage').files[0];
        const status = addonForm.querySelector('input[name="status"]:checked').value;

        console.log({ name, price, category, description, image, status });

        // For now, just close the modal
        closeModal();
    });

    console.log("✅ addons.js loaded");
});
