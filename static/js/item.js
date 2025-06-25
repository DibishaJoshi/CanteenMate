document.addEventListener('DOMContentLoaded', function () {
    const addItemBtn = document.getElementById('addUnitBtn');
    const modal = document.getElementById('item-modal');
    const closeBtn = document.querySelector('.close-btn');
    const cancelBtn = document.getElementById('cancelBtn');
    const form = document.getElementById('item-form');
    const searchInput = document.querySelector('.search-box input');
    const tableBody = document.getElementById('item-table-body');

    // Show modal
    addItemBtn.addEventListener('click', () => {
        form.reset();
        modal.style.display = 'block';
        document.getElementById('modal-header-title').innerText = "Add New Item";
    });

    // Close Modal
    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = '';
        form.reset();
        document.querySelector('.modal-header h2').textContent = 'Add Item';
    }

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    window.addEventListener('click', function (e) {
        if (e.target === modal) closeModal();
    });


    // // Handle form submission (demo)
    // form.addEventListener('submit', function (e) {
    //     e.preventDefault();

    //     const name = document.getElementById('item-name').value;
    //     const category = document.getElementById('item-category').value;
    //     const price = parseFloat(document.getElementById('item-price').value).toFixed(2);
    //     const available = document.getElementById('item-available').checked ? 'Yes' : 'No';

    //     // You can send data to the server here (e.g., using fetch)

    //     console.log({
    //         name,
    //         category,
    //         price,
    //         available,
    //         description: document.getElementById('item-description').value,
    //         image: document.getElementById('item-image').files[0]
    //     });

    //     // Optionally add new item to the table dynamically (demo purpose)
    //     const newRow = document.createElement('tr');
    //     newRow.innerHTML = `
    //         <td>NEW</td>
    //         <td>${name}</td>
    //         <td>${category}</td>
    //         <td>$${price}</td>
    //         <td><span class="status ${available === 'Yes' ? 'available' : 'not-available'}">${available}</span></td>
    //         <td class="actions">
    //             <button class="btn-edit"><i class="fas fa-edit"></i></button>
    //             <button class="btn-delete"><i class="fas fa-trash"></i></button>
    //         </td>
    //     `;
    //     tableBody.appendChild(newRow);

    //     closeModal();
    // });

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
    document.querySelectorAll('.btn-edit').forEach(button => {
    button.addEventListener('click', function () {
        const itemId = this.dataset.id;
        const name = this.dataset.name;
        const category = this.dataset.category;
        const price = this.dataset.price;
        const description = this.dataset.description;
        const available = this.dataset.available === 'true';

        // Fill the form
        document.getElementById('item-id').value = itemId;
        document.getElementById('item-name').value = name;
        document.getElementById('item-category').value = category;
        document.getElementById('item-price').value = price;
        document.getElementById('item-description').value = description;
        document.getElementById('item-available').checked = available;

        // Change modal header
        document.getElementById('modal-header-title').innerText = "Edit Item";

        // Show modal
        modal.style.display = 'block';
    });
});


    console.log("item.js loaded");
});
