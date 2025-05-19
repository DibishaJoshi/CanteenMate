document.addEventListener('DOMContentLoaded', function () {
    const addItemBtn = document.getElementById('addUnitBtn');
    const modal = document.getElementById('item-modal');
    const closeModalBtn = modal.querySelector('.close');
    const cancelBtn = modal.querySelector('.cancel-btn');
    const form = document.getElementById('item-form');
    const searchInput = document.querySelector('.search-box input');
    const tableBody = document.getElementById('item-table-body');

    // Show modal
    addItemBtn.addEventListener('click', () => {
        form.reset();
        modal.style.display = 'block';
        document.getElementById('modal-title').innerText = "Add New Item";
    });

    // Close modal
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

    // Handle form submission (demo)
    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const name = document.getElementById('item-name').value;
        const category = document.getElementById('item-category').value;
        const price = parseFloat(document.getElementById('item-price').value).toFixed(2);
        const available = document.getElementById('item-available').checked ? 'Yes' : 'No';

        // You can send data to the server here (e.g., using fetch)

        console.log({
            name,
            category,
            price,
            available,
            description: document.getElementById('item-description').value,
            image: document.getElementById('item-image').files[0]
        });

        // Optionally add new item to the table dynamically (demo purpose)
        const newRow = document.createElement('tr');
        newRow.innerHTML = `
            <td>NEW</td>
            <td>${name}</td>
            <td>${category}</td>
            <td>$${price}</td>
            <td><span class="status ${available === 'Yes' ? 'available' : 'not-available'}">${available}</span></td>
            <td class="actions">
                <button class="btn-edit"><i class="fas fa-edit"></i></button>
                <button class="btn-delete"><i class="fas fa-trash"></i></button>
            </td>
        `;
        tableBody.appendChild(newRow);

        closeModal();
    });

    // Search functionality
    searchInput.addEventListener('keyup', function () {
        const filter = this.value.toLowerCase();
        const rows = tableBody.querySelectorAll('tr');

        rows.forEach(row => {
            const name = row.cells[1].textContent.toLowerCase();
            const category = row.cells[2].textContent.toLowerCase();

            if (name.includes(filter) || category.includes(filter)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });

    console.log("✅ item.js loaded");
});
