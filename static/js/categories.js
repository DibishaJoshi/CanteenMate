console.log("✅ categories.js loaded");
document.addEventListener('DOMContentLoaded', function () {
    // Tooltip init (if used)
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (el) {
        return new bootstrap.Tooltip(el);
    });

    // Modal Elements
    const modal = document.getElementById('categoryModal');
    const openBtn = document.querySelector('.add-btn');
    const closeBtn = document.querySelector('.close-btn');
    const cancelBtn = document.getElementById('cancelBtn');
    const categoryForm = document.getElementById('categoryForm');

    // Open Modal
    openBtn.addEventListener('click', function () {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    });

    // Close Modal
    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = '';
        categoryForm.reset();
        document.querySelector('.modal-header h2').textContent = 'Add Category';
    }

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    window.addEventListener('click', function (e) {
        if (e.target === modal) closeModal();
    });

    // Handle Form Submit
    categoryForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const name = document.getElementById('categoryName').value;
        const description = document.getElementById('categoryDescription').value;
        const image = document.getElementById('categoryImage').value;
        const status = document.querySelector('input[name="status"]:checked').value;

        console.log('Form submitted:', { name, description, image, status });

        const successAlert = document.createElement('div');
        successAlert.className = 'alert alert-success';
        successAlert.textContent = 'Category saved successfully!';
        document.querySelector('.category-section').insertBefore(successAlert, document.querySelector('.section-header'));

        closeModal();

        setTimeout(() => successAlert.remove(), 3000);
    });

    // Edit Buttons
    document.querySelectorAll('.action-btn.edit').forEach(button => {
        button.addEventListener('click', function () {
            const row = this.closest('tr');
            const name = row.cells[1].textContent.trim();
            const description = ""; // You don’t show description in table. Adjust as needed.
            const status = row.querySelector('.status-badge').classList.contains('active') ? 'active' : 'inactive';

            document.getElementById('categoryName').value = name;
            document.getElementById('categoryDescription').value = description;
            document.querySelector(`input[name="status"][value="${status}"]`).checked = true;

            document.querySelector('.modal-header h2').textContent = 'Edit Category';
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        });
    });

    // Delete Buttons
    document.querySelectorAll('.action-btn.delete').forEach(button => {
        button.addEventListener('click', function () {
            const row = this.closest('tr');
            const name = row.cells[1].textContent;

            if (confirm(`Are you sure you want to delete the category "${name}"?`)) {
                row.style.backgroundColor = '#ffdddd';
                row.style.opacity = '0.5';

                const alert = document.createElement('div');
                alert.className = 'alert alert-danger';
                alert.textContent = `Category "${name}" deleted successfully!`;
                document.querySelector('.category-section').insertBefore(alert, document.querySelector('.section-header'));

                setTimeout(() => {
                    alert.remove();
                    row.remove();
                }, 1000);
            }
        });
    });

    // Search Functionality
    const searchInput = document.querySelector('.search-filter input');
    searchInput.addEventListener('keyup', function () {
        const term = this.value.toLowerCase();
        const rows = document.querySelectorAll('.data-table tbody tr');

        rows.forEach(row => {
            const name = row.cells[1].textContent.toLowerCase();
            const itemsCount = row.cells[2].textContent.toLowerCase();

            if (name.includes(term) || itemsCount.includes(term)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });

    // Pagination buttons (demo)
    document.querySelectorAll('.page-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.page-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            console.log('Page changed:', this.textContent.trim());
        });
    });
});
