document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('unitModal');
    const openModalBtn = document.getElementById('addUnitBtn');
    const closeModalBtn = document.querySelector('.close-btn');
    const cancelBtn = document.getElementById('cancelBtn');
    const searchInput = document.querySelector('.search-box input');

    // Open modal
    openModalBtn.addEventListener('click', () => {
        document.getElementById('unitForm').reset(); // Reset form
        modal.style.display = 'block';
    });

    // Close modal
    function closeModal() {
        modal.style.display = 'none';
    }

    closeModalBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    // Optional: Close modal when clicking outside of it
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Search functionality
    searchInput.addEventListener('keyup', function () {
        const searchTerm = this.value.toLowerCase();
        const rows = document.querySelectorAll('.units-list table tbody tr');

        rows.forEach(row => {
            const unitName = row.cells[1].textContent.toLowerCase();
            const shortName = row.cells[2].textContent.toLowerCase();

            if (unitName.includes(searchTerm) || shortName.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });

    console.log("✅ units.js loaded");
});
